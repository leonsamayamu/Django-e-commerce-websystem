from django.contrib import admin
<<<<<<< HEAD
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import (Category, Order, OrderItem, Product, ProductImage, ProductReview, ProductVariant,
                     ProductViewDaily)

STATUS_COLORS = {"pending": "warning", "processing": "info", "shipped": "success", "delivered": "success", "cancelled": "danger"}


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    search_fields = ["name"]


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "preview", "position"]
    readonly_fields = ["preview"]

    @admin.display(description="Preview")
    def preview(self, obj):
        return format_html('<img src="{}" alt="" style="height:64px;width:64px;object-fit:cover;border-radius:8px">',
                           obj.image.url) if obj and obj.image else "-"


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 0
    fields = ["name", "sku", "price", "stock", "available", "position"]


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ["thumb", "name", "category", "price", "stock", "available"]
    list_display_links = ["thumb", "name"]
    list_filter = ["category", "available"]
    list_editable = ["price", "stock", "available"]
    search_fields = ["name"]
    list_select_related = ["category"]
    inlines = [ProductVariantInline, ProductImageInline]
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("images")

    @admin.display(description="")
    def thumb(self, obj):
        return format_html('<img src="{}" alt="" style="height:40px;width:40px;object-fit:cover;border-radius:8px">', obj.cover_url)


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "variant", "product_name", "variant_name", "price", "quantity"]
=======
from .models import Category, Product, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "stock", "available"]
    list_filter = ["category", "available"]
    list_editable = ["price", "stock", "available"]
    search_fields = ["name"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "price", "quantity"]
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    can_delete = False


@admin.register(Order)
<<<<<<< HEAD
class OrderAdmin(ModelAdmin):
    list_display = ["id", "name", "user", "show_status", "payment_method", "paid", "courier", "created"]
    list_filter = ["status", "paid", "payment_method", "created"]
    search_fields = ["name", "email", "id"]
    inlines = [OrderItemInline]

    @display(description="Status", ordering="status", label=STATUS_COLORS)
    def show_status(self, obj):
        return obj.status


@admin.register(ProductViewDaily)
class ProductViewDailyAdmin(ModelAdmin):
    list_display = ["product", "day", "views"]
    list_filter = ["day"]
    date_hierarchy = "day"


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = ["product", "user", "rating", "visible", "created"]
    list_filter = ["visible", "rating"]
    search_fields = ["product__name", "user__username", "comment"]
=======
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "user", "status", "created", "paid"]
    list_filter = ["status", "paid", "created"]
    inlines = [OrderItemInline]
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
