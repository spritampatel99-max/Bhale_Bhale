# NovaMart: project overview

## Status of each capability

| Capability | Status |
|---|---|
| Shared login with role-based redirect (customer to storefront, admin to dashboard) | **Implemented** (Django auth, sessions, server-side checks) |
| Customer registration, profile, address book | **Implemented** |
| 10 demo customers incl. `niraj_dalal` / `1234`, 1 demo admin | **Implemented** (idempotent management command, DEBUG-only) |
| Storefront: home, listing, search, filters, sort, pagination, detail, categories | **Implemented** |
| Product images (ImageField), upload validation, fallback image | **Implemented** |
| Database cart with AJAX + non-JS fallback | **Implemented** |
| Checkout, atomic order creation, stock validation and reduction | **Implemented** |
| Order history/detail (owner-only), customer cancellation | **Implemented** |
| Admin dashboard, products/categories/orders/customers management, uploads | **Implemented** |
| Analytics (daily/weekly/monthly, categories, products, AOV, low stock), CSV export | **Implemented** |
| Payments | **Simulated** (Cash on Delivery or labelled demo payment; no gateway) |
| Ratings | **Simulated** demo values (no reviews system) |
| Demo order history (84 orders, `is_demo=True`) | **Simulated** sample data for analytics |
| Delivery partners, e-mail, SMS, taxes/invoices, coupons, returns | **Future** |
| Rate limiting, 2FA, password reset by e-mail | **Future** |
| PostgreSQL | **Optional** (config included, not required) |

## Request flow (checkout)

```
Browser form POST  ->  CsrfViewMiddleware
   -> orders.views.checkout  (login_required, validates CheckoutForm)
   -> orders.services.place_order  (transaction.atomic)
        lock + re-read products  ->  validate stock/active
        cart.pricing.calculate_totals (Decimal, server-side)
        create Order + OrderItems (snapshots)
        guarded stock decrement (stock >= qty)
        clear cart
   -> redirect to /orders/<number>/confirmation/  (owner-only lookup)
```

## URL map

| URL | Purpose |
|---|---|
| `/` | Home |
| `/products/`, `/products/<slug>/` | Listing (search/filter/sort), detail |
| `/categories/`, `/categories/<slug>/` | Category browsing |
| `/cart/` (+ `add/`, `update/`, `remove/`) | Cart |
| `/checkout/` | Checkout |
| `/orders/`, `/orders/<order_number>/` (+ `confirmation/`, `cancel/`) | Customer orders |
| `/account/`, `/account/addresses/...` | Profile and addresses |
| `/login/`, `/register/`, `/logout/` | Authentication |
| `/dashboard/` | Admin overview |
| `/dashboard/products/` (+ `add/`, `<id>/edit/`, `<id>/delete/`) | Product management |
| `/dashboard/categories/` (+ `add/`, `<id>/edit/`, `<id>/delete/`) | Category management |
| `/dashboard/orders/`, `/dashboard/orders/<order_number>/` | Order management |
| `/dashboard/customers/`, `/dashboard/customers/<id>/` | Customer management |
| `/dashboard/analytics/`, `/dashboard/sales/`, `/dashboard/sales/export/` | Analytics, sales ledger, CSV |
| `/admin/` | Django's built-in admin |

## Design system

Tokens (colours, radii, spacing, shadows, fonts) are CSS variables in `static/css/main.css`.
Palette: deep navy ink, saffron accent, sky-blue for links/focus, rose for discounts, mint for stock/success.
The storefront is light and airy with one bold moment (the hero); the dashboard has its own dark sidebar identity (`dashboard.css`).
Animations are subtle and disabled for users with `prefers-reduced-motion`.
