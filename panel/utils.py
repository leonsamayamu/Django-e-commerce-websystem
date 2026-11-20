"""Helpers that let one view serve both a pop-up (AJAX) and a normal page (no-JS fallback)."""
from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render


class ConfirmForm(forms.Form):
    """Empty form used for 'Are you sure?' pop-ups (it only carries the CSRF token)."""


def is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def form_args(request):
    """(data, files) for a form: bound on POST, unbound otherwise (even if the POST body is empty)."""
    return (request.POST, request.FILES) if request.method == "POST" else (None, None)


def modal_form(request, form, *, title, partial, submit="Save", subtitle="", danger=False, cancel_url="/staff/", ctx=None):
    context = {"form": form, "title": title, "partial": partial, "submit": submit, "subtitle": subtitle,
               "danger": danger, "cancel_url": cancel_url, **(ctx or {})}
    if is_ajax(request):
        # 422 = form re-rendered with errors; the JS swaps the pop-up content for this HTML.
        return render(request, "panel/modal_form.html", context, status=422 if form.is_bound else 200)
    return render(request, "panel/page_form.html", context)


def done(request, message, *, to, level="success"):
    getattr(messages, level)(request, message)
    if is_ajax(request):
        return JsonResponse({"ok": True})  # JS closes the pop-up and reloads to show the message
    return redirect(to)


def paginate(request, queryset, per_page=20):
    page = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()


def confirm_delete(request, obj, *, title, message, ok, back, submit="Delete"):
    """Standard 'Are you sure?' pop-up that deletes `obj` on POST."""
    from django.urls import reverse
    form = ConfirmForm(*form_args(request)[:1])
    if request.method == "POST" and form.is_valid():
        obj.delete()
        return done(request, ok, to=reverse(back))
    return modal_form(request, form, title=title, partial="panel/forms/confirm.html", submit=submit, danger=True,
                      cancel_url=reverse(back), ctx={"message": message})
