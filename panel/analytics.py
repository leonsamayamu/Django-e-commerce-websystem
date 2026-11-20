"""Sales, customer and newsletter analytics. All queries are aggregated in the database."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from store.models import Order, OrderItem, ProductViewDaily
from support.models import Subscriber

LINE = F("price") * F("quantity")
ZERO = Decimal("0")


def _bounds(days, offset=0):
    end = timezone.localdate() - timedelta(days=offset * days)
    return end - timedelta(days=days - 1), end


def _live_items(days, offset=0):
    start, end = _bounds(days, offset)
    return OrderItem.objects.exclude(order__status="cancelled").filter(order__created__date__range=(start, end))


def range_totals(days, offset=0):
    start, end = _bounds(days, offset)
    agg = _live_items(days, offset).aggregate(revenue=Sum(LINE), units=Sum("quantity"), orders=Count("order", distinct=True))
    revenue, orders = agg["revenue"] or ZERO, agg["orders"] or 0
    subs = Subscriber.objects.filter(created__date__range=(start, end)).count()
    return {
        "revenue": revenue, "orders": orders, "units": agg["units"] or 0,
        "aov": (revenue / orders) if orders else ZERO,
        "customers": User.objects.filter(is_staff=False, date_joined__date__range=(start, end)).count(),
        "subscribers": subs,
        "unsubscribed": Subscriber.objects.filter(unsubscribed_at__date__range=(start, end)).count(),
        "views": ProductViewDaily.objects.filter(day__range=(start, end)).aggregate(v=Sum("views"))["v"] or 0,
    }


def pct_change(current, previous):
    """% change vs the previous period, or None when there is nothing to compare with."""
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _fill(rows, days, keys):
    start, _ = _bounds(days)
    by_day = {r["day"]: r for r in rows}
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        row = by_day.get(d, {})
        out.append({"day": d, **{k: row.get(k) or 0 for k in keys}})
    return out


def daily_revenue(days):
    rows = (_live_items(days).annotate(day=TruncDate("order__created")).values("day")
            .annotate(revenue=Sum(LINE), orders=Count("order", distinct=True)))
    return _fill(rows, days, ["revenue", "orders"])


def daily_people(days):
    start, end = _bounds(days)
    cust = (User.objects.filter(is_staff=False, date_joined__date__range=(start, end))
            .annotate(day=TruncDate("date_joined")).values("day").annotate(n=Count("id")))
    subs = (Subscriber.objects.filter(created__date__range=(start, end))
            .annotate(day=TruncDate("created")).values("day").annotate(n=Count("id")))
    unsubs = (Subscriber.objects.filter(unsubscribed_at__date__range=(start, end))
              .annotate(day=TruncDate("unsubscribed_at")).values("day").annotate(n=Count("id")))
    c, s, u = (_fill(list(x), days, ["n"]) for x in (cust, subs, unsubs))
    return [{"day": c[i]["day"], "customers": c[i]["n"], "subscribed": s[i]["n"], "unsubscribed": u[i]["n"]} for i in range(days)]


def top_products(days, limit=5):
    return list(_live_items(days).values("product_id", "product__name")
                .annotate(revenue=Sum(LINE), units=Sum("quantity")).order_by("-revenue")[:limit])


def revenue_by_category(days):
    return list(_live_items(days).values("product__category__name").annotate(revenue=Sum(LINE)).order_by("-revenue"))


def top_customers(days, limit=5):
    return list(_live_items(days).exclude(order__user=None)
                .values("order__user_id", "order__user__username", "order__user__email")
                .annotate(revenue=Sum(LINE), orders=Count("order", distinct=True)).order_by("-revenue")[:limit])


def orders_by_status(days):
    start, end = _bounds(days)
    counts = dict(Order.objects.filter(created__date__range=(start, end)).values_list("status").annotate(n=Count("id")))
    return [(label, counts.get(key, 0)) for key, label in Order.STATUS_CHOICES]


def most_viewed(days, limit=5):
    start, end = _bounds(days)
    units = {r["product_id"]: r["units"] for r in _live_items(days).values("product_id").annotate(units=Sum("quantity"))}
    rows = (ProductViewDaily.objects.filter(day__range=(start, end)).values("product_id", "product__name")
            .annotate(views=Sum("views")).order_by("-views")[:limit])
    return [{**r, "units": units.get(r["product_id"], 0),
             "conversion": round(units.get(r["product_id"], 0) / r["views"] * 100, 1) if r["views"] else 0} for r in rows]


def subscriber_summary():
    return {"active": Subscriber.objects.filter(active=True).count(),
            "inactive": Subscriber.objects.filter(active=False).count()}
