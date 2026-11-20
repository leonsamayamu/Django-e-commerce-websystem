from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from panel import analytics as an
from panel.templatetags.panel_ui import icon
from store.models import Category, Order, OrderItem, Product, ProductViewDaily
from support.models import Subscriber

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
PW = "Tr0ub4dor&3-xyz"


class AnalyticsBase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Shoes")
        self.p1 = Product.objects.create(category=self.cat, name="Runner", price="100.00", stock=50)
        self.p2 = Product.objects.create(category=self.cat, name="Boot", price="50.00", stock=50)
        self.staff = User.objects.create_user("staff", "s@x.com", PW, is_staff=True)
        self.cust = User.objects.create_user("cust", "c@x.com", PW)

    def order(self, product, qty, status="delivered", days_ago=0, user=None):
        o = Order.objects.create(user=user or self.cust, name="N", email="n@x.com", address="a", status=status)
        OrderItem.objects.create(order=o, product=product, price=product.price, quantity=qty)
        Order.objects.filter(pk=o.pk).update(created=timezone.now() - timedelta(days=days_ago))
        return o


class AnalyticsCalculationTests(AnalyticsBase):
    def test_totals_exclude_cancelled_and_other_periods(self):
        self.order(self.p1, 2)                                   # 200 this period
        self.order(self.p2, 1, days_ago=3)                       # 50 this period
        self.order(self.p1, 5, status="cancelled")               # ignored
        self.order(self.p1, 1, days_ago=40)                      # outside a 30 day window
        t = an.range_totals(30)
        self.assertEqual((t["revenue"], t["orders"], t["units"]), (Decimal("250"), 2, 3))
        self.assertEqual(t["aov"], Decimal("125"))
        self.assertEqual(an.range_totals(30, offset=1)["revenue"], Decimal("100"))

    def test_pct_change(self):
        self.assertEqual(an.pct_change(150, 100), 50.0)
        self.assertEqual(an.pct_change(50, 100), -50.0)
        self.assertIsNone(an.pct_change(10, 0))

    def test_daily_series_is_zero_filled(self):
        self.order(self.p1, 1)
        rows = an.daily_revenue(7)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[-1]["revenue"], Decimal("100"))
        self.assertTrue(all(r["revenue"] == 0 for r in rows[:-1]))

    def test_top_products_categories_customers_status(self):
        self.order(self.p1, 1)
        self.order(self.p2, 5)
        self.order(self.p2, 1, status="cancelled")
        self.assertEqual([r["product__name"] for r in an.top_products(30)], ["Boot", "Runner"])
        self.assertEqual(an.revenue_by_category(30)[0]["product__category__name"], "Shoes")
        self.assertEqual(an.top_customers(30)[0]["order__user__username"], "cust")
        self.assertEqual(dict(an.orders_by_status(30))["Cancelled"], 1)

    def test_people_and_most_viewed(self):
        Subscriber.objects.create(email="a@x.com")
        Subscriber.objects.create(email="b@x.com", active=False, unsubscribed_at=timezone.now())
        t = an.range_totals(7)
        self.assertEqual((t["subscribers"], t["unsubscribed"], t["customers"]), (2, 1, 1))
        ProductViewDaily.objects.create(product=self.p1, day=timezone.localdate(), views=20)
        self.order(self.p1, 2)
        top = an.most_viewed(30)[0]
        self.assertEqual((top["views"], top["units"], top["conversion"]), (20, 2, 10.0))


class AnalyticsPageTests(AnalyticsBase):
    def test_permissions(self):
        self.assertEqual(self.client.get(reverse("staff_analytics")).status_code, 302)
        self.client.force_login(self.cust)
        self.assertEqual(self.client.get(reverse("staff_analytics")).status_code, 403)
        self.assertEqual(self.client.get(reverse("staff_analytics_export")).status_code, 403)

    def test_page_renders_with_data_and_bad_range_falls_back(self):
        self.order(self.p1, 2)
        self.client.force_login(self.staff)
        r = self.client.get(reverse("staff_analytics"), {"days": "999"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["days"], 30)
        self.assertContains(r, "chart.umd.min.js")
        self.assertContains(r, 'id="analytics-data"')
        self.assertContains(r, "KES 200")
        for days in (7, 90):
            self.assertEqual(self.client.get(reverse("staff_analytics"), {"days": days}).status_code, 200)

    def test_csv_export(self):
        o = self.order(self.p1, 2)
        self.client.force_login(self.staff)
        r = self.client.get(reverse("staff_analytics_export"), {"days": 7})
        self.assertEqual(r["Content-Type"], "text/csv")
        body = r.content.decode()
        self.assertIn("order,date,customer", body)
        self.assertIn(f"{o.pk},", body)
        self.assertIn("200", body)

    def test_icons(self):
        self.assertIn("<svg", icon("cube"))
        self.assertEqual(icon("does-not-exist"), "")


class ProductViewTrackingTests(AnalyticsBase):
    def views(self):
        return sum(ProductViewDaily.objects.values_list("views", flat=True))

    def test_counts_once_per_session_per_day(self):
        url = reverse("product_detail", args=[self.p1.pk])
        self.client.get(url)
        self.client.get(url)
        self.assertEqual(self.views(), 1)
        self.client.get(reverse("product_detail", args=[self.p2.pk]))
        self.assertEqual(self.views(), 2)
        from django.test import Client
        Client().get(url)  # a different visitor
        self.assertEqual(self.views(), 3)

    def test_staff_and_bots_not_counted(self):
        url = reverse("product_detail", args=[self.p1.pk])
        self.client.get(url, HTTP_USER_AGENT="Googlebot/2.1")
        self.assertEqual(self.views(), 0)
        self.client.force_login(self.staff)
        self.client.get(url)
        self.assertEqual(self.views(), 0)


class SubscriptionDisplayTests(AnalyticsBase):
    def test_staff_subscribers_page_shows_account_link_and_filters(self):
        Subscriber.objects.create(email="c@x.com")                       # matches customer account
        Subscriber.objects.create(email="guest@x.com")
        Subscriber.objects.create(email="old@x.com", active=False)
        self.client.force_login(self.staff)
        r = self.client.get(reverse("staff_subscribers"))
        self.assertContains(r, "@cust")
        self.assertContains(r, "Active account")
        self.assertContains(r, "Guest")
        self.assertNotContains(r, "old@x.com")                           # default tab = active
        self.assertContains(self.client.get(reverse("staff_subscribers"), {"status": "inactive"}), "old@x.com")
        self.assertContains(self.client.get(reverse("staff_subscribers"), {"status": "all"}), "old@x.com")
        self.assertContains(self.client.get(reverse("staff_subscribers"), {"q": "guest"}), "guest@x.com")

    def test_new_subscription_shows_up_for_staff_immediately(self):
        self.client.post(reverse("subscribe"), {"email": "fresh@x.com", "next": "/"})
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("staff_subscribers")), "fresh@x.com")
        self.assertContains(self.client.get(reverse("staff_dashboard")), "fresh@x.com")  # newest subscribers card
        self.assertEqual(self.client.get(reverse("staff_dashboard")).context["active_subs"], 1)

    def test_users_list_shows_newsletter_status_and_filter(self):
        Subscriber.objects.create(email="C@X.com")                       # case-insensitive match
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("staff_users")), "Subscribed")
        r = self.client.get(reverse("staff_users"), {"role": "subscribed"})
        self.assertContains(r, "c@x.com")
        self.assertNotContains(r, "s@x.com")

    def test_customer_sees_status_and_can_toggle_in_profile(self):
        self.client.force_login(self.cust)
        self.assertContains(self.client.get(reverse("profile")), "Not subscribed")
        self.client.post(reverse("newsletter_toggle"), {})
        self.assertTrue(Subscriber.objects.get(email="c@x.com").active)
        page = self.client.get(reverse("profile"))
        self.assertContains(page, "Subscribed")
        self.assertContains(self.client.get(reverse("product_list")), "You are subscribed with c@x.com")  # footer
        self.client.post(reverse("newsletter_toggle"), {"action": "unsubscribe"})
        sub = Subscriber.objects.get(email="c@x.com")
        self.assertFalse(sub.active)
        self.assertIsNotNone(sub.unsubscribed_at)

    def test_subscribing_with_own_email_again_says_so(self):
        Subscriber.objects.create(email="c@x.com")
        self.client.force_login(self.cust)
        r = self.client.post(reverse("subscribe"), {"email": "c@x.com", "next": "/"}, follow=True)
        self.assertContains(r, "You are already subscribed")
        r = self.client.post(reverse("subscribe"), {"email": "other@x.com", "next": "/"}, follow=True)
        self.assertContains(r, "Thanks for subscribing")  # generic reply for other addresses

    def test_registration_opt_in_creates_subscriber(self):
        data = {"username": "new1", "first_name": "N", "email": "new1@x.com", "password1": PW, "password2": PW}
        self.client.post(reverse("register"), {**data, "subscribe": "on"})
        self.assertTrue(Subscriber.objects.filter(email="new1@x.com", active=True).exists())
        from django.test import Client
        Client().post(reverse("register"), {**data, "username": "new2", "email": "new2@x.com"})
        self.assertFalse(Subscriber.objects.filter(email="new2@x.com").exists())  # opt-in only

    def test_toggle_requires_login(self):
        self.assertEqual(self.client.post(reverse("newsletter_toggle"), {}).status_code, 302)
