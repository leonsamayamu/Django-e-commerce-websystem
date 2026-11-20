from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, F
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OrderStatusForm, ProductForm
from .models import Order, OrderItem, Product


def staff_required(view):
    """Must be logged in AND is_staff. Customers get redirected to login."""
    return login_required(user_passes_test(lambda u: u.is_staff, login_url="login")(view))


@staff_required
def dashboard(request):
    revenue = OrderItem.objects.exclude(order__status="cancelled").aggregate(
        t=Sum(F("price") * F("quantity")))["t"] or 0
    return render(request, "staff/dashboard.html", {
        "order_count": Order.objects.count(),
        "pending_count": Order.objects.filter(status="pending").count(),
        "product_count": Product.objects.count(),
        "low_stock": Product.objects.filter(stock__lte=5, available=True),
        "revenue": revenue,
        "recent": Order.objects.all()[:8],
    })


@staff_required
def orders(request):
    qs = Order.objects.annotate(n=Count("items"))
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    return render(request, "staff/orders.html", {
        "orders": qs, "statuses": Order.STATUS_CHOICES, "active": status})


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = OrderStatusForm(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Order updated.")
        return redirect("staff_order_detail", pk=pk)
    return render(request, "staff/order_detail.html", {"order": order, "form": form})


@staff_required
def products(request):
    return render(request, "staff/products.html", {"products": Product.objects.select_related("category")})


@staff_required
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product saved.")
        return redirect("staff_products")
    return render(request, "staff/product_form.html", {"form": form, "product": product})
