"""Context for the Unfold admin dashboard (templates/admin/index.html)."""
import json

from django.conf import settings
from django.contrib.auth.models import User

from panel.analytics import daily_revenue, range_totals
from store.models import Order
from support.models import Subscriber


def dashboard_callback(request, context):
    days = daily_revenue(7)
    totals = range_totals(30)
    chart = json.dumps({
        "labels": [d["day"].strftime("%a") for d in days],
        "datasets": [{"data": [float(d["revenue"]) for d in days], "backgroundColor": "var(--color-primary-500)",
                      "borderRadius": 6}],
    })
    context.update({
        "currency": settings.CURRENCY,
        "kpis": [
            {"label": "Revenue (30 days)", "value": f"{settings.CURRENCY} {totals['revenue']:,.0f}", "icon": "payments"},
            {"label": "Orders (30 days)", "value": totals["orders"], "icon": "receipt_long"},
            {"label": "Pending orders", "value": Order.objects.filter(status="pending").count(), "icon": "pending_actions"},
            {"label": "Customers", "value": User.objects.filter(is_staff=False).count(), "icon": "group"},
            {"label": "Active subscribers", "value": Subscriber.objects.filter(active=True).count(), "icon": "mark_email_read"},
        ],
        "sales_chart": chart,
    })
    return context
