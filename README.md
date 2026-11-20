# Django Shop

<<<<<<< HEAD
An online shop with a staff back-office, role-based staff accounts, PayHero (M-Pesa) payments, guest checkout,
product options, reviews, invoices, an editable About page, and a customer chat assistant that cannot read your database.

## Run it

    python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser                       # your shop-admin account
    python manage.py seed_demo                             # optional demo data (development only)
    python manage.py runserver
    python manage.py test                                  # 151 tests

Shop: `/` &middot; Staff panel: `/staff/` (log in at `/accounts/login/`) &middot; Django admin: `/admin/` (superusers only).
Demo logins (after `seed_demo`, change or delete before going live): `customer / customer12345`; staff, all with
password `staff12345`: `staff` (manager), `warehouse`, `delivery`, `support`, `marketing`.

**Upgrading from the previous version:** `pip install -r requirements.txt`, then `python manage.py migrate`.
Existing staff accounts automatically become **Managers**, so nobody loses access. Old orders get private links.

## Settings (environment variables)
| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS` | Production basics. HTTPS settings switch on when DEBUG is off. |
| `PUBLIC_BASE_URL` | Your public https address (e.g. `https://shop.example.com`). Needed so PayHero can reach the payment callback and so emails contain correct links. |
| `ANTHROPIC_API_KEY`, `ASSISTANT_MODEL` | Enables free-text AI answers (default model `claude-haiku-5-5`). Without a key the assistant still answers your commands. |
| `FIELD_ENCRYPTION_KEY` | Optional Fernet key for encrypting payment gateway credentials (otherwise derived from the secret key; if that changes, re-enter credentials). |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `SHOP_EMAIL`, `DEFAULT_FROM_EMAIL` | Real email delivery (emails print in the terminal by default). |
| `SHOP_NAME`, `ANNOUNCEMENT` | Shop name; optional banner above the header. |

## Staff roles
Shop admins (superusers) create staff accounts at **Users > Add user** and choose a role. Each role only sees its own sections.

| | Manager | Warehouse | Delivery | Support | Marketing | Shop admin |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Dashboard | yes | yes (stock, to pack) | yes (own run sheet) | yes | yes | yes |
| Products, categories, options | yes | yes | | | | yes |
| Orders | all | all; set pending/processing/shipped, assign courier | **only assigned**; set shipped/out for delivery/delivered | read-only | | all |
| Invoices | yes | | | yes | | yes |
| Payments list | yes | | | | | yes |
| Users (customers) | yes | | | | | yes |
| Messages, inquiries | yes | | | yes | | yes |
| Reviews moderation | yes | | | yes | yes | yes |
| Analytics, subscribers, newsletter | yes | | | | yes | yes |
| About page content | yes | | | | yes | yes |
| Payment gateways, AI assistant, store settings | | | | | | yes |
| Create/edit staff, delete users | | | | | | yes |

**The Django admin (`/admin/`) is for shop admins only.** Staff accounts get a plain 404 there and never see a link to it
(enforced by middleware and by the admin site's own permission check).

Order rules: cancelling returns items to stock (re-opening takes them again); delivering a pay-on-delivery order marks it paid
(cash collected); online-payment orders cannot be dispatched until paid; customers are emailed on every status change.

## Payments with PayHero (M-Pesa)
1. In your PayHero dashboard create a payment channel (note the **Channel ID**) and API keys (username + password).
2. **Staff panel > Payment gateways > Add gateway** (shop admin only). Credentials are encrypted and never shown again.
3. Set `PUBLIC_BASE_URL`. Each gateway shows its callback URL.

Flow: checkout creates the order, sends an M-Pesa prompt, and shows a waiting page that confirms the result. **An order is only
marked paid after the shop asks PayHero's transaction-status API itself**; a callback alone is never trusted, and amounts are re-checked.
Without a public URL (local testing) payments still complete because the waiting page polls PayHero. Failed payments can be retried
from the order page; staff can re-check any payment in **Payments**. Stock is held for unpaid orders until staff cancel them.

## Shop features
- **Guest checkout** (switchable in Store settings): no account needed; every order has a private link (`/order/<token>/`)
  for tracking, paying and downloading the invoice, sent by email. Customers with accounts also see orders under My orders.
- **Options (size, colour...)**: each with its own stock and optional price. Added in the product pop-up.
- **Reviews**: logged-in customers rate 1-5 with a comment, one review per product (editable); "Verified purchase" badge;
  staff can hide or delete.
- **Invoices**: sequential numbers, business details and VAT from Store settings, printable page and PDF, for customers (via
  their order link) and staff. Item names are saved at purchase so old invoices never change.
- **About page**: headline, intro, sections and photos are stored in the database and edited in **About page** (staff panel,
  pop-ups, multi-photo upload). Text is escaped; photos are validated and resized.
- Everything from before: photo galleries, sidebars, profiles, messages, contact form, newsletter, analytics, pop-up CRUD panel.

## AI assistant (customers and guests)
A chat button on every shop page. **It cannot access the database**, by design and by test:
- The AI module (`assistant/ai.py`) imports no models or Django code and sends the model no tools. A test fails if that ever changes.
- The model only ever receives the visitor's question and the **commands** shop admins wrote (never orders, customers, stock,
  prices, staff or payment data). A test creates secret data and proves none of it reaches the model.
- Built-in safety rules are placed last in the prompt so admin "style" text cannot override them. History is kept server-side,
  so visitors cannot forge earlier turns.
- Limits: 500-character questions, short replies, plain text only, per-minute and per-day limits per visitor (needs a shared cache
  such as Redis in production; the default in-memory cache is per process).

**Staff panel > AI assistant** (shop admin only): turn it on/off, set name, greeting, tone, fallback message, daily limit, and manage
**commands**. A command has a `/trigger` (visitors type `/shipping` or tap its button for the exact reply), keywords (used when the AI is
off), an audience (everyone, customers, guests) and whether the AI may use it as knowledge. The AI is billed by the model provider; keep the daily limit modest.

## Other pieces
Tailwind CSS (prebuilt; `npm install && npm run watch:css` to change the design), django-unfold admin theme, Chart.js analytics,
Heroicons. Licences for bundled files are in `panel/static/panel/vendor/`.

## Before going live
Set the environment variables above; use PostgreSQL; serve `media/` from nginx or object storage; use Redis for the cache; delete the demo
accounts; fill in Store settings (business name, address, tax PIN) and the About page; add assistant commands; add your PayHero gateway.
=======
    python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser        # your own admin account
    python manage.py seed_demo              # optional: demo products + demo accounts (dev only)
    python manage.py runserver

## Who can do what
- Customer (register at /accounts/register/): browse, cart, checkout (login required), see "My orders".
- Staff (`is_staff=True`): log in at /accounts/login/ and land on /staff/ - dashboard, order status/paid, product add/edit.
- Admin site (/admin/): superusers have full access. A staff user can only open /admin/ pages they are
  granted permissions for (Admin > Users > edit user > permissions or groups).

Create staff in the admin: Users > Add user > tick "Staff status".
Demo logins from seed_demo (change or delete before going live): customer/customer12345, staff/staff12345.
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
