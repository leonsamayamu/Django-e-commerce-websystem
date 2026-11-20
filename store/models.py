<<<<<<< HEAD
import json
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F
from django.templatetags.static import static
from django.urls import reverse

from .images import IMAGE_VALIDATORS, optimize_image, product_image_path
=======
from django.conf import settings
from django.db import models
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
<<<<<<< HEAD
    stock = models.PositiveIntegerField(default=0, help_text="Used only when the product has no variants.")
    image_url = models.URLField(blank=True, help_text="Optional fallback if no photos are uploaded.")
=======
    stock = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True)
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.name

<<<<<<< HEAD
    # ---- photos
    def image_urls(self):
        """All photo URLs, cover first. Use prefetch_related('images') in list views."""
        urls = [i.image.url for i in self.images.all()]
        if not urls and self.image_url:
            urls = [self.image_url]
        return urls or [static("store/placeholder.svg")]

    @property
    def cover_url(self):
        return self.image_urls()[0]

    @property
    def gallery_json(self):
        return json.dumps(self.image_urls())

    # ---- variants (size, colour...). Prefetch 'variants' in list views.
    @property
    def has_variants(self):
        return len(self.variants.all()) > 0

    @property
    def live_variants(self):
        return [v for v in self.variants.all() if v.available]

    @property
    def total_stock(self):
        return sum(v.stock for v in self.live_variants) if self.has_variants else self.stock

    @property
    def lowest_price(self):
        prices = [v.effective_price for v in self.live_variants]
        return min(prices) if prices else self.price

    @property
    def price_varies(self):
        return len({v.effective_price for v in self.live_variants}) > 1

    @property
    def variants_json(self):
        return json.dumps([{"id": v.pk, "name": v.name, "price": str(v.effective_price), "stock": v.stock}
                           for v in self.live_variants])


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=80, help_text="e.g. Size 42 / Black")
    sku = models.CharField("SKU", max_length=40, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                help_text="Leave empty to use the product price.")
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product} - {self.name}"

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.price


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_path, validators=IMAGE_VALIDATORS)
    position = models.PositiveSmallIntegerField(default=0)  # 0 = cover photo
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product} photo {self.position}"

    def save(self, *args, **kwargs):
        if self.image and not getattr(self.image, "_committed", True):  # new upload
            self.image = optimize_image(self.image.file)
        super().save(*args, **kwargs)


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=100, blank=True)
    comment = models.TextField(max_length=1000, blank=True)
    visible = models.BooleanField(default=True, help_text="Staff can hide a review without deleting it.")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]
        constraints = [models.UniqueConstraint(fields=["product", "user"], name="one_review_per_user_product")]

    def __str__(self):
        return f"{self.product} - {self.rating}/5 by {self.user}"

=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"), ("processing", "Processing"), ("shipped", "Shipped"),
<<<<<<< HEAD
        ("out_for_delivery", "Out for delivery"), ("delivered", "Delivered"), ("cancelled", "Cancelled"),
    ]
    PAYMENT_CHOICES = [("cod", "Pay on delivery"), ("payhero", "Mobile money (M-Pesa)")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="orders")  # empty for guest orders
    token = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="cod")
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="deliveries")
=======
        ("delivered", "Delivered"), ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="orders")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField()
<<<<<<< HEAD
    notes = models.TextField(blank=True, max_length=500)
=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    created = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Order #{self.pk} - {self.name}"

<<<<<<< HEAD
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(24)  # unguessable link for guests and emails
        super().save(*args, **kwargs)

    def total(self):
        return sum((i.line_total() for i in self.items.all()), Decimal("0"))

    @property
    def is_guest(self):
        return self.user_id is None

    @property
    def invoice_number(self):
        from content.models import StoreSettings
        return f"{StoreSettings.load().invoice_prefix}{self.pk:06d}"

    def get_absolute_url(self):
        return reverse("order_view", args=[self.token])

    @property
    def awaiting_online_payment(self):
        return self.payment_method == "payhero" and not self.paid and self.status != "cancelled"
=======
    def total(self):
        return sum(i.line_total() for i in self.items.all())
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
<<<<<<< HEAD
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=200, blank=True)  # snapshots keep invoices correct if a product is renamed
    variant_name = models.CharField(max_length=80, blank=True)
=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of purchase
    quantity = models.PositiveIntegerField()

    def line_total(self):
        return self.price * self.quantity
<<<<<<< HEAD

    @property
    def display_name(self):
        base = self.product_name or self.product.name
        return f"{base} ({self.variant_name})" if self.variant_name else base

    def adjust_stock(self, sign):
        """sign=+1 returns the items to stock (cancellation), -1 takes them again."""
        if self.variant_id:
            ProductVariant.objects.filter(pk=self.variant_id).update(stock=F("stock") + sign * self.quantity)
        else:
            Product.objects.filter(pk=self.product_id).update(stock=F("stock") + sign * self.quantity)

    def available_stock(self):
        return self.variant.stock if self.variant_id else self.product.stock


class ProductViewDaily(models.Model):
    """First-party, privacy-friendly view counter: one row per product per day, no personal data."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="daily_views")
    day = models.DateField()
    views = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "day"], name="unique_product_day_views")]
        ordering = ["-day"]

    def __str__(self):
        return f"{self.product} {self.day}: {self.views}"
=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
