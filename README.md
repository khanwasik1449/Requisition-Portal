# BRAC IED Central Portal

Requisition and resource management portal for BRAC Institute of Educational
Development. Covers vehicle transport, meeting room bookings, ICT equipment,
office supplies and payslips — all behind configurable, database-driven
approval workflows that an administrator can reshape without editing code.

## Features

### Transport Requisition
- Public request form (no login required) with a 5-step wizard
- Email-based status tracking for requesters
- **4-stage approval chain**: Supervisor → Grants → Transport Admin → Assigned
- Grants can **correct the project and budget codes** before passing on
- Transport Admin assigns a **vehicle and driver** from the fleet
- Conflict detection, capacity checks, driverless/vehicleless states handled

### MeetSpace (Meeting Room Booking)
- Public booking form (no login) and email-based tracking
- Room management (add/edit/retire) by HR admin
- HR approval workflow: approve, reject with reason, or **suggest alternative
  rooms/times** which the requester can accept or decline
- Availability search with 3-day time-slot suggestions when nothing is free
- Announcements board with file attachments

### Dynamic Form & Workflow Engine (`portal_config`)
- **Form fields are database rows** — add, remove, reorder or relabel fields
  from the admin UI without a code change or a migration
- **Workflow stages are database rows** — reorder stages, change the role that
  acts at each stage, and choose which actions are allowed
  (`approve`, `decline`, `amend`, `assign`)
- **Amendable fields** — a stage can be granted permission to correct specific
  fields (this is how Grants edits project/budget codes)
- **Module on/off switches** — turn a module off (URLs 404) or hide it from the
  menu without touching `settings.py`
- New modules can be registered as configuration rows and plugged in later

### Core
- **Email notifications** run on a Django Q background queue, so a slow or
  unreachable SMTP server never blocks an approval
- Signed, expiring approval links in email with login-as-recipient enforcement
- Audit log of every create/approve/decline/amend action
- Unified "My Requisitions" across all types
- Role-based access with per-stage authorization
- Mobile responsive
- BRAC IED branding and logo throughout

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0 |
| Database | PostgreSQL (primary) / SQLite (dev) |
| Server | Gunicorn + nginx |
| Task Queue | Django Q (ORM-backed cluster) |
| Templates | Django templates + Bootstrap 5.3 |

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
# Edit .env — secret key, DB credentials and allowed hosts are all required.
```

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG` and `DJANGO_ALLOWED_HOSTS` have **no
defaults**. The server refuses to start if they are missing, rather than
silently running with an insecure development key.

### 3. Run migrations & create an admin

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

Migrations seed the workflow configuration, so a fresh database already has the
transport and MeetSpace approval chains configured.

### 4. Start the background worker (needed for emails)

```bash
python3 manage.py qcluster
```

Without the cluster running, emails are queued but never delivered.

### 5. Run the development server

```bash
python3 manage.py runserver 0.0.0.0:8000
```

## Production Deployment

### Systemd services

Two services are expected under `/etc/systemd/system/`:

| Service | Role |
|---|---|
| `requisition_portal.service` | Gunicorn via `run.sh` (sources `.env`), binds `127.0.0.1:8001` |
| `qcluster.service` | Django Q cluster for background email |

```bash
sudo systemctl enable --now requisition_portal.service qcluster.service
```

> The two names are easy to confuse. `requisition_portal.service` (underscore)
> is the live server. A `requisition-portal.service` (hyphen) runserver on
> `:8000` is a leftover from development — it uses a different `SECRET_KEY` and
> a stale SQLite file, so signed email links built for one are rejected by the
> other. Keep it disabled.

### nginx

nginx proxies `80` → `127.0.0.1:8001` and serves `/static/` from `staticfiles/`.

### Deploy script

```bash
./deploy.sh
```

Pulls latest code, installs dependencies, runs migrations, collects static
files, and restarts the gunicorn service.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key — no fallback |
| `DJANGO_DEBUG` | Yes | `True` / `False` — no fallback |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated hosts |
| `DJANGO_BASE_URL` | No | Public URL used to build email links (defaults to `http://10.10.11.201`) |
| `DB_ENGINE` | No | Defaults to `sqlite3`; use `django.db.backends.postgresql` in production |
| `DB_NAME` | No | Database name |
| `DB_USER` | For PG | Database user |
| `DB_PASSWORD` | For PG | Database password |
| `DB_HOST` | For PG | Database host |
| `DB_PORT` | For PG | Database port |

`DJANGO_BASE_URL` matters more than it looks: approval links are signed with
`SECRET_KEY` and must point at the instance that will verify them. Pointing
them at a different port or host makes every link in every email fail.

## Public vs. Staff Areas

Transport requests and meeting room bookings are **open to anyone**. Approvals,
reporting and fleet management remain staff-only.

| URL | Access | Purpose |
|---|---|---|
| `/transport/create/` | **Public** | Submit a transport request; anonymous rows store `user = NULL` |
| `/transport/track/` | **Public** | Track your own requests by email |
| `/meetspace/bookings/new/` | **Public** | Book a meeting room |
| `/meetspace/track/` | **Public** | Track your own bookings by email |
| `/transport/` | Login | All requests (role-scoped) |
| `/meetspace/` | Login | Bookings, rooms and announcements management |
| `/portal-config/` | Superadmin / transport_admin | Form Builder and workflow editor |
| `/admin/` | Login | Django admin |

**Email is the public tracking key.** The track pages match
`email_address__iexact` only, so they return a requester's own rows and nothing
else — they cannot be used to enumerate other people's requests.

Public submissions bypass login, so those forms validate every required field
themselves and return HTTP 400 with inline messages rather than raising.
`TransportRequisition.user` and `Booking.user` are nullable with `SET_NULL`, so
deleting an account never destroys a public request.

## Configuring Forms and Workflows

Everything below is editable at **`/portal-config/`** by a superadmin or the
transport admin. No restart is required — changes apply on the next request.

### Turning modules on and off

Each module has two independent switches:

| Switch | Effect |
|---|---|
| **On** | Off means the module is not routed — its URLs 404 and its data is unreachable from the portal |
| **Show in menu** | Off hides it from the nav, dashboard and "My Requisitions" while leaving it routed |

Routing is checked per-request by a custom URL resolver, so switching a module
off takes effect immediately rather than waiting for a worker restart.

Modules that have no configuration row yet fall back to
`ENABLED_MODULES` / `VISIBLE_MODULES` in `settings.py`, so a fresh deploy
behaves exactly as that file declares.

### Editing a form

Each `FormField` row controls a question on the public form: label, widget type,
whether it is required, which step it sits on and its order.

Fields fall into one of two storage modes:

- **Stored in a database column** — the value lands on a real model column, so
  reports, exports and SQL filtering keep working. Use this for existing fields.
- **Extra data** — the value is written to the requisition's `extra_data` JSON
  blob. Use this for brand new questions; they work immediately with no
  migration.

Declaring a custom key as "stored in a database column" is rejected with an
explanation if the model has no such attribute.

### Editing a workflow

Each `WorkflowStage` row is one step of an approval chain and declares:

- **Who can act** — a role, or "any approver". The superadmin can always act.
- **Allowed actions** — `approve`, `decline`, `amend`, `assign`
- **Amendable fields** — which fields that stage may correct before approving
- **Whether it is terminal** — end of the chain

The transport chain ships as:

| # | Stage | Role | Actions |
|---|---|---|---|
| 1 | Supervisor Approval | `supervisor` | approve, decline |
| 2 | Grants Approval | `grants` | approve, decline, **amend** project + budget code |
| 3 | Transport Admin | `transport_admin` | approve, decline, **assign** vehicle + driver |
| 4 | Vehicle and Driver Assigned | — | terminal |

MeetSpace ships as a simpler chain: `pending` → `approved`, both gated on
`hr_admin`.

### Adding a module

A new requisition type needs three things and nothing else in the view layer:

1. A `Module` row (key, name, order)
2. `FormField` rows for its form
3. `WorkflowStage` rows for its chain

Plus a `ModuleURLResolver` entry in `requisition_portal/urls.py` and the
requisition model registered in `portal_config.engine.MODULE_MODELS`.

## Roles

| Role | Capabilities |
|---|---|
| **admin** | Full access — all modules, Form Builder, audit log, reports |
| **supervisor** | First-stage approval on transport and internal requests |
| **grants** | Second-stage approval; may correct project and budget codes |
| **transport_admin** | Transport approvals, vehicle/driver assignment, Form Builder access |
| **hr_admin** | MeetSpace bookings, rooms and announcements |
| **ict_admin** | ICT requisition approvals |
| **internal_admin** | Internal requisition approvals |
| **requester** | Create and view own requests only (default sign-up role) |

## Project Structure

```
├── accounts/                 # User model, roles, auth views, sign-up
├── contracts/                # HR contract management
├── employees/                # Employee records
├── ict_requisition/          # ICT requisition workflow
├── internal_requisition/    # Internal requisition workflow
├── transport_requisition/   # Transport requisition workflow
├── meetspace/                # Meeting room booking (ported from MeetSpace)
├── notifications/            # Email sending, email logs, audit log, Q tasks
├── payslip/                  # Payslip generation and requests
├── portal_config/            # Dynamic form & workflow engine
│   ├── models.py             # Module, FormField, WorkflowStage
│   ├── engine.py             # Field validation, stage transitions, value IO
│   ├── routing.py            # Module-aware URL resolver
│   └── views.py              # Form Builder and workflow editor
├── requisition_portal/       # Settings, root URLs, home/dashboard views
├── templates/                # Portal templates
├── static/                   # Static assets
├── deploy.sh                 # Production deploy script
├── run.sh                    # Gunicorn start script
├── Jenkinsfile               # CI/CD pipeline
└── .env.example              # Environment template
```

## Notes and Known Constraints

- **Template changes need a service restart.** Django 6.0 always wraps template
  loaders in `cached.Loader`, so gunicorn workers read templates from disk once
  at startup. Restart after editing any template:
  `sudo systemctl restart requisition_portal.service`

- **Email delivery requires the Q cluster.** Check `qcluster.service` is running
  if approvals go through but no mail arrives.

- **Public forms validate everything themselves.** There is no Django Form
  class behind them; validation lives in `portal_config.engine` and is driven
  by the `FormField` rows.