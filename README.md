# BRAC IED Central Portal

Enterprise requisition management system with ICT, Transport, and Internal requisitions, plus HR module (contracts, employees, payslip) and self-registration with admin approval.

## Features

- **ICT Requisitions** — Request IT equipment, software licenses, and accessories
- **Transport Requisitions** — Request vehicle transport for official trips
- **Internal Requisitions** — Request office supplies, stationery, and resources
- **Payslip Requests** — Public form to request payslips by name/PIN
- **Self-Registration** — Sign up with requester role; accounts require admin activation
- **Role-Based Access** — Admin, transport_admin, hr_admin, requester roles with scoped permissions
- **Unified "My Requisitions"** — Single view of all your requests across types
- **Audit Log** — Track all create/approve/reject actions with timestamps
- **HR Module** — Contract management, employee records, payslip generation
- **System Documentation** — Built-in HTML/PDF documentation
- **Mobile Responsive** — Overlay sidebar, card-style tables on small screens
- **Background Tasks** — Email notifications via Django Q

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0 |
| Database | PostgreSQL (primary) / SQLite (dev) |
| Server | Gunicorn + nginx |
| Task Queue | Django Q (ORM-backed) |
| PDF | WeasyPrint |
| CI/CD | Jenkins (Jenkinsfile) |

## Quick Start

### 1. Clone & setup

```bash
git clone https://github.com/khanwasik1449/Requisition-Portal.git
cd Requisition-Portal
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings (secret key, DB credentials, etc.)
```

### 3. Run migrations & seed

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

### 4. Start development server

```bash
python3 manage.py runserver 0.0.0.0:8000
```

## Production Deployment

### Prerequisites

- nginx, PostgreSQL, Python 3.12+
- WeasyPrint system libs: `libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`

### Setup

```bash
./deploy.sh
```

This pulls latest code, installs deps, runs migrations, collects static files, and restarts the gunicorn service.

### Systemd service

A `requisition_portal.service` file is expected at `/etc/systemd/system/`. The service runs `run.sh` which sources `.env` and starts gunicorn on `127.0.0.1:8001`.

### nginx

The nginx config proxies `80` → `127.0.0.1:8001` and serves `/static/` from the `staticfiles/` directory.

## CI/CD (Jenkins)

See `Jenkinsfile` for the full pipeline:

1. Checkout → venv setup → lint → collectstatic → migrate → deploy via SSH
2. The deploy stage (`deploy.sh`) runs on the `main` branch only
3. Setup instructions:
   - Create a Jenkins Pipeline job pointing to this repo (SCM)
   - Add the Jenkins SSH public key to the server's `~/.ssh/authorized_keys`
   - Uncomment the SSH deploy command in `Jenkinsfile`

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | dev-only fallback | Django secret key |
| `DJANGO_DEBUG` | No | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | No | `*` | Comma-separated hosts |
| `DB_ENGINE` | No | `sqlite3` | Database engine |
| `DB_NAME` | No | `db.sqlite3` | Database name |
| `DB_USER` | For PG | — | DB user |
| `DB_PASSWORD` | For PG | — | DB password |
| `DB_HOST` | For PG | — | DB host |
| `DB_PORT` | For PG | — | DB port |

## Public Transport Requests

The transport request form and status tracking are **open to anyone — no login
required**. Approvals, reports and history remain staff-only.

| URL | Access | Purpose |
|---|---|---|
| `/transport/create/` | **Public** | Submit a request; anonymous rows store `user = NULL` |
| `/transport/track/` | **Public** | Look up your own requests by email |
| `/transport/` | Login | All requests (role-scoped) |
| `/transport/history/` | Admin / transport_admin | Every request plus its audit trail |
| `/transport/report/` | Admin / transport_admin | Filtered summary + Excel export |

**Email is the public tracking key.** `/transport/track/` matches
`email_address__iexact` only, so it returns a requester's own rows and nothing
else — it cannot be used to enumerate other people's requests.

Public submissions bypass login, so the form validates every required field
itself and returns HTTP 400 with messages instead of raising on missing input.
`TransportRequisition.user` is nullable and uses `SET_NULL`, so deleting a user
account never destroys a public request.

## Enabling and Disabling Modules

Functional modules are switched on/off with the `ENABLED_MODULES` list in
`requisition_portal/settings.py`. Disabled modules are **unrouted and hidden**,
but their apps stay installed and their tables and data are preserved — so a
module can be switched back on at any time with no data loss.

```python
ENABLED_MODULES = ['transport']   # currently active
ENABLED_MODULES = ['ict', 'transport', 'internal', 'hr']   # everything on
```

| Key | Covers |
|---|---|
| `ict` | ICT requisitions |
| `transport` | Transport requisitions |
| `internal` | Internal requisitions |
| `hr` | HR — contracts, employees, payslip |

`accounts` (users/roles) and `notifications` (approval emails, audit log) are
core and always active — transport approvals depend on them.

### Enabled vs. visible

Two independent lists:

- `ENABLED_MODULES` — what is **routed**. A module here has working URLs.
- `VISIBLE_MODULES` — what is **shown** in the sidebar, landing page,
  dashboard, selection page and "My Requisitions".

This lets you park a module without switching it off. A module can stay
enabled (URLs resolve, staff reach it by bookmark, data untouched) while being
absent from the UI. Current state: everything enabled, only Transport visible.

What happens when a module is **disabled** (`ENABLED_MODULES`):

- Its URLs are not registered, so its routes return 404 and its named URLs
  cannot be reversed
- Signed approve/reject email links for that type are rejected

What happens when a module is **hidden** (in `ENABLED_MODULES`, not in
`VISIBLE_MODULES`):

- No links anywhere in the UI, for any role
- Dashboard counters and "My Requisitions" skip its requisition type
- Its URLs still resolve for anyone who navigates directly

In both cases rows in its tables are left untouched.

After editing, restart the service:

```bash
sudo systemctl restart requisition_portal.service
```

## Roles

| Role | Capabilities |
|---|---|
| **admin** | Full access — all requisitions, audit log, approvals, reports |
| **transport_admin** | Transport requisition management, report access |
| **hr_admin** | HR module access (contracts, employees, payslip) |
| **requester** | Create & view own requisitions only (default sign-up role) |

## Project Structure

```
├── accounts/           # User model, auth views, sign-up
├── contracts/          # HR contract management
├── employees/          # Employee records
├── ict_requisition/    # ICT requisition workflow
├── internal_requisition/ # Internal requisition workflow
├── transport_requisition/ # Transport requisition workflow
├── notifications/      # Email logs, audit log
├── payslip/            # Payslip generation & requests
├── requisition_portal/ # Core settings, URLs, home/dashboard/docs views
├── templates/          # Portal templates (base, home, docs, etc.)
├── static/             # Static assets
├── Jenkinsfile         # CI/CD pipeline
├── deploy.sh           # Production deploy script
├── run.sh              # Gunicorn start script
└── .env.example        # Environment template
```
