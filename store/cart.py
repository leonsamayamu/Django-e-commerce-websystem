from decimal import Decimal
<<<<<<< HEAD

from .models import Product


def make_key(product_id, variant_id=None):
    return f"{product_id}:{variant_id or 0}"


def parse_key(key):
    pid, _, vid = str(key).partition(":")
    return int(pid), int(vid or 0)  # raises ValueError for malformed keys; old carts used just "<pid>"


class Cart:
    """Session cart: {"product_id:variant_id": quantity}. Prices and stock always come from the database."""
=======
from .models import Product


class Cart:
    """Session-based cart: {product_id: quantity}. Prices always come from the database."""
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault("cart", {})

    def _save(self):
        self.session.modified = True

<<<<<<< HEAD
    def add(self, product, variant=None, quantity=1):
        key = make_key(product.pk, variant.pk if variant else None)
        limit = variant.stock if variant else product.stock
        self.data[key] = max(1, min(self.data.get(key, 0) + quantity, limit))  # never exceed stock
        self._save()

    def set(self, key, quantity):
        item = next((i for i in self if i["key"] == key), None)
        if item is None or quantity <= 0:
            return self.remove(key)
        self.data[key] = min(quantity, item["stock"])
        self._save()

    def remove(self, key):
        self.data.pop(key, None)
=======
    def add(self, product, quantity=1):
        pid = str(product.pk)
        new_qty = self.data.get(pid, 0) + quantity
        self.data[pid] = max(1, min(new_qty, product.stock))  # never exceed stock
        self._save()

    def set(self, product, quantity):
        if quantity <= 0:
            self.remove(product.pk)
        else:
            self.data[str(product.pk)] = min(quantity, product.stock)
            self._save()

    def remove(self, product_id):
        self.data.pop(str(product_id), None)
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
        self._save()

    def clear(self):
        self.session["cart"] = {}
        self._save()

    def __len__(self):
        return sum(self.data.values())

    def __iter__(self):
<<<<<<< HEAD
        parsed = {}
        for key, qty in self.data.items():
            try:
                parsed[key] = (*parse_key(key), qty)
            except ValueError:
                continue
        products = {p.pk: p for p in Product.objects.filter(pk__in={v[0] for v in parsed.values()}, available=True)
                    .prefetch_related("images", "variants")}
        for key, (pid, vid, qty) in parsed.items():
            product = products.get(pid)
            if product is None:
                continue
            variant = None
            if vid:
                variant = next((v for v in product.variants.all() if v.pk == vid and v.available), None)
                if variant is None:
                    continue
            elif product.has_variants:
                continue  # the product gained options after it was added: customer must choose again
            unit = variant.effective_price if variant else product.price
            stock = variant.stock if variant else product.stock
            yield {"key": key, "product": product, "variant": variant, "quantity": qty, "unit_price": unit,
                   "line_total": unit * qty, "stock": stock,
                   "name": f"{product.name} ({variant.name})" if variant else product.name}
=======
        products = Product.objects.filter(pk__in=self.data.keys(), available=True)
        for p in products:
            qty = self.data[str(p.pk)]
            yield {"product": p, "quantity": qty, "line_total": p.price * qty}
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b

    def total(self):
        return sum((i["line_total"] for i in self), Decimal("0"))
