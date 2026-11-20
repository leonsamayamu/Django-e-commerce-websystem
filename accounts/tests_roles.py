from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.roles import caps_for, role_of
from store.models import Category, Order, OrderItem, Product

PW = "Tr0ub4dor&3-xyz"
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def staff(username, role):
    u = User.objects.create_user(username, f"{username}@x.com", PW, is_staff=True)
    u.profile.staff_role = role
    u.profile.save()
    return u


class RoleBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "boss@x.com", PW)
        self.manager = staff("mgr", "manager")
        self.warehouse = staff("wh", "warehouse")
        self.courier = staff("courier", "delivery")
        self.other_courier = staff("courier2", "delivery")
        self.support = staff("sup", "support")
        self.marketing = staff("mkt", "marketing")
        self.cust = User.objects.create_user("cust", "cust@x.com", PW)
        cat = Category.objects.create(name="C")
        self.product = Product.objects.create(category=cat, name="Widget", price="100.00", stock=10)

    def order(self, courier=None, status="shipped", method="cod", paid=False):
        o = Order.objects.create(user=self.cust, name="Cust", email="cust@x.com", phone="0712345678", address="Nairobi",
                                 status=status, payment_method=method, paid=paid, courier=courier)
        OrderItem.objects.create(order=o, product=self.product, product_name="Widget", price="100.00", quantity=1)
        return o

    def code(self, user, name, *args, ajax=False):
        self.client.force_login(user)
        return self.client.get(reverse(name, args=args), **(AJAX if ajax else {})).status_code


class AdminLockoutTests(RoleBase):
    def test_django_admin_is_for_superusers_only(self):
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)  # anonymous can reach the login form
        for user in (self.manager, self.warehouse, self.courier, self.cust):
            self.client.force_login(user)
            for path in ("/admin/", "/admin/store/product/", "/admin/auth/user/", "/admin/login/"):
                self.assertEqual(self.client.get(path).status_code, 404, f"{user.username} {path}")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_admin_site_itself_refuses_non_superusers(self):
        from django.contrib import admin
        from django.test import RequestFactory
        req = RequestFactory().get("/admin/")
        req.user = self.manager
        self.assertFalse(admin.site.has_permission(req))
        req.user = self.admin
        self.assertTrue(admin.site.has_permission(req))

    def test_staff_never_see_a_link_to_the_admin_site(self):
        pages = ["staff_dashboard", "staff_orders", "staff_products", "staff_users", "staff_messages"]
        for user in (self.manager, self.warehouse, self.courier, self.support, self.marketing):
            self.client.force_login(user)
            for name in pages:
                r = self.client.get(reverse(name))
                if r.status_code == 200:
                    self.assertNotContains(r, "/admin/", msg_prefix=f"{user.username} {name}")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("staff_dashboard")), 'href="/admin/"')  # shop admins keep it


class RolePermissionTests(RoleBase):
    def test_capabilities_per_role(self):
        self.assertEqual(role_of(self.cust), "")
        self.assertEqual(role_of(self.admin), "admin")
        self.assertIn("admin", caps_for(self.admin))
        for u in (self.manager, self.warehouse, self.courier, self.support, self.marketing):
            self.assertNotIn("admin", caps_for(u))
        self.assertIn("catalog", caps_for(self.warehouse))
        self.assertNotIn("analytics", caps_for(self.courier))

    def test_legacy_staff_without_role_act_as_managers(self):
        legacy = User.objects.create_user("old", "old@x.com", PW, is_staff=True)
        self.assertEqual(role_of(legacy), "manager")
        self.assertEqual(self.code(legacy, "staff_products"), 200)

    def test_access_matrix(self):
        o = self.order(courier=self.courier)
        matrix = {
            "staff_dashboard": {"mgr", "wh", "courier", "sup", "mkt", "boss"},
            "staff_products": {"mgr", "wh", "boss"},
            "staff_categories": {"mgr", "wh", "boss"},
            "staff_orders": {"mgr", "wh", "courier", "sup", "boss"},
            "staff_users": {"mgr", "boss"},
            "staff_analytics": {"mgr", "mkt", "boss"},
            "staff_payments": {"mgr", "boss"},
            "staff_messages": {"mgr", "sup", "boss"},
            "staff_contacts": {"mgr", "sup", "boss"},
            "staff_reviews": {"mgr", "sup", "mkt", "boss"},
            "staff_subscribers": {"mgr", "mkt", "boss"},
            "staff_newsletter": {"mgr", "mkt", "boss"},
            "staff_about": {"mgr", "mkt", "boss"},
            "staff_gateways": {"boss"},
            "staff_assistant": {"boss"},
            "staff_settings": {"boss"},
        }
        people = {"mgr": self.manager, "wh": self.warehouse, "courier": self.courier, "sup": self.support,
                  "mkt": self.marketing, "boss": self.admin}
        for name, allowed in matrix.items():
            for key, user in people.items():
                expected = 200 if key in allowed else 403
                self.assertEqual(self.code(user, name), expected, f"{key} -> {name}")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("staff_gateways")).status_code, 302)

    def test_customers_get_403_on_every_panel_page(self):
        for name in ("staff_dashboard", "staff_orders", "staff_gateways", "staff_assistant", "staff_about"):
            self.assertEqual(self.code(self.cust, name), 403, name)

    def test_only_admins_create_staff_and_pick_roles(self):
        self.client.force_login(self.manager)
        r = self.client.get(reverse("staff_user_new"), **AJAX)
        self.assertNotContains(r, "staff_role")
        self.client.force_login(self.admin)
        r = self.client.get(reverse("staff_user_new"), **AJAX)
        for label in ("Warehouse", "Delivery", "Customer support", "Marketing", "Manager"):
            self.assertContains(r, label)

    def test_admin_changes_a_staff_role(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("staff_user_edit", args=[self.warehouse.pk]), {
            "first_name": "W", "last_name": "H", "email": "wh@x.com", "role": "staff", "staff_role": "support", "is_active": "on"}, **AJAX)
        self.warehouse.profile.refresh_from_db()
        self.assertEqual(self.warehouse.profile.staff_role, "support")


class FulfilmentTests(RoleBase):
    def post_status(self, user, order, **data):
        self.client.force_login(user)
        return self.client.post(reverse("staff_order_status", args=[order.pk]), data, **AJAX)

    def test_delivery_sees_only_their_own_orders(self):
        mine, theirs = self.order(courier=self.courier), self.order(courier=self.other_courier)
        self.client.force_login(self.courier)
        listing = self.client.get(reverse("staff_orders")).content.decode()
        self.assertIn(f'href="/staff/orders/{mine.pk}/"', listing)
        self.assertNotIn(f'href="/staff/orders/{theirs.pk}/"', listing)
        self.assertEqual(self.client.get(reverse("staff_order_detail", args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("staff_order_status", args=[theirs.pk]), **AJAX).status_code, 404)

    def test_delivery_cannot_see_invoices_or_cancel(self):
        o = self.order(courier=self.courier)
        self.assertEqual(self.code(self.courier, "staff_order_invoice", o.pk), 403)
        r = self.post_status(self.courier, o, status="cancelled")
        self.assertEqual(r.status_code, 422)  # not an allowed choice for this role
        o.refresh_from_db()
        self.assertEqual(o.status, "shipped")

    def test_delivery_marks_cod_order_delivered_and_it_becomes_paid(self):
        o = self.order(courier=self.courier, status="out_for_delivery")
        self.assertEqual(self.post_status(self.courier, o, status="delivered").status_code, 200)
        o.refresh_from_db()
        self.assertEqual((o.status, o.paid), ("delivered", True))  # cash collected

    def test_warehouse_limited_to_pack_and_ship(self):
        o = self.order(status="pending")
        self.assertEqual(self.post_status(self.warehouse, o, status="delivered").status_code, 422)
        self.assertEqual(self.post_status(self.warehouse, o, status="shipped", courier=self.courier.pk).status_code, 200)
        o.refresh_from_db()
        self.assertEqual((o.status, o.courier), ("shipped", self.courier))

    def test_cannot_ship_unpaid_online_order(self):
        o = self.order(status="processing", method="payhero", paid=False)
        r = self.post_status(self.manager, o, status="shipped")
        self.assertContains(r, "waiting for the customer", status_code=422)
        o.refresh_from_db()
        self.assertEqual(o.status, "processing")
        self.assertEqual(self.post_status(self.manager, o, status="shipped", paid="on").status_code, 200)

    def test_only_managers_mark_paid_and_assign_courier_not_delivery(self):
        o = self.order(status="shipped", courier=self.courier)
        r = self.client.get(reverse("staff_order_status", args=[o.pk]), **AJAX)
        self.client.force_login(self.courier)
        r = self.client.get(reverse("staff_order_status", args=[o.pk]), **AJAX)
        self.assertNotContains(r, 'name="paid"')
        self.assertNotContains(r, 'name="courier"')
        self.client.force_login(self.manager)
        r = self.client.get(reverse("staff_order_status", args=[o.pk]), **AJAX)
        self.assertContains(r, 'name="paid"')
        self.assertContains(r, 'name="courier"')

    def test_dashboard_shows_delivery_staff_their_run_sheet(self):
        o = self.order(courier=self.courier)
        self.client.force_login(self.courier)
        html = self.client.get(reverse("staff_dashboard")).content.decode()
        self.assertIn("Your deliveries", html)
        self.assertIn("0712345678", html)
        self.assertNotIn("Revenue", html)
