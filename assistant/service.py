"""Chat logic. This layer may read the admin-written AssistantCommand rows; it never gives the model anything else."""
import re

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from . import ai
from .models import AssistantCommand, AssistantSettings

MAX_HISTORY = 10          # messages kept per visitor session (5 exchanges)
BURST_LIMIT = 8           # messages per minute


def ai_available(cfg):
    return bool(cfg.use_ai and settings.ANTHROPIC_API_KEY)


def audience_of(user):
    return "customers" if user.is_authenticated else "guests"


def visible_commands(user):
    return AssistantCommand.objects.filter(active=True).filter(Q(audience="all") | Q(audience=audience_of(user)))


def _client_ids(request):
    if not request.session.session_key:
        request.session.save()
    return [f"ip:{request.META.get('REMOTE_ADDR', '?')}", f"s:{request.session.session_key}"]


def _bump(key, timeout):
    cache.add(key, 0, timeout)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout)
        return 1


def rate_limited(request, cfg):
    """True when this visitor (by IP or session) sent too many messages. Checked before any AI cost is incurred."""
    today = timezone.localdate().isoformat()
    for cid in _client_ids(request):
        if _bump(f"assistant:min:{cid}", 60) > BURST_LIMIT or _bump(f"assistant:day:{cid}:{today}", 86400) > cfg.max_messages_per_day:
            return True
    return False


def keyword_match(text, commands):
    words = set(re.findall(r"[a-z0-9']+", text.lower()))
    best, best_score = None, 0
    for c in commands:
        score = sum(1 for k in c.keyword_list() if set(re.findall(r"[a-z0-9']+", k)) <= words)
        if score > best_score:
            best, best_score = c, score
    return best


def help_text(commands):
    lines = [f"/{c.trigger} - {c.title}" for c in commands]
    return "Available commands:\n" + "\n".join(lines) if lines else "No commands have been set up yet."


def get_history(request):
    return [m for m in request.session.get("assistant_history", []) if m.get("role") in ("user", "assistant")][-MAX_HISTORY:]


def remember(request, user_text, reply):
    hist = get_history(request) + [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
    request.session["assistant_history"] = hist[-MAX_HISTORY:]


def answer(request, raw_text):
    """Returns {'reply': str, 'kind': 'command'|'ai'|'fallback'|'limit'}."""
    cfg = AssistantSettings.load()
    text = ai.clean_user_text(raw_text)
    if not text:
        return {"reply": "Please type a question.", "kind": "fallback"}
    if rate_limited(request, cfg):
        return {"reply": "You are sending messages very quickly. Please wait a bit and try again.", "kind": "limit"}
    commands = list(visible_commands(request.user))

    if text.startswith("/"):                                   # slash commands: exact, admin-written replies, no AI involved
        trigger = text[1:].split(" ")[0].lower()
        if trigger in ("help", "commands", ""):
            return {"reply": help_text(commands), "kind": "command"}
        match = next((c for c in commands if c.trigger == trigger), None)
        if match:
            return {"reply": match.response, "kind": "command"}
        return {"reply": f"I don't know the command /{trigger}.\n" + help_text(commands), "kind": "command"}

    if ai_available(cfg):
        knowledge = [(c.title, c.response) for c in commands if c.use_in_ai]
        system = ai.build_system_prompt(cfg.name, cfg.extra_instructions, knowledge)
        messages = get_history(request) + [{"role": "user", "content": text}]
        try:
            reply = ai.call_model(system, messages, api_key=settings.ANTHROPIC_API_KEY, model=settings.ASSISTANT_MODEL)
            remember(request, text, reply)
            return {"reply": reply, "kind": "ai"}
        except ai.AIError:
            pass  # fall through to the offline answer below
    match = keyword_match(text, commands)
    if match:
        return {"reply": match.response, "kind": "command"}
    return {"reply": cfg.fallback_message, "kind": "fallback"}
