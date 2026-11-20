from pathlib import Path
import os

<<<<<<< HEAD
from django.urls import reverse_lazy

=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
BASE_DIR = Path(__file__).resolve().parent.parent
# Development only: set DJANGO_SECRET_KEY and DEBUG=0 in production.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"] if DEBUG else os.environ.get("ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
<<<<<<< HEAD
    "unfold",  # admin theme: must come before django.contrib.admin
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "store",
    "accounts",
    "support",
    "panel",
    "content",
    "payments",
    "assistant",
=======
    "django.contrib.admin",
    "django.contrib.auth", 
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages", 
    "django.contrib.staticfiles",
    "store",
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
<<<<<<< HEAD
    "accounts.middleware.AdminOnlyMiddleware",
=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
<<<<<<< HEAD
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
=======
    "DIRS": [], "APP_DIRS": True,
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "store.context_processors.cart",
<<<<<<< HEAD
        "support.context_processors.support",
        "panel.context_processors.panel",
        "assistant.context_processors.assistant",
=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CURRENCY = "KES"

# Authentication
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "product_list"
LOGOUT_REDIRECT_URL = "product_list"
<<<<<<< HEAD

# Media (user uploads). In production serve MEDIA_ROOT from nginx or object storage (S3), not Django.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
MAX_PRODUCT_IMAGES = 8

# Shop identity and email. Console backend prints emails in the terminal during development.
SHOP_NAME = os.environ.get("SHOP_NAME", "Django Shop")
SHOP_EMAIL = os.environ.get("SHOP_EMAIL", "shop@example.com")  # receives contact/message notifications
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", SHOP_EMAIL)
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000

# Optional banner above the header, e.g. ANNOUNCEMENT="Free delivery on orders over KES 5,000". Empty = hidden.
SHOP_ANNOUNCEMENT = os.environ.get("ANNOUNCEMENT", "")

# ---- AI assistant (customer chat). The key lives in the environment, never in the database. ----------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ASSISTANT_MODEL = os.environ.get("ASSISTANT_MODEL", "claude-haiku-5-5")

# ---- Payments (PayHero) -------------------------------------------------------------------------
# PayHero must be able to reach your callback URL, so set this to your public https address in production.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}  # use Redis in production

# Fast password hashing while running the test suite only.
import sys
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}  # no stale singletons between tests

# ---- Admin theme (django-unfold) ------------------------------------------------------------
_TEAL = {"50": "oklch(98.4% .014 180.72)", "100": "oklch(95.3% .051 180.801)", "200": "oklch(91% .096 180.426)",
         "300": "oklch(85.5% .138 181.071)", "400": "oklch(77.7% .152 181.912)", "500": "oklch(70.4% .14 182.503)",
         "600": "oklch(60% .118 184.704)", "700": "oklch(51.1% .096 186.391)", "800": "oklch(43.7% .078 188.216)",
         "900": "oklch(38.6% .063 188.416)", "950": "oklch(27.7% .046 192.524)"}


def _nav(title, icon, name):
    return {"title": title, "icon": icon, "link": reverse_lazy(name)}


UNFOLD = {
    "SITE_TITLE": f"{SHOP_NAME} Admin",
    "SITE_HEADER": SHOP_NAME,
    "SITE_SUBHEADER": "Back office",
    "SITE_URL": "/",
    "SITE_SYMBOL": "storefront",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {"primary": _TEAL},
    "DASHBOARD_CALLBACK": "config.dashboard.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {"title": "Overview", "items": [
                _nav("Dashboard", "dashboard", "admin:index"),
                {"title": "Staff panel", "icon": "monitoring", "link": "/staff/analytics/"},
                {"title": "View shop", "icon": "shopping_bag", "link": "/"},
            ]},
            {"title": "Catalog", "items": [
                _nav("Products", "inventory_2", "admin:store_product_changelist"),
                _nav("Categories", "category", "admin:store_category_changelist"),
            ]},
            {"title": "Sales", "items": [
                _nav("Orders", "receipt_long", "admin:store_order_changelist"),
                _nav("Payments", "payments", "admin:payments_payment_changelist"),
                _nav("Payment gateways", "account_balance", "admin:payments_paymentgateway_changelist"),
                _nav("Reviews", "reviews", "admin:store_productreview_changelist"),
            ]},
            {"title": "People", "items": [
                _nav("Users", "group", "admin:auth_user_changelist"),
                _nav("Groups", "badge", "admin:auth_group_changelist"),
                _nav("Profiles", "account_circle", "admin:accounts_profile_changelist"),
            ]},
            {"title": "Communication", "items": [
                _nav("Conversations", "forum", "admin:support_thread_changelist"),
                _nav("Contact inquiries", "mail", "admin:support_contactmessage_changelist"),
                _nav("Subscribers", "mark_email_read", "admin:support_subscriber_changelist"),
                _nav("Newsletters", "campaign", "admin:support_newsletter_changelist"),
                _nav("AI assistant commands", "smart_toy", "admin:assistant_assistantcommand_changelist"),
            ]},
            {"title": "Site", "items": [
                _nav("About sections", "article", "admin:content_aboutsection_changelist"),
                _nav("About photos", "image", "admin:content_aboutphoto_changelist"),
                _nav("Store settings", "settings", "admin:content_storesettings_changelist"),
            ]},
        ],
    },
}
=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
