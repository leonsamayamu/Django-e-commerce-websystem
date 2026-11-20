import csv
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, ProtectedError, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import capability_required, staff_required, superuser_required
from accounts.roles import caps_for, role_of
from store.forms import ProductForm
from store.invoices import build_pdf, invoice_data
from store.models import Category, Order, OrderItem, Product, ProductVariant
from support.emails import absolute_url
from support.models import Subscriber

from . import analytics as an

from .forms import CategoryForm, OrderStatusForm, UserCreateForm, UserEditForm, VariantFormSet
from .utils import ConfirmForm, done, form_args, modal_form, paginate

LINE_TOTAL = F("items__price") * F("items__quantity")


# ---------------------------------------------------------------- dashboard
def _orders_for(user):
    """Delivery staff only ever see the orders assigned to them."""
    qs = Order.objects.all()
    return qs.filter(courier=user) if role_of(user) == "delivery" else qs


def low_stock_items(limit=6):
    simple = [{"name": p.name, "stock": p.stock, "pk": p.pk} for p in
              Product.objects.filter(available=True, variants__isnull=True, stock__lte=5)]
    options = [{"name": f"{v.product.name} - {v.name}", "stock": v.stock, "pk": v.product_id} for v in
               ProductVariant.objects.filter(available=True, stock__lte=5, product__available=True).select_related("product")]
    return sorted(simple + options, key=lambda x: x["stock"])[:limit]


@staff_required
def dashboard(request):
    caps = caps_for(request.user)
    ctx = {"role": role_of(request.user)}
    if "analytics" in caps:
        today = timezone.localdate()
        start = today - timedelta(days=6)
        live_items = OrderItem.objects.exclude(order__status="cancelled")
        daily = {r["day"]: r["total"] for r in live_items.filter(order__created__date__gte=start)
                 .annotate(day=TruncDate("order__created")).values("day")
                 .annotate(total=Sum(F("price") * F("quantity")))}
        days = [{"day": start + timedelta(days=i), "total": daily.get(start + timedelta(days=i), Decimal("0"))} for i in range(7)]
        peak = max((d["total"] for d in days), default=0) or 1
        for d in days:
            d["pct"] = max(4, int(d["total"] / peak * 100)) if d["total"] else 2
        ctx.update(revenue=live_items.aggregate(t=Sum(F("price") * F("quantity")))["t"] or 0,
                   week_revenue=sum(d["total"] for d in days), days=days,
                   customer_count=User.objects.filter(is_staff=False).count())
    if "orders" in caps:
        orders = _orders_for(request.user)
        ctx.update(order_count=orders.count(), pending_count=orders.filter(status="pending").count(),
                   recent=orders.annotate(t=Sum(LINE_TOTAL)).order_by("-created", "-pk")[:6],
                   to_pack=orders.filter(status__in=("pending", "processing")).count(),
                   to_deliver=orders.filter(status__in=("shipped", "out_for_delivery")).count())
        if role_of(request.user) == "delivery":
            ctx["my_deliveries"] = (orders.exclude(status__in=("delivered", "cancelled"))
                                    .annotate(t=Sum(LINE_TOTAL)).order_by("created"))
    if "catalog" in caps:
        ctx.update(product_count=Product.objects.count(), low_stock=low_stock_items())
    if "marketing" in caps:
        ctx.update(active_subs=Subscriber.objects.filter(active=True).count(),
                   new_subs_week=Subscriber.objects.filter(active=True, created__gte=timezone.now() - timedelta(days=7)).count(),
                   latest_subs=Subscriber.objects.filter(active=True)[:5])
    return render(request, "panel/dashboard.html", ctx)


# ---------------------------------------------------------------- orders
@capability_required("orders")
def orders(request):
    qs = _orders_for(request.user).annotate(n=Count("items"), t=Sum(LINE_TOTAL)).select_related("courier").order_by("-created", "-pk")
    status, q = request.GET.get("status", ""), request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        cond = Q(name__icontains=q) | Q(email__icontains=q)
        qs = qs.filter(cond | Q(pk=q)) if q.isdigit() else qs.filter(cond)
    page, query_string = paginate(request, qs, 20)
    return render(request, "panel/orders.html", {
        "page": page, "query_string": query_string, "statuses": Order.STATUS_CHOICES, "active": status, "q": q})


@capability_required("orders")
def order_detail(request, pk):
    order = get_object_or_404(_orders_for(request.user).prefetch_related("items__product", "payments"), pk=pk)
    return render(request, "panel/order_detail.html", {"order": order, "payments": list(order.payments.all())})


@capability_required("orders_fulfil")
def order_status(request, pk):
    order = get_object_or_404(_orders_for(request.user), pk=pk)
    url = absolute_url(request, order.get_absolute_url())
    form = OrderStatusForm(*form_args(request), instance=order, actor=request.user, order_url=url)
    if request.method == "POST" and form.is_valid():
        form.save()
        return done(request, f"Order #{order.pk} updated.", to=reverse("staff_order_detail", args=[pk]))
    return modal_form(request, form, title=f"Update order #{order.pk}", partial="panel/forms/order_status.html",
                      subtitle=f"{order.name} - {order.email}", cancel_url=reverse("staff_order_detail", args=[pk]),
                      ctx={"order": order})


@capability_required("invoices")
def order_invoice(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, "store/invoice.html", {**invoice_data(order), "staff_pdf": reverse("staff_order_invoice_pdf", args=[pk])})


@capability_required("invoices")
def order_invoice_pdf(request, pk):
    order = get_object_or_404(Order, pk=pk)
    resp = HttpResponse(build_pdf(order), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="invoice-{order.invoice_number}.pdf"'
    return resp


# ---------------------------------------------------------------- products
@capability_required("catalog")
def products(request):
    qs = Product.objects.select_related("category").prefetch_related("images", "variants")
    q, cat, state = request.GET.get("q", "").strip(), request.GET.get("category", ""), request.GET.get("state", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat.isdigit():
        qs = qs.filter(category_id=cat)
    if state == "hidden":
        qs = qs.filter(available=False)
    elif state == "low":
        qs = qs.filter(Q(variants__isnull=True, stock__lte=5) | Q(variants__available=True, variants__stock__lte=5)).distinct()
    page, query_string = paginate(request, qs, 15)
    return render(request, "panel/products.html", {
        "page": page, "query_string": query_string, "q": q, "cat": cat, "state": state,
        "categories": Category.objects.all()})


def _product_form(request, product=None):
    form = ProductForm(*form_args(request), instance=product)
    # The pop-up always sends the options table; a post without it simply leaves the options unchanged.
    has_options = request.method == "POST" and "variants-TOTAL_FORMS" in request.POST
    formset = VariantFormSet(request.POST if has_options else None, instance=product or Product(), prefix="variants")
    if request.method == "POST" and form.is_valid() and (not has_options or formset.is_valid()):
        with transaction.atomic():
            saved = form.save()
            if has_options:
                formset.instance = saved
                formset.save()
        return done(request, f"Product '{saved.name}' {'updated' if product else 'added'}.", to=reverse("staff_products"))
    return modal_form(request, form, title="Edit product" if product else "Add product",
                      subtitle=product.name if product else "Fill in the details, upload photos and add options if needed.",
                      partial="panel/forms/product.html", submit="Save product", cancel_url=reverse("staff_products"),
                      ctx={"product": product, "formset": formset})


@capability_required("catalog")
def product_create(request):
    return _product_form(request)


@capability_required("catalog")
def product_edit(request, pk):
    return _product_form(request, get_object_or_404(Product, pk=pk))


@capability_required("catalog")
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ConfirmForm(*form_args(request)[:1])
    if request.method == "POST" and form.is_valid():
        try:
            product.delete()
        except ProtectedError:  # order history must keep its products: hide instead of delete
            product.available = False
            product.save(update_fields=["available"])
            return done(request, f"'{product.name}' is in past orders, so it cannot be deleted. It was hidden from the shop instead.",
                        to=reverse("staff_products"), level="warning")
        return done(request, f"Product '{product.name}' deleted.", to=reverse("staff_products"))
    return modal_form(request, form, title="Delete product?", partial="panel/forms/confirm.html", submit="Delete product",
                      danger=True, cancel_url=reverse("staff_products"),
                      ctx={"message": f"'{product.name}' and its photos will be permanently deleted. "
                                      "If it appears in past orders it will be hidden instead."})


# ---------------------------------------------------------------- categories
@capability_required("catalog")
def categories(request):
    return render(request, "panel/categories.html", {"categories": Category.objects.annotate(n=Count("products"))})


def _category_form(request, category=None):
    form = CategoryForm(*form_args(request), instance=category)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        return done(request, f"Category '{saved.name}' {'updated' if category else 'added'}.", to=reverse("staff_categories"))
    return modal_form(request, form, title="Edit category" if category else "Add category",
                      partial="panel/forms/category.html", cancel_url=reverse("staff_categories"))


@capability_required("catalog")
def category_create(request):
    return _category_form(request)


@capability_required("catalog")
def category_edit(request, pk):
    return _category_form(request, get_object_or_404(Category, pk=pk))


@capability_required("catalog")
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = ConfirmForm(*form_args(request)[:1])
    if request.method == "POST" and form.is_valid():
        try:
            category.delete()
        except ProtectedError:
            return done(request, f"'{category.name}' still has products. Move or delete them first.",
                        to=reverse("staff_categories"), level="error")
        return done(request, f"Category '{category.name}' deleted.", to=reverse("staff_categories"))
    return modal_form(request, form, title="Delete category?", partial="panel/forms/confirm.html", submit="Delete category",
                      danger=True, cancel_url=reverse("staff_categories"),
                      ctx={"message": f"Delete the category '{category.name}'? This only works if it has no products."})


# ---------------------------------------------------------------- users
def can_edit(actor, target):
    """Staff manage customers; only superusers manage staff and other superusers."""
    return actor.is_superuser or target.pk == actor.pk or not (target.is_staff or target.is_superuser)


def can_remove(actor, target):
    """Deactivate/delete: never yourself, never a superuser, and staff accounts need a superuser."""
    return target.pk != actor.pk and not target.is_superuser and can_edit(actor, target)


def _target(request, pk, check):
    target = get_object_or_404(User, pk=pk)
    if not check(request.user, target):
        raise PermissionDenied
    return target


@capability_required("customers")
def users(request):
    qs = (User.objects.annotate(order_count=Count("orders", distinct=True),
                                subscribed=Exists(Subscriber.objects.filter(active=True, email__iexact=OuterRef("email"))))
          .select_related("profile"))
    q, role = request.GET.get("q", "").strip(), request.GET.get("role", "")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if role == "customers":
        qs = qs.filter(is_staff=False)
    elif role == "staff":
        qs = qs.filter(is_staff=True)
    elif role == "inactive":
        qs = qs.filter(is_active=False)
    elif role == "subscribed":
        qs = qs.filter(subscribed=True)
    page, query_string = paginate(request, qs.order_by("-date_joined"), 20)
    rows = list(page.object_list)
    for u in rows:
        u.can_edit, u.can_remove = can_edit(request.user, u), can_remove(request.user, u)
    return render(request, "panel/users.html", {"page": page, "rows": rows, "query_string": query_string, "q": q, "role": role})


@capability_required("customers")
def user_create(request):
    form = UserCreateForm(*form_args(request), actor=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        return done(request, f"User '{user.username}' created.", to=reverse("staff_users"))
    return modal_form(request, form, title="Add user", subtitle="Create a customer or staff account.",
                      partial="panel/forms/user_create.html", submit="Create user", cancel_url=reverse("staff_users"))


@capability_required("customers")
def user_edit(request, pk):
    target = _target(request, pk, can_edit)
    form = UserEditForm(*form_args(request), instance=target, actor=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return done(request, f"User '{target.username}' updated.", to=reverse("staff_users"))
    return modal_form(request, form, title="Edit user", subtitle=f"@{target.username}",
                      partial="panel/forms/user_edit.html", cancel_url=reverse("staff_users"), ctx={"target": target})


@capability_required("customers")
def user_password(request, pk):
    target = _target(request, pk, can_edit)
    form = SetPasswordForm(target, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return done(request, f"Password changed for '{target.username}'.", to=reverse("staff_users"))
    return modal_form(request, form, title="Set new password", subtitle=f"@{target.username}",
                      partial="panel/forms/password.html", submit="Change password", cancel_url=reverse("staff_users"))


@capability_required("customers")
def user_toggle(request, pk):
    target = _target(request, pk, can_remove)
    form = ConfirmForm(*form_args(request)[:1])
    action = "Deactivate" if target.is_active else "Activate"
    if request.method == "POST" and form.is_valid():
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        return done(request, f"User '{target.username}' {'activated' if target.is_active else 'deactivated'}.", to=reverse("staff_users"))
    msg = ("They will no longer be able to log in. Their orders and messages are kept." if target.is_active
           else "They will be able to log in again.")
    return modal_form(request, form, title=f"{action} user?", partial="panel/forms/confirm.html", submit=action,
                      danger=target.is_active, cancel_url=reverse("staff_users"),
                      ctx={"message": f"{action} '{target.username}'? {msg}"})


@superuser_required
def user_delete(request, pk):
    target = _target(request, pk, can_remove)
    form = ConfirmForm(*form_args(request)[:1])
    if request.method == "POST" and form.is_valid():
        target.delete()
        return done(request, f"User '{target.username}' deleted.", to=reverse("staff_users"))
    return modal_form(request, form, title="Delete user?", partial="panel/forms/confirm.html", submit="Delete user", danger=True,
                      cancel_url=reverse("staff_users"),
                      ctx={"message": f"Permanently delete '{target.username}'? Their orders are kept (unlinked), "
                                      "but their messages are deleted. Deactivating is usually safer."})


# ---------------------------------------------------------------- analytics
RANGES = (7, 30, 90)


def _days(request):
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    return days if days in RANGES else 30


@capability_required("analytics")
def analytics(request):
    days = _days(request)
    cur, prev = an.range_totals(days), an.range_totals(days, offset=1)
    cur_cur = settings.CURRENCY

    def kpi(label, key, icon, money=False):
        value = cur[key]
        text = f"{cur_cur} {value:,.0f}" if money else f"{value:,}"
        return {"label": label, "value": text, "icon": icon, "delta": an.pct_change(value, prev[key])}

    kpis = [kpi("Revenue", "revenue", "banknotes", True), kpi("Orders", "orders", "shopping-cart"),
            kpi("Average order", "aov", "chart-bar", True), kpi("New customers", "customers", "user-group"),
            kpi("New subscribers", "subscribers", "envelope-open"), kpi("Product views", "views", "eye")]
    rev, people = an.daily_revenue(days), an.daily_people(days)
    status = an.orders_by_status(days)
    products, cats = an.top_products(days), an.revenue_by_category(days)
    data = {
        "currency": cur_cur,
        "revenue": {"labels": [d["day"].strftime("%d %b") for d in rev], "revenue": [float(d["revenue"]) for d in rev],
                    "orders": [d["orders"] for d in rev]},
        "status": {"labels": [x[0] for x in status], "values": [x[1] for x in status]},
        "products": {"labels": [r["product__name"] for r in products], "values": [float(r["revenue"]) for r in products]},
        "categories": {"labels": [r["product__category__name"] for r in cats], "values": [float(r["revenue"]) for r in cats]},
        "people": {"labels": [d["day"].strftime("%d %b") for d in people], "customers": [d["customers"] for d in people],
                   "subscribed": [d["subscribed"] for d in people], "unsubscribed": [d["unsubscribed"] for d in people]},
    }
    return render(request, "panel/analytics.html", {
        "days": days, "ranges": RANGES, "kpis": kpis, "chart_data": data, "top_products": products,
        "top_customers": an.top_customers(days), "most_viewed": an.most_viewed(days),
        "subs": an.subscriber_summary(), "unsubscribed_in_range": cur["unsubscribed"]})


@capability_required("analytics")
def analytics_export(request):
    days = _days(request)
    start, end = an._bounds(days)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="orders-{start}-to-{end}.csv"'
    w = csv.writer(resp)
    w.writerow(["order", "date", "customer", "email", "status", "paid", "total"])
    for o in (Order.objects.filter(created__date__range=(start, end)).annotate(t=Sum(LINE_TOTAL)).order_by("created")):
        w.writerow([o.pk, timezone.localtime(o.created).strftime("%Y-%m-%d %H:%M"), o.name, o.email, o.status, o.paid, o.t or 0])
    return resp
