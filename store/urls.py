<<<<<<< HEAD
from django.urls import path

from . import views
=======
from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views, staff_views
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
<<<<<<< HEAD
    path("product/<int:pk>/review/", views.review_submit, name="review_submit"),
    path("product/<int:pk>/review/delete/", views.review_delete, name="review_delete"),
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<str:key>/", views.cart_update, name="cart_update"),
    path("cart/remove/<str:key>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("my-orders/", views.my_orders, name="my_orders"),

    path("order/<str:token>/", views.order_view, name="order_view"),
    path("order/<str:token>/pay/", views.order_pay, name="order_pay"),
    path("order/<str:token>/pay/wait/", views.order_pay_wait, name="order_pay_wait"),
    path("order/<str:token>/pay/status/", views.order_pay_status, name="order_pay_status"),
    path("order/<str:token>/invoice/", views.invoice_view, name="invoice_view"),
    path("order/<str:token>/invoice.pdf", views.invoice_pdf, name="invoice_pdf"),
=======
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),

    # Customer accounts
    path("accounts/login/", views.ShopLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),  # POST only
    path("accounts/register/", views.register, name="register"),
    path("my-orders/", views.my_orders, name="my_orders"),

    # Staff area (is_staff only)
    path("staff/", staff_views.dashboard, name="staff_dashboard"),
    path("staff/orders/", staff_views.orders, name="staff_orders"),
    path("staff/orders/<int:pk>/", staff_views.order_detail, name="staff_order_detail"),
    path("staff/products/", staff_views.products, name="staff_products"),
    path("staff/products/new/", staff_views.product_edit, name="staff_product_new"),
    path("staff/products/<int:pk>/edit/", staff_views.product_edit, name="staff_product_edit"),
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
]
