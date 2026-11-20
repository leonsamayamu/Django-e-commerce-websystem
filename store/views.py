<<<<<<< HEAD
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import Profile
from content.models import StoreSettings
from payments import payhero, services
from payments.models import PaymentGateway
from support.emails import absolute_url, notify_shop, send_safely

from .cart import Cart
from .invoices import build_pdf, invoice_data
from .models import Order, OrderItem, Product, ProductReview, ProductVariant, ProductViewDaily

SORTS = {"new": "-created", "price_asc": "price", "price_desc": "-price", "name": "name"}
PAGE_SIZE = 12


def _money(value):
    try:
        d = Decimal(value)
        return d if d.is_finite() and d >= 0 else None
    except (InvalidOperation, TypeError):
        return None


def _safe_back(request, default):
    nxt = request.POST.get("next", "")
    return nxt if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}) else default


# ------------------------------------------------------------------ catalogue
def product_list(request):
    qs = (Product.objects.filter(available=True).select_related("category").prefetch_related("images", "variants")
          .annotate(avg_rating=Avg("reviews__rating", filter=Q(reviews__visible=True)),
                    review_count=Count("reviews", filter=Q(reviews__visible=True), distinct=True)))
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    lo, hi = _money(request.GET.get("min")), _money(request.GET.get("max"))
    sort = request.GET.get("sort", "new")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat.isdigit():
        qs = qs.filter(category_id=cat)
    if lo is not None:
        qs = qs.filter(price__gte=lo)
    if hi is not None:
        qs = qs.filter(price__lte=hi)
    qs = qs.order_by(SORTS.get(sort, "-created"), "-pk")
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    filtered = bool(q or cat or lo is not None or hi is not None)
    return render(request, "store/product_list.html", {
        "page": page, "q": q, "active_category": cat, "min": request.GET.get("min", ""),
        "max": request.GET.get("max", ""), "sort": sort, "sorts": SORTS.keys(),
        "query_string": params.urlencode(), "show_hero": not filtered and page.number == 1,
    })


BOT_HINTS = ("bot", "crawl", "spider", "slurp", "preview", "curl", "python-requests")


def _count_view(request, product):
    """Count one view per visitor session per product per day. Staff and bots are ignored."""
    if request.user.is_staff or any(h in request.headers.get("User-Agent", "").lower() for h in BOT_HINTS):
        return
    today = timezone.localdate()
    seen = {k: v for k, v in request.session.get("viewed", {}).items() if v == today.isoformat()}
    if str(product.pk) in seen:
        return
    seen[str(product.pk)] = today.isoformat()
    request.session["viewed"] = seen
    rows = ProductViewDaily.objects.filter(product=product, day=today)
    if not rows.update(views=F("views") + 1):
        try:
            ProductViewDaily.objects.create(product=product, day=today, views=1)
        except IntegrityError:  # two first views at the same moment
            rows.update(views=F("views") + 1)


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related("images", "variants"), pk=pk, available=True)
    _count_view(request, product)
    reviews = list(product.reviews.filter(visible=True).select_related("user"))
    buyers = set(OrderItem.objects.filter(product=product).exclude(order__status="cancelled").values_list("order__user_id", flat=True))
    for r in reviews:
        r.verified = r.user_id in buyers
    mine = next((r for r in reviews if request.user.is_authenticated and r.user_id == request.user.pk), None)
    if request.user.is_authenticated and mine is None:
        mine = ProductReview.objects.filter(product=product, user=request.user).first()  # hidden by staff but still theirs
    avg = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else None
    return render(request, "store/product_detail.html", {
        "product": product, "urls": product.image_urls(), "variants": product.live_variants, "reviews": reviews,
        "avg_rating": avg, "my_review": mine, "stars": range(1, 6)})


@login_required
@require_POST
def review_submit(request, pk):
    product = get_object_or_404(Product, pk=pk, available=True)
    try:
        rating = int(request.POST.get("rating", ""))
    except ValueError:
        rating = 0
    if not 1 <= rating <= 5:
        messages.error(request, "Please choose a rating from 1 to 5 stars.")
    else:
        ProductReview.objects.update_or_create(
            product=product, user=request.user,
            defaults={"rating": rating, "title": request.POST.get("title", "").strip()[:100],
                      "comment": request.POST.get("comment", "").strip()[:1000]})
        messages.success(request, "Thanks for your review!")
    return redirect(reverse("product_detail", args=[pk]) + "#reviews")


@login_required
@require_POST
def review_delete(request, pk):
    ProductReview.objects.filter(product_id=pk, user=request.user).delete()
    messages.success(request, "Your review was deleted.")
    return redirect(reverse("product_detail", args=[pk]) + "#reviews")


# ------------------------------------------------------------------ cart
@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related("variants"), pk=pk, available=True)
=======
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import RegisterForm
from .models import Category, Order, OrderItem, Product


def product_list(request):
    products = Product.objects.filter(available=True).select_related("category")
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat:
        products = products.filter(category_id=cat)
    return render(request, "store/product_list.html", {
        "products": products, "categories": Category.objects.all(),
        "q": q, "active_category": cat,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, available=True)
    return render(request, "store/product_detail.html", {"product": product})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, available=True)
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    try:
        qty = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        qty = 1
<<<<<<< HEAD
    variant, ok, msg = None, True, f"{product.name} added to cart."
    if product.has_variants:
        wanted = request.POST.get("variant", "")
        variant = next((v for v in product.live_variants if str(v.pk) == wanted), None)
        if variant is None:
            ok, msg = False, "Please choose an option first."
    if ok and (variant.stock if variant else product.stock) == 0:
        ok, msg = False, "Out of stock."
    cart = Cart(request)
    if ok:
        cart.add(product, variant, qty)
        if variant:
            msg = f"{product.name} ({variant.name}) added to cart."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": ok, "message": msg, "count": len(cart)})
    (messages.success if ok else messages.error)(request, msg)
    return redirect("cart" if ok else "product_detail", **({} if ok else {"pk": pk}))
=======
    cart = Cart(request)
    if product.stock == 0:
        msg, ok = "Out of stock.", False
    else:
        cart.add(product, qty)
        msg, ok = f"{product.name} added to cart.", True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": ok, "message": msg, "count": len(cart)})
    (messages.success if ok else messages.error)(request, msg)
    return redirect(request.POST.get("next") or "cart")
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b


def cart_detail(request):
    cart = Cart(request)
    return render(request, "store/cart.html", {"items": list(cart), "total": cart.total()})


@require_POST
<<<<<<< HEAD
def cart_update(request, key):
    try:
        Cart(request).set(key, int(request.POST.get("quantity", 1)))
=======
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        Cart(request).set(product, int(request.POST.get("quantity", 1)))
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    except ValueError:
        pass
    return redirect("cart")


@require_POST
<<<<<<< HEAD
def cart_remove(request, key):
    Cart(request).remove(key)
    return redirect("cart")


# ------------------------------------------------------------------ checkout (customers and guests)
FIELDS = ("name", "email", "phone", "address", "notes", "payment_method", "gateway", "mpesa_phone")


def _validate_checkout(data, cfg, gateways):
    errors = []
    if not data["name"]:
        errors.append("Please enter your name.")
    try:
        validate_email(data["email"])
    except ValidationError:
        errors.append("Please enter a valid email address.")
    if len(data["phone"]) < 9:
        errors.append("Please enter a phone number we can reach you on.")
    if not data["address"]:
        errors.append("Please enter a delivery address.")
    method = data["payment_method"]
    if method == "payhero":
        if not gateways:
            errors.append("Mobile money is not available right now.")
        elif not payhero.normalize_phone(data["mpesa_phone"] or data["phone"]):
            errors.append("Enter a valid M-Pesa number, e.g. 0712 345 678.")
    elif method == "cod":
        if not cfg.cod_enabled:
            errors.append("Pay on delivery is not available.")
    else:
        errors.append("Please choose a payment method.")
    return errors


def checkout(request):
    cfg = StoreSettings.load()
    if not request.user.is_authenticated and not cfg.guest_checkout:
        return redirect_to_login(request.get_full_path())
=======
def cart_remove(request, pk):
    Cart(request).remove(pk)
    return redirect("cart")


@login_required
def checkout(request):
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    cart = Cart(request)
    items = list(cart)
    if not items:
        return redirect("product_list")
<<<<<<< HEAD
    gateways = [g for g in PaymentGateway.objects.filter(enabled=True) if g.has_credentials]
    initial = {"name": "", "email": "", "phone": "", "address": "", "notes": "", "mpesa_phone": "",
               "payment_method": "payhero" if gateways else "cod"}
    if request.user.is_authenticated:
        prof, _ = Profile.objects.get_or_create(user=request.user)
        initial.update(name=request.user.get_full_name() or request.user.username, email=request.user.email,
                       phone=prof.phone, address=prof.address)
    values = initial
    if request.method == "POST":
        values = {k: request.POST.get(k, "").strip() for k in FIELDS}
        errors = _validate_checkout(values, cfg, gateways)
        for e in errors:
            messages.error(request, e)
        if not errors:
            try:
                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user if request.user.is_authenticated else None, name=values["name"],
                        email=values["email"], phone=values["phone"], address=values["address"],
                        notes=values["notes"][:500], payment_method=values["payment_method"])
                    for i in items:
                        locked = (ProductVariant.objects.select_for_update().get(pk=i["variant"].pk) if i["variant"]
                                  else Product.objects.select_for_update().get(pk=i["product"].pk))  # no overselling
                        if locked.stock < i["quantity"]:
                            raise ValueError(f"Not enough stock for {i['name']}.")
                        locked.stock -= i["quantity"]
                        locked.save(update_fields=["stock"])
                        OrderItem.objects.create(
                            order=order, product=i["product"], variant=i["variant"], product_name=i["product"].name,
                            variant_name=i["variant"].name if i["variant"] else "", price=i["unit_price"], quantity=i["quantity"])
            except ValueError as e:
                messages.error(request, str(e))
                return redirect("cart")
            if request.user.is_authenticated and not prof.address:  # remember delivery details for next time
                prof.address, prof.phone = values["address"], values["phone"] or prof.phone
                prof.save()
            cart.clear()
            link = absolute_url(request, order.get_absolute_url())
            send_safely(f"Order #{order.pk} received", f"Hello {order.name},\n\nThank you for your order #{order.pk}. "
                        f"Total: KES {order.total()}.\nTrack it and download your invoice here: {link}\n", [order.email])
            notify_shop(f"New order #{order.pk}", f"{order.name} ({order.email}) placed an order for KES {order.total()}. "
                        f"Payment: {order.get_payment_method_display()}.")
            if order.payment_method == "payhero":
                gateway = next((g for g in gateways if str(g.pk) == values["gateway"]), gateways[0])
                services.start_payment(request, order, gateway, values["mpesa_phone"] or values["phone"])
                return redirect("order_pay_wait", token=order.token)
            return redirect(order.get_absolute_url() + "?placed=1")
    return render(request, "store/checkout.html", {
        "items": items, "total": cart.total(), "values": values, "gateways": gateways, "cod_enabled": cfg.cod_enabled})


# ------------------------------------------------------------------ order pages (private link: works for guests too)
def _order(token):
    return get_object_or_404(Order.objects.prefetch_related("items__product", "payments__gateway"), token=token)


def order_view(request, token):
    order = _order(token)
    gateways = [g for g in PaymentGateway.objects.filter(enabled=True) if g.has_credentials]
    return render(request, "store/order_view.html", {
        "order": order, "payments": list(order.payments.all()), "gateways": gateways, "placed": request.GET.get("placed")})


@require_POST
def order_pay(request, token):
    order = _order(token)
    if not order.awaiting_online_payment:
        messages.error(request, "This order does not need an online payment.")
        return redirect(order.get_absolute_url())
    gateway = get_object_or_404(PaymentGateway, pk=request.POST.get("gateway") or 0, enabled=True)
    try:
        services.start_payment(request, order, gateway, request.POST.get("mpesa_phone", "") or order.phone)
    except services.PaymentError as exc:
        messages.error(request, str(exc))
        return redirect(order.get_absolute_url())
    return redirect("order_pay_wait", token=token)


def order_pay_wait(request, token):
    order = _order(token)
    payment = order.payments.first()
    if payment is None:
        return redirect(order.get_absolute_url())
    return render(request, "store/order_pay_wait.html", {"order": order, "payment": payment})


def order_pay_status(request, token):
    order = _order(token)
    payment = order.payments.first()
    if payment is None:
        raise Http404
    if payment.status == "pending":
        payment = services.refresh_payment(payment, order_url=absolute_url(request, order.get_absolute_url()))
    return JsonResponse({"status": payment.status, "message": payment.message, "receipt": payment.receipt,
                         "paid": Order.objects.filter(pk=order.pk, paid=True).exists(), "url": order.get_absolute_url()})


def invoice_view(request, token):
    return render(request, "store/invoice.html", invoice_data(_order(token)))


def invoice_pdf(request, token):
    order = _order(token)
    resp = HttpResponse(build_pdf(order), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="invoice-{order.invoice_number}.pdf"'
    return resp
=======
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()
        if not (name and email and address):
            messages.error(request, "Name, email and address are required.")
        else:
            try:
                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user, name=name, email=email, address=address,
                        phone=request.POST.get("phone", "").strip())
                    for i in items:
                        # Lock the row so two buyers cannot take the last item.
                        p = Product.objects.select_for_update().get(pk=i["product"].pk)
                        if p.stock < i["quantity"]:
                            raise ValueError(f"Not enough stock for {p.name}.")
                        p.stock -= i["quantity"]
                        p.save(update_fields=["stock"])
                        OrderItem.objects.create(order=order, product=p,
                                                 price=p.price, quantity=i["quantity"])
            except ValueError as e:
                messages.error(request, str(e))
                return redirect("cart")
            cart.clear()
            return render(request, "store/order_done.html", {"order": order})
    return render(request, "store/checkout.html", {"items": items, "total": cart.total(), "user_obj": request.user})


class ShopLoginView(LoginView):
    """Staff go to the staff dashboard; customers go back to the shop (or ?next=)."""
    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        return "/staff/" if self.request.user.is_staff else "/"


def register(request):
    if request.user.is_authenticated:
        return redirect("product_list")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account has been created.")
        return redirect(request.GET.get("next") or "product_list")
    return render(request, "registration/register.html", {"form": form})
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b


@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related("items__product")
    return render(request, "store/my_orders.html", {"orders": orders})
