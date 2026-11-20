import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from . import service
from .models import AssistantSettings


def _enabled_or_404():
    cfg = AssistantSettings.load()
    return cfg if cfg.enabled else None


@require_GET
def init(request):
    cfg = _enabled_or_404()
    if cfg is None:
        return JsonResponse({"enabled": False}, status=404)
    chips = [{"trigger": c.trigger, "title": c.title} for c in service.visible_commands(request.user) if c.show_chip]
    return JsonResponse({"enabled": True, "name": cfg.name, "greeting": cfg.greeting, "chips": chips,
                         "history": service.get_history(request)})


@require_POST
def chat(request):
    if _enabled_or_404() is None:
        return JsonResponse({"error": "disabled"}, status=404)
    try:
        payload = json.loads(request.body[:4000] or b"{}")
        text = payload.get("message", "") if isinstance(payload, dict) else None
        if not isinstance(text, str):
            raise ValueError
    except ValueError:
        return JsonResponse({"error": "bad request"}, status=400)
    # Only the message text is read from the request. History comes from the server-side session,
    # so a visitor cannot forge earlier "assistant" turns to steer the model.
    return JsonResponse(service.answer(request, text))


@require_POST
def reset(request):
    request.session.pop("assistant_history", None)
    return JsonResponse({"ok": True})
