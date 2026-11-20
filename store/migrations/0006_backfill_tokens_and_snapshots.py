import secrets

from django.db import migrations


def backfill(apps, schema_editor):
    Order = apps.get_model("store", "Order")
    OrderItem = apps.get_model("store", "OrderItem")
    for order in Order.objects.filter(token__isnull=True):
        order.token = secrets.token_urlsafe(24)
        order.save(update_fields=["token"])
    for item in OrderItem.objects.filter(product_name="").select_related("product"):
        item.product_name = item.product.name
        item.save(update_fields=["product_name"])


class Migration(migrations.Migration):
    dependencies = [("store", "0005_order_courier_order_notes_order_payment_method_and_more")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
