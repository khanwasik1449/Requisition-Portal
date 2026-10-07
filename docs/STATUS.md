# Port Status — `Farah` (React) against `main` (Django templates)

This branch keeps the Django backend exactly as `main` ships it — same models,
same views, same templates, same routes — and adds a parallel `/api/` layer so
a React front end can reproduce those pages. `.\run.ps1` still starts the
original application unchanged.

## Validation legend

| Value | What it means |
| --- | --- |
| **Real UI-validated** | Driven end-to-end in a real Chromium browser by `test_meetspace_ui.py`, asserting on what a user can actually see (rendered headings, on-screen text, resulting navigation) — not on the source that produces it. |
| **Real API-validated** | Exercised end-to-end over the HTTP layer the React pages call, asserting on the same sentences and status codes the Django views emit. |

Every area reached so far carries **Real UI-validated**: each one is visited by
`test_meetspace_ui.py`, which loads the route in Chromium, waits for it to
settle, fails on any uncaught JavaScript, and matches the page's heading.

## Area status

| Area | Routes covered | Validation |
| --- | --- | --- |
| Sign-in & routing | `/` → sign-in (no home page), `/login`, `/home` landing, 404 | **Real UI-validated** |
| Dashboard | role-aware counters, **Requisitions** menu holding exactly 5 entries | **Real UI-validated** |
| Transport requisitions | `/transport`, `/transport/create`, `/transport/:id`, `/transport/history`, `/transport/report`, `/transport/track` | **Real UI-validated** |
| ICT requisitions | `/ict`, `/ict/create`, `/ict/:id` | **Real UI-validated** |
| Internal requisitions | `/internal`, `/internal/create`, `/internal/:id` | **Real UI-validated** |
| My requisitions & profile | `/my-requisitions`, `/profile` | **Real UI-validated** |
| Admin — users | `/admin/users`, `.../create`, `.../:id/edit` | **Real UI-validated** |
| Admin — form builder | `/admin/form-builder`, field list, field create & edit | **Real UI-validated** |
| Admin — workflow editor | `/admin/workflow-editor` | **Real UI-validated** |
| Admin — email & audit | `/admin/email-settings`, `/admin/email-logs`, `/admin/audit-log` | **Real UI-validated** |
| MeetSpace | dashboard, rooms (create/edit/duplicate), availability, announcement, bookings, booking detail, public booking + confirmation, public track | **Real UI-validated** |
| HR — contracts | `/hr/contracts`, `/list`, `/create`, `/bulk-create`, `/email/:id`, `/bulk-email`, `/bulk-email-status`, `/manual`, `/email-log`, `/email-settings` | **Real UI-validated** |
| HR — employees | `/hr/employees`, `/add`, `/edit/:pin`, `/delete/:pin`, `/import`, `/detail/:pin` | **Real UI-validated** |
| HR — payslips | `/hr/payslip`, `/list`, `/bulk`, `/requests`, plus the public `/hr/payslip/request` | **Real UI-validated** |
| Legacy HR addresses | `/contracts`, `/employees`, `/payslips` → their `/hr/...` targets | **Real UI-validated** |
| HR shell | pages render inside `contracts/base.html`'s own sidebar, with the portal sidebar absent, and main's `in request.path` active-state quirks reproduced | **Real UI-validated** |

## Evidence

Re-run these yourself; each prints `PASSED: n / FAILED: 0` and exits 0.

| Suite | Scope | Result |
| --- | --- | --- |
| `test_meetspace_ui.py` | every page above, driven through Chromium | **PASSED: 83 / FAILED: 0** |
| `test_hr_api.py` | contracts, employees and payslips over the API | **PASSED: 82 / FAILED: 0** |
| `test_meetspace_api.py` | MeetSpace over the API | **PASSED: 60 / FAILED: 0** |
| `test_formbuilder_api.py` | Form Builder field CRUD | **PASSED: 20 / FAILED: 0** |
| `test_users_api.py` | admin user create/edit | **PASSED: 12 / FAILED: 0** |
| `npx tsc --noEmit` | front-end type check | 0 errors |
| `npm run build` | production build | succeeded |
| `python manage.py check` | Django project check | 0 issues |

```powershell
# both servers must be up:  .\run.ps1   and   npm run dev   (in frontend\)
venv\Scripts\python.exe test_meetspace_ui.py           # headed
venv\Scripts\python.exe test_meetspace_ui.py --headless
venv\Scripts\python.exe test_hr_api.py
```

`test_meetspace_ui.py` is deliberately data-clean: whatever it creates it
deletes, keyed off `UI-TEST-*` markers, so it can run repeatedly against a
development database. It seeds one row per parameterised route (a contract, an
employee, a payslip, a payslip request, and one transport / ICT / internal
requisition) and asserts on that record actually reaching the screen, so the
detail routes are proven to read real data rather than render an empty shell.
After a full run the database is back to its starting census — 0 contracts,
0 employees, 0 payslips, 0 payslip requests, 0 rooms, 0 bookings,
0 announcements, 0 queued tasks, 27 form fields, users `['admin']`.

> One exception: opening **Email Settings** inserts a default `EmailConfig`
> row. `main`'s `contracts.views.email_settings` calls
> `EmailConfig.get_config()`, which `get_or_create`s it on the GET as well, so
> the row is what the original application produces too — it is not test
> residue.

## Deliberate divergences from `main`

1. **`/hr/contracts/list` shows every contract.** `main`'s `contract_list`
   server-slices to 15 rows, so its six stat cards and its pager only ever
   describe page 1 — rows 16+ are unreachable without hand-typing `?page=2`.
   The React list fetches all rows and pages client-side, which is what `main`'s
   *dashboard* (`/contracts`, also `contracts/list.html`) does. The difference
   is invisible at or below 15 contracts.
2. **PDF endpoints answer `501`, not `500`.** WeasyPrint needs the Pango /
   GObject system libraries, which Windows does not ship — that is exactly why
   `requirements-windows.txt` omits it, and `main` raises a 500 for the same
   reason. The API instead returns `{"detail": ..., "code": "pdf_unavailable"}`
   and the pages surface that sentence.
3. **Contract e-mail fails on this host with main's own sentence**,
   `Failed to send email: ...`, because main attaches that PDF to the message
   and the PDF cannot be rendered here. The failure is logged to `contracts`'
   `EmailLog`, exactly as main logs it.
4. **`field_edit` returns `400` where `main` returns `500`** on a duplicate key.
5. **Employee edit/delete are PIN-addressed in the SPA**
   (`/hr/employees/edit/:pin`) while `main`'s Django routes use a numeric pk.
   The REST layer is PIN-keyed throughout — `EmployeeViewSet.lookup_field = 'pin'`
   — because every `employees/urls.py` route addresses a row by PIN.
6. **Bulk e-mail stays `pending` here.** `run.ps1` starts only `runserver`; the
   README documents `qcluster` as a separate service, and no worker runs in this
   environment. `main` behaves identically without `qcluster`. The test proves
   the status endpoint by inserting the `Success`/`Failure` rows a worker would.

## Notes

- **Role model unchanged.** The React role select hardcodes `main`'s 7 roles and
  appends the record's own role if it is missing.
- **Flash messages.** Django's `messages` framework has no SPA equivalent, so
  `frontend/src/lib/flash.ts` carries one message per navigation and
  `HrLayout` drains it on every route change.
- **HR shell is separate on purpose.** `contracts/base.html` is a different
  shell from `base.html`, so `HrLayout` uses its own `.hr-*` class family rather
  than the portal's `.sidebar` / `.topbar` / `.content-card`; the two never leak
  rules into each other.
