"""
Real-browser verification of the React frontend.

Every page this port builds is driven through Chromium by Playwright, with
assertions on what a user can actually see -- not on the source that renders
it.  It is deliberately data-clean: whatever it creates it deletes, so it can
be run repeatedly against a development database.

Run (both servers must already be up -- `.\run.ps1` and `npm run dev`):

    venv\\Scripts\\python.exe test_meetspace_ui.py             # headed (default)
    venv\\Scripts\\python.exe test_meetspace_ui.py --headless   # CI / no desktop

Headed is the default because the waits are `networkidle`-based and a real
window makes a stalled load obvious instead of silently timing out; pass
`--headless` where no desktop session is available.

Exit status is 0 only when every assertion passed.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request

# Check names echo the headings they matched, emoji and all; Windows' default
# console codec would abort the run mid-print rather than report a result.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):  # pragma: no cover - exotic streams
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.environ.get("UI_BASE_URL", "http://localhost:5173")
DJANGO = os.environ.get("UI_DJANGO_URL", "http://127.0.0.1:8000")
USERNAME = os.environ.get("UI_USER", "admin")
PASSWORD = os.environ.get("UI_PASSWORD", "admin12345")

# Long enough for a cold Vite dev-server transform, short enough that a hung
# page fails the run instead of stalling it.
WAIT = 15_000

# Everything this run creates carries these markers so cleanup can never
# touch real data.
ROOM_NUMBER = "UI-TEST-01"
ROOM_FLOOR = "Ground"
BOOKING_TITLE = "UI smoke booking"
BOOKING_EMAIL = "ui.smoke@example.com"
ANNOUNCEMENT = "UI smoke announcement"
# Comfortably in the future: bookings reject past dates and the availability
# search only offers slots that are still bookable.
SLOT_DATE = "2030-03-12"
BOOKING_DATE = "2030-03-14"

# HR module (contracts / employees / payslips). Four routes are parameterised
# and need a real row to open, so each area seeds exactly one object carrying
# this PIN and nothing else -- cleanup keys off it.
HR_PIN = "UI-TEST-HR"
HR_NAME = "UI smoke employee"
HR_MONTH, HR_YEAR = "January", "2031"
UI_REQ_NAME = "UI smoke requester"
# A signed-in employee. The Requisitions menu is employees-only, and this
# account's email matches the seeded HR employee record, so the portal can
# find the row and treat the account as an employee.
UI_EMP_USER = "ui_employee"
UI_EMP_PASSWORD = "pass-12345"
# Filled in by seed_rows(), which runs before Playwright starts: Django
# refuses database access while the sync API holds an event loop open.
HR_CONTRACT_ID = None
TRANSPORT_ID = None
ICT_ID = None
INTERNAL_ID = None

# The five cards the landing page shows while only `transport` is enabled --
# i.e. the exact contents of the dashboard's Requisitions menu.
EXPECTED_MENU = [
    "Transport Request",
    "BRAC University Email",
    "ICT Requisition",
    "Mail Service",
    "Track Transport Request",
]

RESULTS: list[tuple[bool, str, str]] = []
PAGE_ERRORS: list[str] = []


def verify(condition, message):
    if not condition:
        raise AssertionError(message)


def check(name, fn):
    """Run `fn`, record PASS/FAIL, and print the result immediately."""
    try:
        detail = fn()
    except Exception as exc:  # noqa: BLE001 - the failure *is* the report
        message = (str(exc) or repr(exc)).splitlines()[0]
        RESULTS.append((False, name, message[:200]))
        print(f"  FAIL  {name}  {message[:200]}", flush=True)
        return False
    if not isinstance(detail, str):
        detail = ""
    RESULTS.append((True, name, detail))
    print(f"  PASS  {name}" + (f"  {detail}" if detail else ""), flush=True)
    return True


def section(title):
    print(f"\n=== {title} ===", flush=True)


def reach(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status < 500
    except (urllib.error.URLError, OSError):
        return False


def goto(page, path, heading=None):
    """Load a route, let it settle, and assert nothing blew up."""
    before = len(PAGE_ERRORS)
    page.goto(FRONTEND + path, wait_until="domcontentloaded", timeout=30_000)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:  # noqa: BLE001 - HMR keeps a socket open; not fatal
        pass
    verify(page.url.rstrip("/") == (FRONTEND + path).rstrip("/"),
           f"expected {path}, landed on {page.url}")
    verify(len(PAGE_ERRORS) == before,
           "uncaught JavaScript: " + " | ".join(PAGE_ERRORS[before:])[:300])
    if heading is not None:
        page.get_by_role("heading", name=heading, exact=True) \
            .first.wait_for(state="visible", timeout=WAIT)


def goto_redirect(page, path, expected):
    """Load a legacy address and assert it lands on the HR route it replaced."""
    before = len(PAGE_ERRORS)
    page.goto(FRONTEND + path, wait_until="domcontentloaded", timeout=30_000)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:  # noqa: BLE001 - HMR keeps a socket open; not fatal
        pass
    page.wait_for_url(re.compile(re.escape(expected) + r"$"), timeout=WAIT)
    verify(page.url.rstrip("/") == (FRONTEND + expected).rstrip("/"),
           f"expected {expected}, landed on {page.url}")
    verify(len(PAGE_ERRORS) == before,
           "uncaught JavaScript: " + " | ".join(PAGE_ERRORS[before:])[:300])


def text(page, needle, timeout=WAIT):
    """Wait until `needle` is on screen; returns the matched text."""
    locator = page.get_by_text(needle, exact=False).first
    locator.wait_for(state="visible", timeout=timeout)
    return locator.inner_text().strip()


def fill(page, selector, value):
    locator = page.locator(selector)
    locator.wait_for(state="visible", timeout=WAIT)
    locator.fill(value)


def click(page, selector, timeout=WAIT):
    locator = page.locator(selector).first
    locator.wait_for(state="visible", timeout=timeout)
    locator.click()
    return locator


def login(page, username=None, password=None):
    goto(page, "/")
    fill(page, 'input[placeholder="Enter your username"]',
         username if username is not None else USERNAME)
    fill(page, 'input[placeholder="Enter your password"]',
         password if password is not None else PASSWORD)
    page.locator('form button[type="submit"]').first.click()
    page.wait_for_url("**/dashboard", timeout=30_000)
    # The topbar user block renders for every role; the dashboard's own heading
    # text is role-dependent, so this is the reliable "signed in" signal.
    page.locator(".topbar-user").first.wait_for(state="visible", timeout=WAIT)
    return page.url


def expect_count(locator, count):
    """`count()` does not wait, so poll through Playwright's own expect."""
    from playwright.sync_api import expect
    expect(locator).to_have_count(count, timeout=WAIT)


# --------------------------------------------------------------------------
# Signed-in area.  Returns the live context so the booking detail can be
# checked after the public flow has created a booking.
# --------------------------------------------------------------------------
def signed_in_area(browser):
    context = browser.new_context()
    page = context.new_page()
    page.on("pageerror", lambda e: PAGE_ERRORS.append(f"signed-in: {e}"))

    section("sign-in")
    check(f"signing in as {USERNAME} from /", lambda: login(page))

    section("dashboard")

    check("dashboard renders its role-aware counters", lambda: (
        goto(page, "/dashboard", "Admin Dashboard"),
        text(page, "ICT Requisitions"),
        text(page, "Transport Requisitions"),
        text(page, "Internal Requisitions"),
        text(page, "Meeting Room Bookings"),
    ))

    def requisitions_menu():
        # The admin account has no HR employee record, so the Requisitions
        # menu is employees-only and must not render for it at all.
        verify(page.locator(
            ".topbar-requisitions button.dropdown-toggle").count() == 0,
            "the Requisitions menu rendered for the admin, who is not an employee")

    check("the admin (not an employee) gets no Requisitions menu",
          requisitions_menu)

    section("MeetSpace")

    check("/meetspace renders the MeetSpace dashboard", lambda: (
        goto(page, "/meetspace", "MeetSpace"),
        text(page, "Total_Rooms"),
        text(page, "Recent bookings"),
        text(page, "Announcements"),
        verify(page.locator('a:has-text("Find a room")').count() >= 1,
               "Find a room shortcut missing"),
        verify(page.locator('a:has-text("Manage Rooms")').count() >= 1,
               "Manage Rooms shortcut missing"),
        verify(page.locator('a[href="/meetspace/bookings/new"]').count() >= 1,
               "New Booking shortcut missing"),
        verify(page.locator(".sidebar").count() >= 1,
               "signed-in sidebar missing"),
    ))

    check("/meetspace/rooms renders the room table", lambda: (
        goto(page, "/meetspace/rooms", "Rooms — MeetSpace"),
        text(page, "Meeting rooms available for booking"),
        verify(page.get_by_text("Approved bookings", exact=True).count() >= 1,
               "booking_count column missing"),
        verify(page.get_by_text("Capacity", exact=True).count() >= 1,
               "capacity column missing"),
        verify(page.locator('a:has-text("Add Room")').count() >= 1,
               "Add Room button missing"),
    ))

    already_has_room = page.get_by_text(ROOM_NUMBER, exact=True).count() > 0

    def create_room():
        goto(page, "/meetspace/rooms/new", "Add Room — MeetSpace")
        fill(page, 'input[name="room_number"]', ROOM_NUMBER)
        fill(page, 'input[name="floor"]', ROOM_FLOOR)
        fill(page, 'input[name="min_occupancy"]', "1")
        fill(page, 'input[name="max_occupancy"]', "8")
        page.locator('button:has-text("Save")').first.click()
        page.wait_for_url("**/meetspace/rooms", timeout=WAIT)
        text(page, ROOM_NUMBER)
        text(page, "Available")

    check("Add Room creates a room",
          (lambda: "already present from a previous run in this database")
          if already_has_room else create_room)

    def duplicate_room():
        goto(page, "/meetspace/rooms/new", "Add Room — MeetSpace")
        fill(page, 'input[name="room_number"]', ROOM_NUMBER.lower())
        fill(page, 'input[name="floor"]', "Roof")
        page.locator('button:has-text("Save")').first.click()
        # main's duplicate check is case-insensitive and quotes the posted value.
        text(page, f"Room {ROOM_NUMBER.lower()} already exists.")
        click(page, 'a:has-text("Cancel")')
        page.wait_for_url("**/meetspace/rooms", timeout=WAIT)

    check("duplicate room number is rejected with main's sentence", duplicate_room)

    def edit_room():
        goto(page, "/meetspace/rooms", "Rooms — MeetSpace")
        page.locator("tbody tr", has_text=ROOM_NUMBER) \
             .locator('a[href$="/edit"]').first.click()
        page.get_by_role("heading", name="Edit Room — MeetSpace", exact=True) \
            .first.wait_for(state="visible", timeout=WAIT)
        fill(page, 'input[name="max_occupancy"]', "9")
        page.locator('button:has-text("Save")').first.click()
        page.wait_for_url("**/meetspace/rooms", timeout=WAIT)
        text(page, "1–9")

    check("Edit Room saves the new capacity", edit_room)

    check("/meetspace/availability finds a free room", lambda: (
        goto(page, "/meetspace/availability", "Find a Room — MeetSpace"),
        fill(page, 'input[name="date"]', SLOT_DATE),
        fill(page, 'input[name="start_time"]', "10:00"),
        fill(page, 'input[name="end_time"]', "11:00"),
        fill(page, 'input[name="number_of_participants"]', "4"),
        click(page, 'button:has-text("Search")'),
        text(page, "Available rooms"),
        text(page, ROOM_NUMBER),
        verify(page.locator('a:has-text("Book")').count() >= 1,
               "no Book action on the availability result"),
    ))

    def announcement_guard():
        goto(page, "/meetspace/announcements/new", "Post Announcement — MeetSpace")
        page.locator('button:has-text("Post")').first.click()
        text(page, "Provide announcement text, an attachment, or both.")

    check("empty announcement is rejected with main's sentence", announcement_guard)

    def post_announcement():
        goto(page, "/meetspace/announcements/new", "Post Announcement — MeetSpace")
        page.locator("form textarea").first.fill(ANNOUNCEMENT)
        page.locator('button:has-text("Post")').first.click()
        page.wait_for_url("**/meetspace", timeout=WAIT)
        text(page, ANNOUNCEMENT)

    check("posting an announcement returns to the dashboard", post_announcement)

    check("/meetspace/bookings renders the request table", lambda: (
        goto(page, "/meetspace/bookings", "Bookings — MeetSpace"),
        verify(page.get_by_text("Meeting", exact=True).count() >= 1,
               "Meeting column missing"),
        verify(page.get_by_text("Status", exact=True).count() >= 1,
               "Status column missing"),
    ))

    section("remaining routes render")

    ROUTES = [
        ("/my-requisitions", "My Requisitions"),
        ("/profile", "My Profile"),
        ("/transport", "Transport Requisitions"),
        ("/transport/history", "Tracking History"),
        ("/transport/report", "Transport Requisition Report"),
        ("/ict", "ICT Requisitions"),
        ("/ict/create", "ICT Requisitions"),
        ("/internal", "Internal Requisitions"),
        ("/internal/create", "Internal Requisitions"),
        ("/admin/users", "User Management"),
        ("/admin/users/create", "User Management"),
        ("/admin/form-builder", "Portal Configuration"),
        ("/admin/form-builder/fields?module=transport", "Portal Configuration"),
        ("/admin/form-builder/fields/new?module=transport", "Portal Configuration"),
        ("/admin/workflow-editor?module=transport", "Approval Workflow"),
        ("/admin/email-settings", "Email Configurations"),
        ("/admin/email-logs", "Email Logs"),
        ("/admin/audit-log", "Audit Log"),
    ]
    for path, title in ROUTES:
        check(f"{path} renders {title!r}",
              lambda p=path, t=title: goto(page, p, t))

    # Tier 2C moved the HR pages under /hr/... so their paths mirror
    # module_include('hr', ...) in the project urls; the addresses the portal
    # sidebar used to point at must still resolve.
    for legacy, target in (("/contracts", "/hr/contracts"),
                           ("/employees", "/hr/employees"),
                           ("/payslips", "/hr/payslip/list")):
        check(f"{legacy} redirects to {target}",
              lambda l=legacy, e=target: goto_redirect(page, l, e))

    # The detail routes are keyed on a seeded row, so assert on that row's
    # name actually reaching the screen -- proof the page read the record
    # rather than merely rendering a shell.
    check("seed rows are available", lambda: verify(
        TRANSPORT_ID and ICT_ID and INTERNAL_ID and HR_CONTRACT_ID,
        "seed_rows() did not run -- no ids for the detail routes"))
    for path in (f"/transport/{TRANSPORT_ID}",
                 f"/ict/{ICT_ID}",
                 f"/internal/{INTERNAL_ID}"):
        check(f"{path} shows the seeded record",
              lambda p=path: (goto(page, p),
                              text(page, UI_REQ_NAME)))

    check("Form Builder lists real fields", lambda: (
        goto(page, "/admin/form-builder/fields?module=transport",
             "Portal Configuration"),
        text(page, "Form fields"),
        verify(page.locator("tbody tr").count() > 0,
               "field list is empty -- Form Builder would be a dead screen"),
    ))

    def edit_field_route():
        goto(page, "/admin/form-builder/fields?module=transport",
             "Portal Configuration")
        text(page, "Form fields")
        page.locator("tbody tr").first.locator('a[href*="/edit"]').first.click()
        page.wait_for_url(re.compile(
            r"/admin/form-builder/fields/\d+/edit"), timeout=WAIT)
        page.get_by_role("heading", name="Portal Configuration", exact=True) \
            .first.wait_for(state="visible", timeout=WAIT)

    check("/admin/form-builder/fields/:id/edit resolves", edit_field_route)

    def edit_user_route():
        goto(page, "/admin/users", "User Management")
        page.locator("tbody tr").first.locator('a[href*="/edit"]').first.click()
        page.wait_for_url(re.compile(r"/admin/users/\d+/edit"), timeout=WAIT)
        page.get_by_role("heading", name="User Management", exact=True) \
            .first.wait_for(state="visible", timeout=WAIT)
        verify(page.locator(f'input[value="{USERNAME}"]').count() >= 1
               or page.locator("form input").count() >= 3,
               "the edit form rendered no fields")

    check("/admin/users/:id/edit resolves", edit_user_route)

    check("User Management lists real users", lambda: (
        goto(page, "/admin/users", "User Management"),
        text(page, USERNAME),
    ))

    check("an unknown route renders the 404 page",
          lambda: goto(page, "/this-route-does-not-exist", "Page Not Found"))

    return context, page


def hr_area(page):
    """Every route the HR module builds, each inside contracts/base.html's
    shell -- which is a *different* shell from the portal sidebar, because
    main renders these pages from the HR base template rather than base.html.
    """

    section("HR module (contracts / employees / payslips)")

    ROUTES = [
        ("/hr/contracts", "Contracts dashboard"),
        ("/hr/contracts/list", "Contracts dashboard"),
        ("/hr/contracts/create", "Create Contract"),
        ("/hr/contracts/bulk-create", "Bulk Upload Contracts (CSV)"),
        (f"/hr/contracts/email/{HR_CONTRACT_ID}", "📧 Send Contract via Email"),
        ("/hr/contracts/bulk-email", "Bulk Email Contracts"),
        ("/hr/contracts/manual", "📖 HR Contract System Manual"),
        ("/hr/contracts/email-log", "📧 Email Log"),
        ("/hr/contracts/email-settings", "⚙️ Email Settings"),
        ("/hr/employees", "Employees"),
        ("/hr/employees/add", "Add Employee"),
        (f"/hr/employees/edit/{HR_PIN}", "Edit Employee"),
        (f"/hr/employees/delete/{HR_PIN}", "Delete Employee"),
        ("/hr/employees/import", "Import Employees"),
        (f"/hr/employees/detail/{HR_PIN}", "👤 Employee Details"),
        ("/hr/payslip", "Create Payslip"),
        ("/hr/payslip/list", "Payslip List"),
        ("/hr/payslip/bulk", "Bulk Upload Payslip (CSV)"),
        ("/hr/payslip/requests", "Payslip Requests"),
    ]
    for path, title in ROUTES:
        check(f"{path} renders {title!r}",
              lambda p=path, t=title: goto(page, p, t))

    def shell_is_the_hr_base():
        goto(page, "/hr/contracts", "Contracts dashboard")
        page.locator(".hr-sidebar").first.wait_for(state="visible", timeout=WAIT)
        verify(page.locator(".sidebar").count() == 0,
               "the portal sidebar leaked into the HR shell")
        verify(page.locator(".topbar").count() == 0,
               "the portal topbar leaked into the HR shell")
        text(page, "Contract Management")
        text(page, "MAIN MENU")

    check("HR routes use the HR shell, not the portal sidebar",
          shell_is_the_hr_base)

    def lit_items(path, heading, expected):
        goto(page, path, heading)
        names = [re.sub(r"\s+", " ", n).strip()
                 for n in page.locator(".hr-sidebar a.active")
                               .all_inner_texts()]
        for want in expected:
            verify(any(want in n for n in names),
                   f"{path}: {want!r} not lit (saw {names})")
        for n in names:
            verify(any(want in n for want in expected),
                   f"{path}: unexpected {n!r} lit (want {expected})")
        return f"{len(names)} lit"

    # main's base.html marks items with plain `in request.path` tests, so a
    # few paths light two entries at once. Reproduced rather than tidied.
    check("bulk-create lights Create Contract and Bulk Contracts",
          lambda: lit_items("/hr/contracts/bulk-create",
                            "Bulk Upload Contracts (CSV)",
                            ["Create Contract", "Bulk Contracts"]))
    check("payslip/requests lights Create Payslip and Payslip Requests",
          lambda: lit_items("/hr/payslip/requests", "Payslip Requests",
                            ["Create Payslip", "Payslip Requests"]))
    check("a contract email page lights nothing",
          lambda: lit_items(f"/hr/contracts/email/{HR_CONTRACT_ID}",
                            "📧 Send Contract via Email", []))

    check("/hr/contracts/bulk-email-status falls back to the list",
          lambda: goto_redirect(page, "/hr/contracts/bulk-email-status",
                                "/hr/contracts/list"))

    def public_request_form():
        """request_form.html is standalone: no sidebar, no session needed."""
        goto(page, "/hr/payslip/request")
        verify(page.locator(".hr-sidebar").count() == 0,
               "the HR shell wrapped the public payslip-request page")
        text(page, "Payslip Request")
        text(page, "Back to Home")
        page.fill('input[name="name"]', HR_NAME)
        page.fill('input[name="pin"]', HR_PIN)
        page.locator('input[name="selected_months"]').first.check()
        page.click('button[type="submit"]')
        text(page, "Your payslip request has been submitted successfully!")

    check("the public payslip-request form submits", public_request_form)


def booking_detail(page):
    """Runs after the public flow, which is what creates the booking."""

    def open_booking_detail():
        goto(page, "/meetspace/bookings", "Bookings — MeetSpace")
        page.locator(f'tr:has-text("{BOOKING_TITLE}") a').first.click()
        page.wait_for_url(re.compile(r"/meetspace/bookings/\d+"), timeout=WAIT)
        page.get_by_role("heading", name=re.compile(r"^Booking #\d+ — MeetSpace$"),
                         exact=True).first.wait_for(state="visible", timeout=WAIT)
        text(page, ROOM_NUMBER)
        text(page, "Projector")

    section("booking detail (signed in)")
    check("booking detail opens with its own title", open_booking_detail)


# --------------------------------------------------------------------------
# Employee area -- the Requisitions menu, which is employees-only
# --------------------------------------------------------------------------
def employee_area(browser):
    """The same menu seen by an account that *is* an employee.

    The admin has no HR employee record, so the button is hidden for it; this
    account's email matches the seeded employee record, so the portal finds the
    row and renders the menu.
    """
    context = browser.new_context()
    page = context.new_page()
    page.on("pageerror", lambda e: PAGE_ERRORS.append(f"employee: {e}"))

    section("employee requisitions menu")

    check(f"signing in as {UI_EMP_USER}",
          lambda: login(page, UI_EMP_USER, UI_EMP_PASSWORD))

    def menu():
        btn = page.locator(".topbar-requisitions button.dropdown-toggle")
        btn.first.wait_for(state="visible", timeout=WAIT)
        click(page, ".topbar-requisitions button.dropdown-toggle")
        items = page.locator(
            ".topbar-requisitions .dropdown-menu.show a.dropdown-item")
        expect_count(items, 5)
        labels = [t.strip() for t in items.all_inner_texts()]
        verify(labels == EXPECTED_MENU,
               f"menu holds {labels}, expected {EXPECTED_MENU}")

    check("an employee gets the 5-entry Requisitions menu", menu)

    context.close()


# --------------------------------------------------------------------------
# Public area -- fresh, anonymous browser context
# --------------------------------------------------------------------------
def public_area(browser):
    context = browser.new_context()
    page = context.new_page()
    page.on("pageerror", lambda e: PAGE_ERRORS.append(f"public: {e}"))

    section("public pages (no session)")

    def root_is_login():
        goto(page, "/")
        text(page, "Welcome Back")
        text(page, "Sign in to your account")
        verify(page.get_by_role("heading",
                                name="BRAC IED Central Portal",
                                exact=True).count() == 0,
               "the landing page leaked onto /")
        verify(page.locator(".pub-topbar").count() == 0,
               "/ is showing the landing page shell instead of the login screen")

    check("/ renders the sign-in page, not a home page", root_is_login)

    check("/login renders the same sign-in page", lambda: (
        goto(page, "/login", "Welcome Back"),
        verify(page.locator('input[placeholder="Enter your username"]').is_visible(),
               "username field missing"),
    ))

    check("/home still hosts the landing page", lambda: (
        goto(page, "/home", "BRAC IED Central Portal"),
        text(page, "Staff Sign In"),
    ))

    def landing_cards():
        goto(page, "/home", "BRAC IED Central Portal")
        for label in EXPECTED_MENU + ["Staff Sign In"]:
            text(page, label)
        verify(page.get_by_text("Meeting Room Booking", exact=False).count() == 0,
               "a module-gated card leaked past VISIBLE_MODULES")
        verify(page.get_by_text("Track Meeting Room Booking", exact=False).count() == 0,
               "a module-gated card leaked past VISIBLE_MODULES")

    check("landing shows exactly the gated cards", landing_cards)

    check("/transport/create uses the public shell", lambda: (
        # Step 1 opens on the DOS AND DON'TS notes, so the step title only
        # lives in the progress rail -- assert the form's own header instead.
        goto(page, "/transport/create"),
        text(page, "BRAC IED Vehicle Requisition Form"),
        text(page, "Personal Information"),
        text(page, "Staff Sign In"),
        verify(page.locator(".sidebar").count() == 0,
               "signed-in sidebar rendered on a public page"),
    ))

    check("/transport/track uses the public shell", lambda: (
        goto(page, "/transport/track", "Track Your Transport Request"),
        text(page, "Staff Sign In"),
        verify(page.locator(".sidebar").count() == 0,
               "signed-in sidebar rendered on a public page"),
    ))

    section("public booking flow")

    def booking_form_available():
        goto(page, "/meetspace/bookings/new")
        # "Request a room" is a card header, not a heading element.
        text(page, "Request a room")
        text(page, "Staff Sign In")
        verify(page.locator(
            f'select[name="room"] option:has-text("{ROOM_NUMBER}")').count() == 1,
            f"{ROOM_NUMBER} missing from the room picker")
        verify(page.locator(".sidebar").count() == 0,
               "signed-in sidebar rendered on a public page")

    check("/meetspace/bookings/new offers a room without a session",
          booking_form_available)

    def submit_booking():
        goto(page, "/meetspace/bookings/new")
        text(page, "Request a room")
        fill(page, 'input[name="meeting_title"]', BOOKING_TITLE)
        page.select_option('select[name="room"]', index=1)
        fill(page, 'input[name="number_of_participants"]', "4")
        fill(page, 'input[name="date"]', BOOKING_DATE)
        fill(page, 'input[name="start_time"]', "09:00")
        fill(page, 'input[name="end_time"]', "10:00")
        fill(page, 'input[name="email_address"]', BOOKING_EMAIL)
        fill(page, 'textarea[name="requirements"]', "Projector")
        page.locator('button:has-text("Submit request")').first.click()
        text(page, "Booking Submitted")
        text(page, "The HR admin will review it")
        text(page, BOOKING_TITLE)
        text(page, ROOM_NUMBER)
        text(page, "Pending")
        # main renders booking_submitted.html at the very same URL.
        verify(page.url.endswith("/meetspace/bookings/new"),
               f"confirmation left the form URL: {page.url}")

    check("submitting creates the booking and shows the confirmation", submit_booking)

    check("track finds the booking by its posted email", lambda: (
        goto(page, "/meetspace/track", "Track Your Booking"),
        fill(page, "#email", BOOKING_EMAIL),
        click(page, 'form button:has-text("Track")'),
        text(page, "found for"),
        text(page, BOOKING_TITLE),
        text(page, ROOM_NUMBER),
        text(page, "Projector"),
    ))

    check("track hides other people's bookings", lambda: (
        goto(page, "/meetspace/track", "Track Your Booking"),
        fill(page, "#email", "nobody-else@example.com"),
        click(page, 'form button:has-text("Track")'),
        text(page, "No bookings found for"),
    ))

    def anonymous_bounce():
        page.goto(FRONTEND + "/transport", wait_until="domcontentloaded",
                  timeout=30_000)
        page.wait_for_url("**/login", timeout=WAIT)
        text(page, "Welcome Back")

    check("an anonymous hit on a staff route lands on /login", anonymous_bounce)

    context.close()


# --------------------------------------------------------------------------
# Data hygiene
# --------------------------------------------------------------------------
def load_dotenv():
    """`manage.py` and `run.ps1` both source .env; a bare interpreter does not."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def seed_rows():
    """Create one row per model that a parameterised route needs to open.

    Runs before the browser launches; `purge_markers()` removes them all.
    Nothing here is unique-constrained except `request_number`, which each
    model's `save()` fills in only when it is empty -- so a marker is passed
    explicitly and cleanup keys off it.
    """
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "requisition_portal.settings")
    import django
    django.setup()

    from datetime import date

    from accounts.models import User
    from contracts.models import Contract
    from employees.models import Employee
    from ict_requisition.models import ICTRequisition
    from internal_requisition.models import InternalRequisition
    from payslip.models import Payslip, PayslipRequest
    from transport_requisition.models import TransportRequisition

    global HR_CONTRACT_ID, TRANSPORT_ID, ICT_ID, INTERNAL_ID

    # ---- HR -------------------------------------------------------------
    contract, _ = Contract.objects.get_or_create(
        pin=HR_PIN,
        defaults={"name": HR_NAME, "designation": "Officer", "salary": 5000,
                  "start_date": date(2030, 1, 1),
                  "end_date": date(2030, 12, 31),
                  "contract_type": "New"})
    HR_CONTRACT_ID = contract.pk
    Employee.objects.get_or_create(
        pin=HR_PIN,
        defaults={"name": HR_NAME, "designation": "Officer",
                  "email": BOOKING_EMAIL, "salary": 5000, "gender": "F",
                  "phone": "0700000000", "tin": "T-1"})
    Payslip.objects.get_or_create(
        pin=HR_PIN, month=HR_MONTH, year=HR_YEAR,
        defaults={"name": HR_NAME, "designation": "Officer",
                  "basic_salary": 5000, "house_rent": 3000,
                  "medical_allowance": 1000, "conveyance": 1000,
                  "transport": 500})
    PayslipRequest.objects.get_or_create(
        name=HR_NAME, pin=HR_PIN, months=f"{HR_MONTH}, February",
        year=HR_YEAR)

    # ---- detail routes --------------------------------------------------
    supervisor = User.objects.filter(is_superuser=True).first()

    transport, _ = TransportRequisition.objects.get_or_create(
        request_number="UI-TEST-TR",
        defaults={"full_name": UI_REQ_NAME, "email_address": BOOKING_EMAIL,
                  "mobile_number": "0700000000", "designation": "Officer",
                  "pin": HR_PIN, "num_passengers": 1,
                  "pick_up_date": date(2030, 1, 10),
                  "pick_up_time": "09:00", "pick_up_location": "Niketon",
                  "destination": "Gulshan", "drop_off_date": date(2030, 1, 10),
                  "drop_off_time": "17:00", "drop_off_location": "Niketon",
                  "travelling_reason": "UI smoke trip",
                  "project_name_code": "BUIED", "budget_code": "100"})
    TRANSPORT_ID = transport.pk

    ict, _ = ICTRequisition.objects.get_or_create(
        request_number="UI-TEST-ICT",
        defaults={"full_name": UI_REQ_NAME, "email_address": BOOKING_EMAIL,
                  "designation": "Officer", "pin_number": HR_PIN,
                  "contact_number": "0700000000",
                  "device_equipment": "UI smoke laptop",
                  "purpose": "UI smoke proof",
                  "requisition_date": date(2030, 1, 5),
                  "requirement_date": date(2030, 1, 20),
                  "supervisor": supervisor})
    ICT_ID = ict.pk

    internal, _ = InternalRequisition.objects.get_or_create(
        request_number="UI-TEST-INT",
        defaults={"full_name": UI_REQ_NAME, "email_address": BOOKING_EMAIL,
                  "mobile_number": "0700000000", "designation": "Officer",
                  "pin": HR_PIN, "department": "UI smoke department"})
    INTERNAL_ID = internal.pk

    # A signed-in employee, so the employees-only Requisitions menu has
    # someone to render for. Its email matches the seeded employee record,
    # which is what /api/employees/mine/ matches on.
    User.objects.create_user(
        username=UI_EMP_USER, password=UI_EMP_PASSWORD,
        role=User.Role.REQUESTER, email=BOOKING_EMAIL)


def purge_markers(label="cleanup", quiet=False):
    """Delete exactly what a previous run created -- nothing else."""
    section(label)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "requisition_portal.settings")
    import django
    django.setup()

    from django.db.models import Q

    from contracts.models import Contract
    from employees.models import Employee
    from ict_requisition.models import ICTRequisition
    from internal_requisition.models import InternalRequisition
    from meetspace.models import Announcement, Booking, Room
    from payslip.models import Payslip, PayslipRequest
    from transport_requisition.models import TransportRequisition

    from accounts.models import User as PortalUser

    bookings = Booking.objects.filter(
        Q(meeting_title=BOOKING_TITLE) | Q(email_address__iexact=BOOKING_EMAIL))
    rooms = Room.objects.filter(room_number__iexact=ROOM_NUMBER)
    announcements = Announcement.objects.filter(message__icontains=ANNOUNCEMENT)
    hr_contracts = Contract.objects.filter(pin=HR_PIN)
    hr_employees = Employee.objects.filter(pin=HR_PIN)
    hr_payslips = Payslip.objects.filter(pin=HR_PIN)
    hr_requests = PayslipRequest.objects.filter(pin=HR_PIN)
    tr_reqs = TransportRequisition.objects.filter(
        request_number__startswith="UI-TEST-")
    ict_reqs = ICTRequisition.objects.filter(
        request_number__startswith="UI-TEST-")
    int_reqs = InternalRequisition.objects.filter(
        request_number__startswith="UI-TEST-")

    removed_rooms = rooms.count()
    removed_bookings = bookings.count()
    removed_announcements = announcements.count()
    removed_hr = (hr_contracts.count() + hr_employees.count()
                  + hr_payslips.count() + hr_requests.count())
    removed_requisitions = tr_reqs.count() + ict_reqs.count() + int_reqs.count()

    bookings.delete()
    rooms.delete()
    announcements.delete()
    hr_requests.delete()
    hr_payslips.delete()
    hr_contracts.delete()
    hr_employees.delete()
    int_reqs.delete()
    ict_reqs.delete()
    tr_reqs.delete()
    PortalUser.objects.filter(username=UI_EMP_USER).delete()

    if not quiet:
        def leftovers_are_gone():
            verify(Room.objects.filter(
                room_number__iexact=ROOM_NUMBER).count() == 0,
                "the test room survived cleanup")
            verify(Booking.objects.filter(
                meeting_title=BOOKING_TITLE).count() == 0,
                "the test booking survived cleanup")
            verify(Announcement.objects.filter(
                message__icontains=ANNOUNCEMENT).count() == 0,
                "the test announcement survived cleanup")
            verify(Contract.objects.filter(pin=HR_PIN).count() == 0,
                   "the test contract survived cleanup")
            verify(Employee.objects.filter(pin=HR_PIN).count() == 0,
                   "the test employee survived cleanup")
            verify(Payslip.objects.filter(pin=HR_PIN).count() == 0,
                   "the test payslip survived cleanup")
            verify(PayslipRequest.objects.filter(pin=HR_PIN).count() == 0,
                   "the test payslip request survived cleanup")
            verify(tr_reqs.count() + ict_reqs.count() + int_reqs.count() == 0,
                   "a seeded requisition survived cleanup")

        check("no test data left behind", leftovers_are_gone)

    print(f"  (removed {removed_rooms} rooms, {removed_bookings} bookings, "
          f"{removed_announcements} announcements, {removed_hr} HR rows, "
          f"{removed_requisitions} requisitions)",
          flush=True)


def report():
    passed = sum(1 for ok, _, _ in RESULTS if ok)
    failed = sum(1 for ok, _, _ in RESULTS if not ok)
    if PAGE_ERRORS:
        print("\nuncaught JavaScript exceptions:", flush=True)
        for message in PAGE_ERRORS:
            print(f"  - {message[:300]}", flush=True)
    print(f"\nPASSED: {passed}   FAILED: {failed}", flush=True)
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true",
                        help="run without a visible browser window")
    args = parser.parse_args()

    section("preflight")
    check("React dev server is up", lambda: verify(
        reach(FRONTEND), f"{FRONTEND} is not answering -- run `npm run dev`"))
    check("Django API is up", lambda: verify(
        reach(f"{DJANGO}/api/public/modules/"),
        f"{DJANGO} is not answering -- run `.\\run.ps1`"))

    # Fail before launching a browser if either server is down: a missing API
    # and a broken frontend produce the same confusing blank-page failures.
    if any(not ok for ok, _, _ in RESULTS):
        return report()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        RESULTS.append((False, "playwright is installed",
                        "pip install playwright && playwright install chromium"))
        print("  FAIL  playwright is installed  "
              "pip install playwright && playwright install chromium", flush=True)
        return report()

    # A crashed run must not leave its room/booking behind, or the "Add Room"
    # and "opens the new booking" proofs below would pass vacuously.
    purge_markers("pre-clean", quiet=True)
    seed_rows()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            try:
                auth_context, auth_page = signed_in_area(browser)
                employee_area(browser)
                hr_area(auth_page)
                public_area(browser)
                booking_detail(auth_page)
            finally:
                browser.close()
    finally:
        # Outside the Playwright block: its sync API keeps an event loop alive
        # in this thread, and Django refuses database access under one.
        purge_markers()

    check("no uncaught JavaScript exceptions", lambda: verify(
        len(PAGE_ERRORS) == 0, f"{len(PAGE_ERRORS)} page errors"))
    return report()


if __name__ == "__main__":
    sys.exit(main())
