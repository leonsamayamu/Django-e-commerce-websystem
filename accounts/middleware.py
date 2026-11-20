from django.http import Http404


class AdminOnlyMiddleware:
    """The Django admin (/admin/) is for superusers only. Staff and customers get a plain 404, so the
    admin site is not even discoverable from a staff account."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if request.path.startswith("/admin/") and user.is_authenticated and not user.is_superuser:
            raise Http404
        return self.get_response(request)
