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


def login(page):
    goto(page, "/")
    fill(page, 'input[placeholder="Enter your username"]', USERNAME)
    fill(page, 'input[placeholder="Enter your password"]', PASSWORD)
    page.locator('form button[type="submit"]').first.click()
    page.wait_for_url("**/dashboard", timeout=30_000)
    page.get_by_role("heading", name="Admin Dashboard", exact=True) \
        .first.wait_for(state="visible", timeout=WAIT)
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
        click(page, ".topbar-requisitions button.dropdown-toggle")
        menu = page.locator(".topbar-requisitions .dropdown-menu.show a.dropdown-item")
        expect_count(menu, 5)
        items = [t.strip() for t in menu.all_inner_texts()]
        verify(items == EXPECTED_MENU,
               f"menu holds {items}, expected {EXPECTED_MENU}")

    check("Requisitions menu holds exactly 5 entries", requisitions_menu)

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
        ("/contracts", "Contracts"),
        ("/employees", "Employees"),
        ("/payslips", "Payslips"),
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

    from meetspace.models import Announcement, Booking, Room

    bookings = Booking.objects.filter(
        Q(meeting_title=BOOKING_TITLE) | Q(email_address__iexact=BOOKING_EMAIL))
    rooms = Room.objects.filter(room_number__iexact=ROOM_NUMBER)
    announcements = Announcement.objects.filter(message__icontains=ANNOUNCEMENT)

    removed_rooms = rooms.count()
    removed_bookings = bookings.count()
    removed_announcements = announcements.count()

    bookings.delete()
    rooms.delete()
    announcements.delete()

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

        check("no test data left behind", leftovers_are_gone)

    print(f"  (removed {removed_rooms} rooms, {removed_bookings} bookings, "
          f"{removed_announcements} announcements)", flush=True)


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

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            try:
                auth_context, auth_page = signed_in_area(browser)
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
