# NovaMart

**NovaMart** is a complete, working e-commerce web application built with **Python and Django**.
It has a customer storefront (home, products, categories, cart, checkout, orders, account) and a separate
administrator dashboard (products, categories, orders, customers, uploads, sales data and analytics),
all backed by a real SQL database and **one shared login page** that sends customers and administrators to the right place.

> **This is an educational prototype.** No real payments are processed and no card details are collected.
> It is not production-ready until you complete the checklist in [Production security checklist](#production-security-checklist).

---

## Contents

1. [Feature list](#feature-list)
2. [Technology stack](#technology-stack)
3. [Quick start (Windows)](#quick-start-windows)
4. [Manual setup (all systems)](#manual-setup-all-systems)
5. [Demo accounts](#demo-accounts-development-only)
6. [How login and roles work](#how-login-and-roles-work)
7. [Folder structure](#folder-structure)
8. [Architecture overview](#architecture-overview)
9. [Database models](#database-models)
10. [Product images and uploads](#product-images-and-uploads)
11. [Cart, checkout and inventory rules](#cart-checkout-and-inventory-rules)
12. [Revenue and analytics definitions](#revenue-and-analytics-definitions)
13. [Testing](#testing)
14. [Troubleshooting](#troubleshooting)
15. [Real admin account, changing demo credentials, resetting data](#real-admin-account-changing-demo-credentials-resetting-data)
16. [Production security checklist](#production-security-checklist)
17. [Optional: PostgreSQL](#optional-postgresql)
18. [Known limitations and future improvements](#known-limitations-and-future-improvements)

---

## Feature list

**Implemented (real, database-backed behaviour)**

| Area | What you get |
|---|---|
| Shared login | One login page for everyone; show/hide password; remember-me; role-based redirect; safe `next` handling; logout (POST + CSRF) |
| Registration | Customer self-registration with Django password validation. A role can never be chosen from the browser. |
| Storefront | Hero with live featured products, category tiles, trending, best sellers, new arrivals, special offers, benefits, footer |
| Catalogue | Search, category filter, price range, in-stock filter, sorting (newest / popularity / price), pagination, discount badges, stock indicators, demo ratings |
| Product detail | Photo gallery, price and discount, stock, quantity stepper, related products, breadcrumbs |
| Cart | Database-backed per-customer cart, add / increase / decrease / remove with no page reload (fetch) and a working no-JavaScript fallback, live badge, server-calculated totals |
| Checkout | Shipping form, saved addresses, Cash on Delivery or clearly labelled *simulated* payment, atomic order creation, stock re-validation, order confirmation |
| Customer account | Profile editing, address book, order history, order details, cancel while Pending/Confirmed |
| Admin dashboard | Revenue, orders, customers, active products, low stock, recent orders, best sellers, 14-day activity chart |
| Admin: products | Create / edit / delete (or auto-deactivate if it has orders), upload main + extra photos, price, stock, featured flag, search and filters |
| Admin: categories | Create / edit / activate / deactivate / safe delete (blocked while products exist), category images |
| Admin: orders | Search by order number or username, filter by status and date, update status with inventory-safe rules |
| Admin: customers | Search, view order history, activate / deactivate. Passwords are never shown. |
| Analytics | Daily / weekly / monthly revenue, orders over time, best-selling products, category sales, status breakdown, average order value, low-stock summary, date-range filter, CSV export |
| Quality | 170 automated tests, custom 403 / 404 / 500 pages, responsive layout (320 px to 1440 px), keyboard focus styles, reduced-motion support |

**Simulated for the prototype**: payments (no gateway), delivery/shipping partners (none), ratings (demo values), email notifications (none).
**Future enhancements**: see [Known limitations](#known-limitations-and-future-improvements).

## Technology stack

* **Python 3.12+** and **Django 6.1** (Django's ORM, migrations, auth, sessions, CSRF, messages)
* **SQLite** (SQL database for the prototype), PostgreSQL optional
* **Pillow** for image upload validation (and to draw the demo product pictures)
* **HTML5, CSS3 (custom design system with CSS variables), vanilla JavaScript**
* **Chart.js 4.4.7**, bundled locally in `static/vendor/` (no internet needed for charts)
* Fonts (Bricolage Grotesque, DM Sans) load from Google Fonts when online; a system-font fallback is used offline.

Only two Python packages are required: `Django` and `Pillow` (see `requirements.txt`).

---

## Quick start (Windows)

1. Install **Python 3.12 or newer** from <https://www.python.org/downloads/> (tick **Add python.exe to PATH**).
2. Extract `NOVAMART.zip` and open the `NOVAMART` folder.
3. Double-click **`setup_windows.bat`** (creates `venv`, installs dependencies, migrates, loads demo data).
4. Double-click **`run_windows.bat`**.
5. Open <http://127.0.0.1:8000/> in your browser.

Linux / macOS: `./setup_unix.sh` then `./run_unix.sh`.

Both setup scripts are safe to run again; they never delete your data.

## Manual setup (all systems)

Open **Command Prompt** or **PowerShell** inside the extracted `NOVAMART` folder.

```bat
:: 1. Create a virtual environment
python -m venv venv

:: 2. Activate it
::    Command Prompt:
venv\Scripts\activate
::    PowerShell:
.\venv\Scripts\Activate.ps1

:: 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 4. Create / update the database (migrations are already included)
python manage.py makemigrations
python manage.py migrate

:: 5. Load demo data: 10 customers, 1 admin, 6 categories, 27 products with images, 84 sample orders
python manage.py seed_demo_data --with-demo-users

:: 6. Check and test
python manage.py check
python manage.py test

:: 7. Run the site
python manage.py runserver
```

Linux / macOS equivalents:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data --with-demo-users
python manage.py runserver
```

Then open:

| Page | URL |
|---|---|
| Storefront | <http://127.0.0.1:8000/> |
| Login | <http://127.0.0.1:8000/login/> |
| Admin dashboard | <http://127.0.0.1:8000/dashboard/> |
| Django admin (built-in) | <http://127.0.0.1:8000/admin/> |

---

## Demo accounts (development only)

> These credentials are **public and deliberately weak** (for example `1234`). They exist only for local demos,
> are only created when `DJANGO_DEBUG=True` (or `NOVAMART_ALLOW_DEMO_ACCOUNTS=True`), and must **never** be used on a real server.
> Passwords are stored as Django password hashes, never as plain text. This README is the only place they are listed.

**Customers (10)**

| # | Username | Password |
|---|---|---|
| 1 | `niraj_dalal` | `1234` |
| 2 | `novamart_customer01` | `NovaDemo@01!` |
| 3 | `novamart_customer02` | `NovaDemo@02!` |
| 4 | `novamart_customer03` | `NovaDemo@03!` |
| 5 | `novamart_customer04` | `NovaDemo@04!` |
| 6 | `novamart_customer05` | `NovaDemo@05!` |
| 7 | `novamart_customer06` | `NovaDemo@06!` |
| 8 | `novamart_customer07` | `NovaDemo@07!` |
| 9 | `novamart_customer08` | `NovaDemo@08!` |
| 10 | `novamart_customer09` | `NovaDemo@09!` |

**Administrator (1)**

| Username | Password |
|---|---|
| `novamart_admin` | `NovaAdmin@2026!` |

The seed command is **idempotent**: running it again creates no duplicates. Each run re-applies the documented demo passwords
to these 11 accounts only (so a forgotten demo password is fixed by re-running it). Other users are never touched.

## How login and roles work

* There is **one** login page: `/login/`.
* After a successful login: **customers go to the storefront (`/`)**, **administrators go to the dashboard (`/dashboard/`)**.
* Anonymous visitors opening a protected page are redirected to the login page, and returned afterwards.
* A customer opening `/dashboard/...` receives a friendly **403 Access denied** page. Every dashboard view is protected
  on the server by the `admin_required` decorator (`accounts/permissions.py`); hiding menu items is never the only protection.
* Administrators may use the storefront too (their account menu shows an *Admin dashboard* link).
* The custom `User` model (`accounts.User`, based on `AbstractUser`) has a `role` field (`customer` / `admin`).
  `save()` keeps Django's `is_staff` flag consistent: admin role means staff, customer role means not staff.
  Superusers always get the admin role.
* Deactivated accounts cannot sign in.

## Folder structure

```
NOVAMART/
├── manage.py
├── requirements.txt          # Django, Pillow (pinned)
├── .env.example              # copy to .env for custom settings (never commit .env)
├── setup_windows.bat / run_windows.bat
├── setup_unix.sh / run_unix.sh
├── novamart_project/         # settings, root URLs, WSGI/ASGI, error views
├── accounts/                 # custom User, Address, login/register/profile views, seed command, role decorator
├── catalog/                  # Category, Product, ProductImage, storefront pages, upload validators, demo image generator
├── cart/                     # Cart, CartItem, cart views (JSON + HTML), pricing rules
├── orders/                   # Order, OrderItem, checkout, order history, order services (atomic logic)
├── dashboard/                # admin dashboard views, analytics queries
├── templates/                # base.html, includes/, accounts/, store/, cart/, checkout/, orders/, dashboard/, errors/
├── static/                   # css/ js/ images/ vendor/chart.umd.js
├── media/                    # uploaded images (products/, categories/) created at runtime
├── tests/                    # shared test helpers + project-wide tests (each app also has its own tests.py)
└── docs/PROJECT_OVERVIEW.md
```

`novamart.sqlite3` is **not** shipped; it is created by `migrate` (and filled by `seed_demo_data`).

## Architecture overview

* **Five focused apps**: `accounts` (identity and roles), `catalog` (what we sell), `cart` (what a customer intends to buy),
  `orders` (what was bought), `dashboard` (administration and analytics). Each has a single responsibility.
* **Business rules live in services, not templates**: `cart/pricing.py` computes every total;
  `orders/services.py` (`place_order`, `change_order_status`) is the only code that creates orders or moves stock.
* **The server is the source of truth.** JavaScript only enhances (AJAX cart, charts, gallery); every action works with a plain form post.
* **Security by default**: ORM only (no raw SQL), CSRF on every POST (and `fetch` sends the token), ownership checks by filtering
  querysets on `request.user` (another customer's order/address/cart item is a 404), safe redirects, safe uploads.
* **Money** is always `Decimal`/`DecimalField`; the currency is INR (₹) with Indian digit grouping.
* **Time zone**: `Asia/Kolkata`.

## Database models

| Model | Purpose / key fields |
|---|---|
| `accounts.User` | `AbstractUser` + `role`, `phone` |
| `accounts.Address` | owner (`user`), label, name, phone, address lines, city, state, PIN, `is_default` |
| `catalog.Category` | `name` (unique), `slug` (unique), description, `image`, `is_active` |
| `catalog.Product` | `category` (PROTECT), `name`, `slug`, `sku` (unique), `price`, optional `original_price`, `image`, `stock`, `is_active`, `is_featured`, demo `rating` / `rating_count`; DB check `price > 0` |
| `catalog.ProductImage` | extra photos for a product |
| `cart.Cart` | one per user |
| `cart.CartItem` | cart + product + quantity; unique per (cart, product); DB check `quantity >= 1` |
| `orders.Order` | unique `order_number`, `customer`, `status`, `payment_method`, `payment_status`, shipping snapshot, `subtotal`, `delivery_charge`, `discount`, `total`, `stock_restored`, `is_demo` |
| `orders.OrderItem` | order + product (SET NULL) + **snapshots** of name, SKU, category, unit price; quantity; line total |

Order status: Pending, Confirmed, Processing, Shipped, Delivered, Cancelled.
Payment status (separate): Pending, Paid, Refunded.

## Product images and uploads

* Product and category pictures use Django `ImageField` with `MEDIA_ROOT` (`media/`) and `MEDIA_URL` (`/media/`).
* Seeded products each get a real image file. These are **original illustrations drawn with Pillow** by `catalog/demo_images.py`
  (no licensing concerns, no internet needed), saved through the ImageField exactly like a real upload.
* Administrators upload a main photo and several extra photos in **Dashboard > Products > Add / Edit**.
* Uploads are validated on the server: extension whitelist (`jpg jpeg png webp gif`), real-image check by Pillow, **3 MB** limit
  (`MAX_IMAGE_UPLOAD_BYTES` in settings), and the file name is **replaced by a random name** (the original name is never used).
  A `.php` or other executable can never be saved as an image.
* If an image is missing or its file was deleted, pages show a built-in placeholder and never crash.
* `urls.py` serves `/media/` **only when `DEBUG=True`**. That is a development convenience, **not** for production.
  In production, serve `MEDIA_ROOT` with your web server, a CDN or object storage.

## Cart, checkout and inventory rules

* Delivery fee **₹49**, free for subtotals of **₹999 or more** (configurable via environment variables).
* The cart stores only *which product* and *how many*. Prices are read from the database each time; nothing the browser sends can change a price.
* Checkout (`orders/services.place_order`) runs inside `transaction.atomic()`:
  1. re-reads current price/stock with row locking where the database supports it (PostgreSQL/MySQL; SQLite serialises writers),
  2. rejects inactive products or insufficient stock,
  3. creates the order and order lines with price/name snapshots,
  4. decreases stock with a guarded update (`stock >= qty`), so overselling is impossible,
  5. empties the cart.
  Any failure rolls everything back: no half-created order and no wrong stock.
* **Cash on Delivery**: order starts *Pending*, payment *Pending*.
  **Simulated payment** (clearly labelled demo): order starts *Confirmed*, payment *Paid*.
* **Inventory rules when status changes** (tested):
  * Moving to **Cancelled** returns the items to stock **once**; a *Paid* order becomes *Refunded*.
  * Moving **out of Cancelled** takes the items from stock again; it is refused if stock is no longer sufficient.
  * Marking a COD order **Delivered** sets payment to *Paid*.
  * Customers can cancel only while Pending/Confirmed.
* `Order.discount` is informational (savings versus list price, already reflected in the subtotal).

## Revenue and analytics definitions

* **Revenue** = the `total` of orders with status **Confirmed, Processing, Shipped or Delivered**.
  **Pending** (for example unconfirmed COD) and **Cancelled** orders are excluded, so revenue is never overstated.
* Order counts and average order value use the same set of orders.
* Product and category sales use order-line snapshots of those same orders, so nothing is counted twice and history survives product edits/deletes.
* Dates are bucketed in the `Asia/Kolkata` time zone. Date-range filters are inclusive.
* The demo data includes **84 sample orders over the last 90 days**, flagged `is_demo=True`, clearly separate from real activity.
  Demo orders do not change product stock (the seeded stock is treated as the current net level).

## Testing

```bash
python manage.py check
python manage.py test
```

170 automated tests cover authentication and role redirection, access control, registration, products, search/filter/sort/pagination,
image upload validation, cart rules and ownership, price tampering, checkout (including transaction rollback and stock races),
order access isolation, inventory restoration, admin CRUD, customer management, analytics arithmetic, CSV export safety,
URL/static-asset/template checks, migrations being up to date, and an end-to-end seed-to-checkout-to-admin journey.
The test run uses a throw-away database and a temporary media folder, and a fast password hasher (only while testing).

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Install Python 3.12+ and tick *Add python.exe to PATH*; or try `py -3 -m venv venv`. Reopen the terminal. |
| `Django requires Python 3.12` / wrong interpreter | Run `python --version`. Use `py -3.12` or install a newer Python. Recreate `venv` (delete the folder first). |
| PowerShell: *running scripts is disabled* | Use Command Prompt (`venv\Scripts\activate`) or run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: django` | The environment is not active. Activate it, then `pip install -r requirements.txt`. |
| `No such table` | Run `python manage.py migrate`. |
| Port 8000 busy | `python manage.py runserver 8001` |
| No products / can't log in as a demo user | `python manage.py seed_demo_data --with-demo-users` (also resets the demo passwords) |
| Images missing after moving the project | Keep the `media/` folder with it, or re-run the seed command (it regenerates missing images). |
| Fonts look different offline | Expected. Google Fonts need internet; the fallback system font is used. |
| `Refusing to create demo accounts` | `DJANGO_DEBUG` is False. Demo accounts are deliberately blocked outside development. |

## Real admin account, changing demo credentials, resetting data

* **Create a real administrator**:
  ```bash
  python manage.py createsuperuser
  ```
  Superusers automatically get the Admin role and can use `/dashboard/` and `/admin/`.
* **Change the demo credentials**: edit `accounts/demo_users.py`, then re-run `python manage.py seed_demo_data --with-demo-users`.
  (For anything beyond local demos, delete the demo accounts instead and use your own.)
* **Remove demo accounts** (Django shell): `User.objects.filter(username__startswith="novamart_").delete()` and `niraj_dalal`; orders protect their customers, so remove demo orders first (`Order.objects.filter(is_demo=True).delete()`).
* **Regenerate demo orders**: `python manage.py seed_demo_data --reset-orders` (only deletes orders flagged `is_demo`).
* **Skip sample orders**: `python manage.py seed_demo_data --skip-orders`.
* **Start completely fresh**: stop the server, delete `novamart.sqlite3` and the files inside `media/products` and `media/categories`, then run `migrate` and `seed_demo_data --with-demo-users` again.

## Production security checklist

Before putting anything like this on the internet (see Django's [deployment checklist](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/); run `python manage.py check --deploy`):

- [ ] `DJANGO_DEBUG=False` and a long random `DJANGO_SECRET_KEY` from the environment (the app refuses to start without it when DEBUG is off).
- [ ] `DJANGO_ALLOWED_HOSTS` set to your real domain(s); `DJANGO_CSRF_TRUSTED_ORIGINS` for HTTPS origins.
- [ ] HTTPS everywhere. With DEBUG off the app already enables secure cookies and SSL redirect; set `DJANGO_HSTS_SECONDS` once HTTPS is verified.
- [ ] **No demo accounts**: leave `NOVAMART_ALLOW_DEMO_ACCOUNTS` unset/False and delete any that exist. Create a real admin with `createsuperuser`.
- [ ] Use PostgreSQL (or another production database) and back it up.
- [ ] Serve static files (`collectstatic`, e.g. WhiteNoise or your web server) and media files outside Django.
- [ ] Add login rate-limiting / lockout (for example `django-axes`) and consider two-factor auth for admins.
- [ ] Integrate a real, PCI-compliant payment gateway. Never handle raw card numbers yourself.
- [ ] Email delivery for order confirmations and password reset.
- [ ] Configure logging/monitoring; keep dependencies updated.

## Optional: PostgreSQL

The prototype needs only SQLite. To switch later: `pip install "psycopg[binary]"`, then set in `.env`
`DB_ENGINE=postgresql`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (see `.env.example`), and run `python manage.py migrate`.
Row-level locking in checkout (`select_for_update`) becomes fully effective on PostgreSQL.

## Known limitations and future improvements

* No real payment gateway, e-mail, SMS, shipping integration, taxes/GST invoices, coupons or returns/refund workflow.
* Ratings are demo data; there is no review system yet.
* Carts are for signed-in customers only (no anonymous guest cart).
* No login rate-limiting, password-reset e-mail flow or two-factor authentication.
* Product variants (size/colour), wish-lists, and full-text search ranking are not included.
* Analytics are computed on request; very large stores would want caching or pre-aggregated tables.
* The dev server is not a production server (use gunicorn/uvicorn behind nginx).
* Google Fonts are loaded from the internet when available.
