from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .roles import caps_for


def capability_required(*caps):
    """The user needs at least one of the capabilities (see accounts/roles.py). Anonymous -> login, others -> 403."""
    wanted = set(caps)

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not (caps_for(request.user) & wanted):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator


def staff_required(view):
    """Any staff member (every role has the dashboard capability)."""
    return capability_required("dashboard")(view)


def superuser_required(view):
    """Shop admins only."""
    return capability_required("admin")(view)
