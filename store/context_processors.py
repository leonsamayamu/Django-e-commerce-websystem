from django.conf import settings
<<<<<<< HEAD
from django.db.models import Count, Q

from .cart import Cart
from .models import Category


def cart(request):
    return {
        "cart_count": len(Cart(request)),
        "currency": settings.CURRENCY,
        "shop_name": settings.SHOP_NAME,
        "shop_email": settings.SHOP_EMAIL,
        "announcement": settings.SHOP_ANNOUNCEMENT,
        # Lazy queryset: only hits the database on pages whose sidebar actually lists categories.
        "nav_categories": Category.objects.annotate(
            n=Count("products", filter=Q(products__available=True))),
    }
=======
from .cart import Cart


def cart(request):
    return {"cart_count": len(Cart(request)), "currency": settings.CURRENCY}
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
