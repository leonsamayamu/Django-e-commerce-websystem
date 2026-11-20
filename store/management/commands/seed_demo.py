<<<<<<< HEAD
import io

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from assistant.models import AssistantCommand
from content.models import AboutPage, AboutPhoto, AboutSection, StoreSettings
from store.models import Category, Product, ProductImage, ProductVariant

COLORS = [("#0f766e", "#5eead4"), ("#1d4ed8", "#93c5fd"), ("#b45309", "#fcd34d")]


def demo_photo(title, n, subtitle="Demo photo"):
    bg, fg = COLORS[n % len(COLORS)]
    img = Image.new("RGB", (800, 600), bg)
    draw = ImageDraw.Draw(img)
    draw.ellipse((520, -80, 940, 340), fill=fg)
    try:
        font = ImageFont.load_default(size=54)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((50, 230), title, fill="white", font=font)
    draw.text((50, 320), f"{subtitle} {n + 1}", fill="white", font=font)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return ContentFile(buf.getvalue(), name=f"demo{n}.jpg")


STAFF = [("staff", "manager", "Demo Manager"), ("warehouse", "warehouse", "Demo Warehouse"), ("delivery", "delivery", "Demo Courier"),
         ("support", "support", "Demo Support"), ("marketing", "marketing", "Demo Marketing")]

COMMANDS = [
    ("shipping", "Shipping", "We deliver within 2-3 working days. Nairobi delivery is KES 200; other towns are quoted at checkout confirmation."),
    ("returns", "Returns", "Unused items can be returned within 7 days of delivery. Contact us with your order number to arrange a return."),
    ("payments", "Payments", "You can pay with M-Pesa at checkout or pay cash when your order is delivered."),
    ("hours", "Opening hours", "Our team replies to messages Monday to Saturday, 8am to 6pm."),
]


class Command(BaseCommand):
    help = "Create demo data: products with photos, options, staff of every role, assistant commands and About content. Development only."
=======
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from store.models import Category, Product


class Command(BaseCommand):
    help = "Create demo products and demo accounts (development only)."
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b

    def handle(self, *args, **opts):
        shoes, _ = Category.objects.get_or_create(name="Shoes")
        bags, _ = Category.objects.get_or_create(name="Bags")
<<<<<<< HEAD
        for cat, name, price, stock in [(shoes, "Running Shoe", "4500", 0), (shoes, "Leather Boot", "7200", 4),
                                        (bags, "Backpack", "3200", 0), (bags, "Tote Bag", "1800", 3)]:
            product, _ = Product.objects.get_or_create(
                category=cat, name=name,
                defaults={"price": price, "stock": stock, "description": f"Demo {name}. Replace with real details."})
            if not product.images.exists():
                for n in range(3):
                    ProductImage.objects.create(product=product, image=demo_photo(name, n), position=n)
        for product_name, options in (("Running Shoe", [("Size 40", 5, None), ("Size 41", 3, None), ("Size 42", 2, None), ("Size 43", 0, None)]),
                                      ("Backpack", [("Black", 6, None), ("Navy", 4, None), ("Limited edition", 2, "3800")])):
            product = Product.objects.get(name=product_name)
            if not product.variants.exists():
                for i, (label, stock, price) in enumerate(options):
                    ProductVariant.objects.create(product=product, name=label, stock=stock, price=price, position=i)

        if not User.objects.filter(username="customer").exists():
            User.objects.create_user("customer", "customer@example.com", "customer12345", first_name="Demo Customer")
        for username, role, name in STAFF:
            if not User.objects.filter(username=username).exists():
                u = User.objects.create_user(username, f"{username}@example.com", "staff12345", first_name=name, is_staff=True)
                u.profile.staff_role = role
                u.profile.save()

        for i, (trigger, title, text) in enumerate(COMMANDS):
            AssistantCommand.objects.get_or_create(trigger=trigger, defaults={"title": title, "response": text, "position": i,
                                                   "keywords": {"shipping": "shipping, delivery, deliver", "returns": "return, refund",
                                                                "payments": "pay, payment, mpesa", "hours": "hours, open, opening"}[trigger]})

        cfg = StoreSettings.load()
        if cfg.business_name == "My Shop":
            cfg.business_name, cfg.address, cfg.phone, cfg.email = "Demo Shop Ltd", "Moi Avenue, Nairobi", "0700 000 000", "hello@example.com"
            cfg.save()
        AboutPage.load()
        if not AboutSection.objects.exists():
            for i, (h, b) in enumerate([("Our story", "Replace this text with the story of your business: who you are, when you started and what you care about."),
                                        ("Quality promise", "Every item is checked before it ships. If something is not right, contact us and we will fix it."),
                                        ("Fast support", "Message the shop from your account, ask the assistant, or use the contact form.")]):
                AboutSection.objects.create(heading=h, body=b, position=i)
        if not AboutPhoto.objects.exists():
            for n, cap in enumerate(["Our shop front", "Packing orders", "The team"]):
                AboutPhoto.objects.create(image=demo_photo("About us", n, cap), caption=cap, position=n)
        self.stdout.write(self.style.SUCCESS(
            "Demo data ready. customer/customer12345; staff logins (password staff12345): staff (manager), warehouse, delivery, support, marketing."))
=======
        for cat, name, price, stock in [(shoes, "Running Shoe", "4500", 10), (shoes, "Leather Boot", "7200", 4),
                                        (bags, "Backpack", "3200", 15), (bags, "Tote Bag", "1800", 3)]:
            Product.objects.get_or_create(category=cat, name=name,
                defaults={"price": price, "stock": stock, "description": f"Demo {name}."})
        if not User.objects.filter(username="customer").exists():
            User.objects.create_user("customer", "customer@example.com", "customer12345", first_name="Demo Customer")
        if not User.objects.filter(username="staff").exists():
            User.objects.create_user("staff", "staff@example.com", "staff12345", first_name="Demo Staff", is_staff=True)
        self.stdout.write(self.style.SUCCESS("Demo data ready. customer/customer12345, staff/staff12345"))
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
