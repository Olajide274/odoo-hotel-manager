# Odoo Hotel Manager

A custom Odoo 18 addon for running a small hotel: rooms, bookings, guest billing and online payments in one system. It is built for hotels that still run on paper registers or Excel sheets, where double-bookings, forgotten bar bills and unreconciled payments quietly cost money every week.

<!-- Add 3-4 screenshots here: booking form, folio tab, paid invoice, dashboard.
     Example: ![Booking form](docs/screenshots/booking-form.png) -->

---

## Features

**Rooms**
- Room types with a nightly price, and individual rooms with a status.
- Kanban view for a quick look at room status.

**Bookings**
- Booking lifecycle: Draft, Confirmed, Checked In, Checked Out, Cancelled.
- Double-booking protection: the same room cannot be booked on overlapping dates.
- Nights and total price are computed automatically.
- The nightly price is fixed when the booking is made, so later price changes do not alter existing bookings.

**Billing**
- Guest folio for extra charges (bar, food, laundry, other).
- One-click Odoo invoice generated from the room stay plus all folio charges.
- Payment status (Not Paid, Paid) shown on the booking, driven by the Odoo invoice.
- Charges are locked once an invoice exists, so the folio and the invoice always match.

**Reports**
- Booking calendar, pivot and graph views, dashboard, and a daily revenue view.

**Online booking and payments**
- Public booking flow with Paystack payments and a webhook that confirms payment.

**Access control**
- Two roles: **Receptionist** (day-to-day front desk work) and **Manager** (full control, including prices, configuration and deletions).

**Plans**
- Plan-based access with upgrade prompts for features outside a hotel's plan.

---

## Tech Stack

- **Platform:** Odoo 18.0 Community (Python, XML, QWeb)
- **Database:** PostgreSQL 16
- **Payments:** Paystack REST API
- **Runtime:** Docker and Docker Compose
- **CI:** GitHub Actions

---

## Repository Structure

```
odoo-hotel-manager/
├── .github/workflows/      # CI: automated tests on every push
├── addons/
│   └── hotel_manager/
│       ├── controllers/    # Web controllers (booking pages, Paystack webhook)
│       ├── data/           # Sequences, default data, demo data
│       ├── models/         # Rooms, bookings, folio charges, billing
│       ├── report/         # PDF reports and receipts
│       ├── security/       # Groups and access rights
│       ├── tests/          # Automated tests
│       ├── views/          # Views, menus, website templates
│       └── __manifest__.py
├── config/
│   └── odoo.conf.example   # Copy to odoo.conf (see Quick Start)
├── docker-compose.yml
├── DEPLOY.md               # Production deployment guide
└── README.md
```

---

## Quick Start (Docker)

You only need Docker and Git. Odoo and PostgreSQL run in containers, so nothing else has to be installed.

```bash
git clone https://github.com/Olajide274/odoo-hotel-manager.git
cd odoo-hotel-manager

# Create your local Odoo config (not committed to git)
cp config/odoo.conf.example config/odoo.conf

# Start PostgreSQL and Odoo
docker compose up -d

# Create a database and install the module
docker compose run --rm odoo odoo -d hotel_dev -i hotel_manager --without-demo=all --stop-after-init
docker compose restart odoo
```

Open <http://localhost:8069>, choose the `hotel_dev` database and log in with `admin` / `admin`. **Change this password immediately, and never keep the defaults on a server that is reachable from the internet.**

### One-time accounting setup

Invoicing needs a chart of accounts. In Odoo go to **Invoicing → Configuration → Settings → Fiscal Localization**, pick the Nigerian chart (or the Generic one for development) and save. Without it, "Create Invoice" will report that no sales journal exists.

### Update the module after code changes

```bash
docker compose run --rm odoo odoo -d hotel_dev -u hotel_manager --stop-after-init
docker compose restart odoo
```

---

## Running the Tests

```bash
docker compose run --rm odoo odoo -d hotel_dev -u hotel_manager \
  --test-enable --test-tags /hotel_manager --http-port=8070 \
  --stop-after-init > test.log 2>&1

grep -E "ERROR|FAIL|tests in|failed" test.log | tail
```

A clean run ends with `0 failed, 0 error(s)`. The suite covers room and security rules, booking overlap and pricing, the state flow, and billing totals (the invoice total must equal the folio total).

---

## Paystack Configuration

1. In Odoo, open the Hotel Manager settings and enter your Paystack **Secret Key** and **Public Key** (use test keys while developing).
2. In your Paystack dashboard, set the webhook URL to:

   ```
   https://your-domain.com/hotel/paystack/webhook
   ```

3. Webhooks must reach a public HTTPS address, so payment confirmation only works on a deployed server, not on `localhost`.

Webhook requests are verified with Paystack's signature, and requests with an invalid signature are rejected. **Never commit API keys.** Keep them in Odoo's settings or in a `.env` file that is listed in `.gitignore`.

---

## Deployment

See [DEPLOY.md](DEPLOY.md) for server setup, HTTPS, backups and updates. In short: run the same Docker stack on a VPS behind a reverse proxy, keep PostgreSQL closed to the internet, set a strong Odoo master password, and schedule off-server database backups.

---

## Author

**Michael Olajide David**
Full-Stack Software Engineer, Founder of Swift Digital Services

- GitHub: <https://github.com/Olajide274>
- LinkedIn: <https://www.linkedin.com/in/michael-olajide-david-b27859383>
- Portfolio: <https://swift-portfolio-rho.vercel.app>

---

## License

Released under the LGPL-3.0 license, as declared in the module manifest.
