from .models import AssistantSettings


def assistant(request):
    """Cached (1 minute) so the chat widget costs no database query on most page views."""
    cfg = AssistantSettings.load()
    return {"assistant_enabled": cfg.enabled, "assistant_name": cfg.name, "assistant_greeting": cfg.greeting}
