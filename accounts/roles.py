"""Staff roles and what each one may do in the panel. Superusers (the shop admins) can do everything."""

ALL_CAPS = {
    "dashboard", "catalog", "orders", "orders_fulfil", "orders_manage", "invoices", "payments_view", "customers",
    "messages", "inquiries", "reviews", "marketing", "analytics", "content", "admin",
}
ROLE_LABELS = {"manager": "Manager", "warehouse": "Warehouse", "delivery": "Delivery",
               "support": "Customer support", "marketing": "Marketing"}
ROLE_CAPS = {
    "manager": ALL_CAPS - {"admin"},
    "warehouse": {"dashboard", "catalog", "orders", "orders_fulfil"},
    "delivery": {"dashboard", "orders", "orders_fulfil"},
    "support": {"dashboard", "orders", "invoices", "messages", "inquiries", "reviews"},
    "marketing": {"dashboard", "marketing", "analytics", "content", "reviews"},
}
# Which order statuses a role may set (managers and superusers may set any).
ALLOWED_STATUSES = {
    "warehouse": {"pending", "processing", "shipped"},
    "delivery": {"shipped", "out_for_delivery", "delivered"},
}
ROLE_DESCRIPTIONS = {
    "manager": "Everything except shop-admin settings (payment gateways, assistant, store settings).",
    "warehouse": "Products and stock, and moving orders through processing and shipped.",
    "delivery": "Sees only orders assigned to them; marks them out for delivery or delivered.",
    "support": "Messages, inquiries, reviews, and read-only orders and invoices.",
    "marketing": "Analytics, subscribers, newsletters, About page content and reviews.",
}


def role_of(user):
    """'admin' for superusers, the staff role for staff, '' for customers. Legacy staff without a role act as managers."""
    if not user.is_authenticated:
        return ""
    if user.is_superuser:
        return "admin"
    if not user.is_staff:
        return ""
    profile = getattr(user, "profile", None)
    return (profile.staff_role if profile and profile.staff_role else "manager")


def caps_for(user):
    role = role_of(user)
    if role == "admin":
        return set(ALL_CAPS)
    return set(ROLE_CAPS.get(role, ()))


def allowed_statuses(user):
    role = role_of(user)
    return None if role in ("admin", "manager") else ALLOWED_STATUSES.get(role, set())  # None = any
