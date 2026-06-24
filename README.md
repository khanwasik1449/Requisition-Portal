# Requisition Portal

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
