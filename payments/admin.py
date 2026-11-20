from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Payment, PaymentGateway


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(ModelAdmin):
    """API credentials are write-only: add or change them in the staff panel (Payment gateways), not here."""
    list_display = ["name", "provider", "channel_id", "enabled", "has_credentials"]
    fields = ["name", "provider", "channel_id", "credential_id", "enabled", "position"]

    @admin.display(boolean=True, description="Credentials saved")
    def has_credentials(self, obj):
        return obj.has_credentials


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ["reference", "order", "amount", "phone", "status", "receipt", "created"]
    list_filter = ["status", "gateway"]
    search_fields = ["reference", "receipt", "phone", "order__name"]
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
