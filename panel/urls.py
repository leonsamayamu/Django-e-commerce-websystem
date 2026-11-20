from django.urls import path

from . import views as v
from . import views_admin as a

urlpatterns = [
    path("staff/", v.dashboard, name="staff_dashboard"),

    path("staff/analytics/", v.analytics, name="staff_analytics"),
    path("staff/analytics/export/", v.analytics_export, name="staff_analytics_export"),

    path("staff/orders/", v.orders, name="staff_orders"),
    path("staff/orders/<int:pk>/", v.order_detail, name="staff_order_detail"),
    path("staff/orders/<int:pk>/status/", v.order_status, name="staff_order_status"),
    path("staff/orders/<int:pk>/invoice/", v.order_invoice, name="staff_order_invoice"),
    path("staff/orders/<int:pk>/invoice.pdf", v.order_invoice_pdf, name="staff_order_invoice_pdf"),

    path("staff/products/", v.products, name="staff_products"),
    path("staff/products/new/", v.product_create, name="staff_product_new"),
    path("staff/products/<int:pk>/edit/", v.product_edit, name="staff_product_edit"),
    path("staff/products/<int:pk>/delete/", v.product_delete, name="staff_product_delete"),

    path("staff/categories/", v.categories, name="staff_categories"),
    path("staff/categories/new/", v.category_create, name="staff_category_new"),
    path("staff/categories/<int:pk>/edit/", v.category_edit, name="staff_category_edit"),
    path("staff/categories/<int:pk>/delete/", v.category_delete, name="staff_category_delete"),

    path("staff/users/", v.users, name="staff_users"),
    path("staff/users/new/", v.user_create, name="staff_user_new"),
    path("staff/users/<int:pk>/edit/", v.user_edit, name="staff_user_edit"),
    path("staff/users/<int:pk>/password/", v.user_password, name="staff_user_password"),
    path("staff/users/<int:pk>/toggle/", v.user_toggle, name="staff_user_toggle"),
    path("staff/users/<int:pk>/delete/", v.user_delete, name="staff_user_delete"),

    path("staff/payments/", a.payments, name="staff_payments"),
    path("staff/payments/<int:pk>/recheck/", a.payment_recheck, name="staff_payment_recheck"),
    path("staff/gateways/", a.gateways, name="staff_gateways"),
    path("staff/gateways/new/", a.gateway_new, name="staff_gateway_new"),
    path("staff/gateways/<int:pk>/edit/", a.gateway_edit, name="staff_gateway_edit"),
    path("staff/gateways/<int:pk>/delete/", a.gateway_delete, name="staff_gateway_delete"),

    path("staff/reviews/", a.reviews, name="staff_reviews"),
    path("staff/reviews/<int:pk>/toggle/", a.review_toggle, name="staff_review_toggle"),
    path("staff/reviews/<int:pk>/delete/", a.review_delete, name="staff_review_delete"),

    path("staff/content/about/", a.about_admin, name="staff_about"),
    path("staff/content/about/edit/", a.about_edit, name="staff_about_edit"),
    path("staff/content/about/sections/new/", a.section_new, name="staff_section_new"),
    path("staff/content/about/sections/<int:pk>/edit/", a.section_edit, name="staff_section_edit"),
    path("staff/content/about/sections/<int:pk>/delete/", a.section_delete, name="staff_section_delete"),
    path("staff/content/about/photos/upload/", a.photo_upload, name="staff_photo_upload"),
    path("staff/content/about/photos/<int:pk>/edit/", a.photo_edit, name="staff_photo_edit"),
    path("staff/content/about/photos/<int:pk>/delete/", a.photo_delete, name="staff_photo_delete"),

    path("staff/settings/", a.store_settings, name="staff_settings"),
    path("staff/settings/edit/", a.store_settings_edit, name="staff_settings_edit"),

    path("staff/assistant/", a.assistant_admin, name="staff_assistant"),
    path("staff/assistant/edit/", a.assistant_edit, name="staff_assistant_edit"),
    path("staff/assistant/commands/new/", a.command_new, name="staff_command_new"),
    path("staff/assistant/commands/<int:pk>/edit/", a.command_edit, name="staff_command_edit"),
    path("staff/assistant/commands/<int:pk>/delete/", a.command_delete, name="staff_command_delete"),
]
