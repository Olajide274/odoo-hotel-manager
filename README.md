# Odoo Hotel Manager (odoo-hotel-manager)

A comprehensive, production-ready custom Odoo ERP module designed for hospitality management. This addon seamlessly unifies room management, reservation workflows, guest billing, and localized payment gateway integration (Paystack) into a single cohesive system.

---

## Key Features

- Room Management & Inventory: Track room categories, status (available, occupied, under maintenance), pricing tiers, and amenities.
- Reservation & Booking Engine: Manage guest check-ins, check-outs, reservation schedules, and extended stays with automated availability checks.
- Billing & Invoicing: Integrated guest billing system supporting multi-item folio charges, room service add-ons, tax calculations, and automated Odoo invoice generation.
- Paystack Payment Integration: Native support for Paystack online payment links, automated checkout collection, and payment status callbacks for automated reservation confirmation.
- CI/CD & Deployment: Pre-configured GitHub Actions workflows (.github/workflows) and deployment scripts for streamlined testing and production rollouts.

---

## Tech Stack & Architecture

- Core Platform: Odoo ERP Framework (Python / XML / QWeb)
- Database: PostgreSQL
- Payment Gateway: Paystack REST API
- CI/CD & DevOps: GitHub Actions, Docker / Docker Compose

---

## Repository Structure

odoo-hotel-manager/
├── .github/workflows/        # CI/CD pipelines for linting and automated tests
├── addons/
│   └── hotel_manager/        # Custom Odoo addon module
│       ├── controllers/      # Web controllers (Paystack webhooks & endpoints)
│       ├── models/           # Python models (rooms, bookings, folios)
│       ├── views/            # XML views, form layouts, and menus
│       ├── security/         # Access rights (ir.model.access.csv)
│       └── __manifest__.py   # Odoo module manifest definition
├── config/                   # Custom Odoo server configuration files
├── DEPLOY.md                 # Deployment & server setup guide
├── .gitignore                # Git ignore constraints
└── README.md                 # Project documentation

---

## Installation & Local Setup

### Prerequisites

- Odoo Server (v16+ or v17+)
- Python 3.10+
- PostgreSQL database instance
- Paystack API Keys (Test/Live Secret and Public keys)

### Step-by-Step Installation

1. Clone the Repository:
   git clone https://github.com/Olajide274/odoo-hotel-manager.git
   cd odoo-hotel-manager

2. Add to Odoo Addons Path:
   Copy or link the addons/hotel_manager directory into your Odoo server's custom addons_path specified in your odoo.conf:
   addons_path = /path/to/odoo/addons,/path/to/odoo-hotel-manager/addons

3. Install Dependencies:
   Ensure requests or required Python libraries for Paystack communication are installed in your Odoo virtual environment:
   pip install requests

4. Update App List & Install Module:
   - Restart your Odoo server.
   - Log in to Odoo as Administrator.
   - Enable Developer Mode under Settings.
   - Navigate to Apps -> Update Apps List.
   - Search for hotel_manager and click Install.

---

## Paystack Configuration

1. In Odoo, navigate to Hotel Manager -> Settings -> Payment Configurations.
2. Enter your Paystack Secret Key and Public Key.
3. Set your webhook URL in your Paystack Dashboard:
   https://your-odoo-domain.com/hotel/paystack/webhook

---

## Deployment

For production deployments, container setup, and server configuration guidance, please refer to DEPLOY.md.

---

## Author

Michael Olajide David
Full-Stack Software Engineer & Founder at Swift Digital Services
- GitHub: https://github.com/Olajide274
- LinkedIn: https://www.linkedin.com/in/michael-olajide-david-b27859383
- Portfolio: https://michael-olajide-portfolio.vercel.app

---

## License

This project is licensed under the LGPL-3.0 License.
