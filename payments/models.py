import secrets

from django.db import models

from . import crypto


def new_token():
    return secrets.token_urlsafe(24)


class PaymentGateway(models.Model):
    """A PayHero payment channel. Credentials are write-only in the UI and encrypted in the database."""
    PROVIDERS = [
        ("payhero_mpesa", "PayHero M-Pesa (Paybill, Till or bank channel)"),
        ("payhero_wallet", "PayHero wallet (SasaPay)"),
    ]
    name = models.CharField(max_length=80, help_text="Shown to customers at checkout, e.g. 'M-Pesa'.")
    provider = models.CharField(max_length=20, choices=PROVIDERS, default="payhero_mpesa")
    channel_id = models.PositiveIntegerField(help_text="PayHero dashboard > Payment Channels > My Payment Channels.")
    credential_id = models.CharField(max_length=60, blank=True, help_text="Optional: your own Daraja credential ID registered on PayHero.")
    username_enc = models.TextField(blank=True, editable=False)
    password_enc = models.TextField(blank=True, editable=False)
    callback_token = models.CharField(max_length=64, unique=True, default=new_token, editable=False)
    enabled = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.name

    # credentials (never returned to templates in full)
    @property
    def api_username(self):
        return crypto.decrypt(self.username_enc)

    @property
    def api_password(self):
        return crypto.decrypt(self.password_enc)

    def set_credentials(self, username=None, password=None):
        if username:
            self.username_enc = crypto.encrypt(username)
        if password:
            self.password_enc = crypto.encrypt(password)

    @property
    def has_credentials(self):
        return bool(self.api_username and self.api_password)

    @property
    def masked_username(self):
        u = self.api_username
        return (u[:3] + "*" * max(len(u) - 3, 3)) if u else "not set"

    @property
    def provider_code(self):
        return "sasapay" if self.provider == "payhero_wallet" else "m-pesa"


class Payment(models.Model):
    STATUS = [("pending", "Pending"), ("success", "Paid"), ("failed", "Failed")]
    order = models.ForeignKey("store.Order", on_delete=models.CASCADE, related_name="payments")
    gateway = models.ForeignKey(PaymentGateway, null=True, on_delete=models.SET_NULL, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=20)
    reference = models.CharField(max_length=40, unique=True)             # our external_reference
    provider_reference = models.CharField(max_length=80, blank=True)     # PayHero 'reference' (used for status checks)
    checkout_request_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    receipt = models.CharField("M-Pesa receipt", max_length=40, blank=True)
    message = models.CharField(max_length=255, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.reference} {self.status}"
