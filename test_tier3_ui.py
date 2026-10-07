"""
Real-browser verification of the Tier 3 React pages: documentation, signup,
the signed email-action deep links, the public track page and the
send-reminder buttons on the requisition list pages.

Same contract as test_meetspace_ui.py: every page is driven through Chromium
with assertions on what a user can actually see, and whatever the run creates
it deletes afterwards.

Run (both servers must already be up -- `.\\run.ps1` and `npm run dev`):

    venv\\Scripts\\python.exe test_tier3_ui.py             # headed (default)
    venv\\Scripts\\python.exe test_tier3_ui.py --headless   # CI / no desktop

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

WAIT = 15_000

# Everything this run creates carries these markers so cleanup can never touch
# real data.
MARK = "T3UI-"
USER_MARK = "tier3ui_"
INACTIVE_PASSWORD = "pass-12345"
SIGNUP_PASSWORD = "Sup3rSecret!"

INACTIVE_SENTENCE = (
    "Your account is pending admin approval. Please try again later."
)

# Filled in by seed_rows(), which runs before Playwright starts: Django refuses
# database access while the sync API holds an event loop open.
TR_APPROVE_ID = None
TR_APPROVE_TOKEN = None
ICT_REJECT_ID = None
ICT_REJECT_TOKEN = None
ANON_TOKEN = None
REM_TR_ID = None
REM_ICT_ID = None
REM_INT_ID = None

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


def _purge_queue():
    from django_q.brokers import get_broker
    broker = get_broker()
    for name in ("purge_queue", "purge", "delete_queue"):
        method = getattr(broker, name, None)
        if callable(method):
            return method()
    return None


def seed_rows():
    """Create the rows the parameterised routes need, plus signed action links.

    Runs before the browser launches; `purge_markers()` removes them all.
    """
    _django()

    from datetime import date

    from accounts.models import User
    from ict_requisition.models import ICTRequisition
    from internal_requisition.models import InternalRequisition
    from notifications.utils import sign_action_token
    from transport_requisition.models import TransportRequisition

    global TR_APPROVE_ID, TR_APPROVE_TOKEN, ICT_REJECT_ID, ICT_REJECT_TOKEN
    global ANON_TOKEN, REM_TR_ID, REM_ICT_ID, REM_INT_ID

    supervisor = User.objects.filter(is_superuser=True).first()

    def transport(marker):
        return TransportRequisition.objects.create(
            request_number=marker, status="pending_first",
            full_name="Tier three UI smoke", email_address="t3ui@example.com",
            mobile_number="0700000000", designation="Officer",
            pin="0000", num_passengers=1,
            pick_up_date=date(2030, 1, 10), pick_up_time="09:00",
            pick_up_location="Niketon", destination="Gulshan",
            drop_off_date=date(2030, 1, 10), drop_off_time="17:00",
            drop_off_location="Niketon", travelling_reason="Tier three UI proof",
            project_name_code="BUIED", budget_code="100")

    tr = transport(MARK + "TR")
    TR_APPROVE_ID = tr.pk
    TR_APPROVE_TOKEN = sign_action_token("transport", tr.pk, "approve", supervisor.pk)

    anon = transport(MARK + "ANON")
    ANON_TOKEN = sign_action_token("transport", anon.pk, "approve", supervisor.pk)

    rem_tr = transport(MARK + "REM-TR")
    REM_TR_ID = rem_tr.pk

    ict = ICTRequisition.objects.create(
        request_number=MARK + "ICT", status="pending_first",
        full_name="Tier three UI smoke", email_address="t3ui@example.com",
        designation="Officer", pin_number="0000", contact_number="0700000000",
        device_equipment="Tier three UI laptop", purpose="Tier three UI proof",
        requisition_date=date(2030, 1, 5), requirement_date=date(2030, 1, 20),
        supervisor=supervisor)
    ICT_REJECT_ID = ict.pk
    ICT_REJECT_TOKEN = sign_action_token("ict", ict.pk, "reject", supervisor.pk)

    rem_ict = ICTRequisition.objects.create(
        request_number=MARK + "REM-ICT", status="pending_first",
        full_name="Tier three UI smoke", email_address="t3ui@example.com",
        designation="Officer", pin_number="0000", contact_number="0700000000",
        device_equipment="Tier three UI laptop", purpose="Tier three UI proof",
        requisition_date=date(2030, 1, 5), requirement_date=date(2030, 1, 20),
        supervisor=supervisor)
    REM_ICT_ID = rem_ict.pk

    rem_int = InternalRequisition.objects.create(
        request_number=MARK + "REM-INT", status="pending_first",
        full_name="Tier three UI smoke", email_address="t3ui@example.com",
        mobile_number="0700000000", designation="Officer",
        pin="0000", department="Tier three UI department")
    REM_INT_ID = rem_int.pk

    # The account a signed-up user would try to sign in with before an
    # administrator approves it.
    User.objects.create_user(
        username=USER_MARK + "inactive", password=INACTIVE_PASSWORD,
        role="requester", is_active=False)


def _django():
    """Standalone scripts have to bootstrap Django themselves -- `manage.py`
    and `run.ps1` both do it for their own process."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "requisition_portal.settings")
    import django
    django.setup()


def purge_markers(label="cleanup", quiet=False):
    """Delete exactly what a previous run created -- nothing else."""
    _django()
    if not quiet:
        section(label)

    from accounts.models import User
    from ict_requisition.models import ICTRequisition
    from internal_requisition.models import InternalRequisition
    from notifications.models import AuditLog, EmailLog
    from transport_requisition.models import TransportRequisition

    pks = {
        "transport": list(
            TransportRequisition.objects.filter(
                request_number__startswith=MARK).values_list("id", flat=True)),
        "ict": list(
            ICTRequisition.objects.filter(
                request_number__startswith=MARK).values_list("id", flat=True)),
        "internal": list(
            InternalRequisition.objects.filter(
                request_number__startswith=MARK).values_list("id", flat=True)),
    }

    AuditLog.objects.filter(
        req_id__in=pks["transport"], req_type="transport").delete()
    AuditLog.objects.filter(req_id__in=pks["ict"], req_type="ict").delete()
    AuditLog.objects.filter(
        req_id__in=pks["internal"], req_type="internal").delete()
    EmailLog.objects.filter(
        req_id__in=pks["transport"], req_type="transport").delete()
    EmailLog.objects.filter(req_id__in=pks["ict"], req_type="ict").delete()
    EmailLog.objects.filter(
        req_id__in=pks["internal"], req_type="internal").delete()

    TransportRequisition.objects.filter(
        request_number__startswith=MARK).delete()
    ICTRequisition.objects.filter(request_number__startswith=MARK).delete()
    InternalRequisition.objects.filter(
        request_number__startswith=MARK).delete()
    User.objects.filter(username__startswith=USER_MARK).delete()

    try:
        _purge_queue()
    except Exception as exc:  # pragma: no cover - broker cleanup is best-effort
        print(f"  (queue purge skipped: {exc})")


# --------------------------------------------------------------------------
# Signed-in area
# --------------------------------------------------------------------------
def signed_in_area(browser):
    context = browser.new_context()
    page = context.new_page()
    page.on("pageerror", lambda e: PAGE_ERRORS.append(f"signed-in: {e}"))

    section("sign-in")
    check(f"signing in as {USERNAME} from /", lambda: login(page))

    section("documentation")

    check("/documentation renders the system manual", lambda: (
        goto(page, "/documentation"),
        text(page, "System Documentation"),
        text(page, "1. System Overview"),
        text(page, "10. URL Reference"),
        text(page, "⬇ Download Documentation"),
        verify(page.locator(".sidebar").count() == 0,
               "signed-in sidebar rendered on a public page"),
    ))

    check("/documentation keeps the table of contents anchors", lambda: (
        goto(page, "/documentation"),
        verify(page.locator('a[href="#overview"]').count() >= 1,
               "overview anchor missing"),
        verify(page.locator('a[href="#urls"]').count() >= 1,
               "urls anchor missing"),
        verify(page.locator('h2[id="workflow"]').count() == 1,
               "workflow section heading missing"),
    ))

    section("signup")

    check("/signup renders the registration form", lambda: (
        goto(page, "/signup"),
        text(page, "Create Account"),
        text(page, "Register for a new account"),
        text(page, "Confirm Password"),
        verify(page.locator('input[placeholder="Choose a username"]').count() == 1,
               "username field missing"),
        verify(page.locator('input[placeholder="Confirm password"]').count() == 1,
               "confirm-password field missing"),
        verify(page.locator('input[disabled]').first.is_disabled(),
               "role field is not disabled"),
        verify(page.locator('input[disabled]').first.input_value() == "requester",
               "role field does not show requester"),
        verify(page.locator(".sidebar").count() == 0,
               "signed-in sidebar rendered on a public page"),
    ))

    def mismatched():
        goto(page, "/signup")
        fill(page, 'input[name="username"]', USER_MARK + "mismatch")
        fill(page, 'input[name="password1"]', SIGNUP_PASSWORD)
        fill(page, 'input[name="password2"]', "different")
        page.locator('button:has-text("Create Account")').first.click()
        text(page, "Passwords do not match")

    check("mismatched passwords are refused with main's sentence", mismatched)

    def register():
        goto(page, "/signup")
        fill(page, 'input[name="username"]', USER_MARK + "new")
        fill(page, 'input[name="email"]', "t3ui@example.com")
        fill(page, 'input[name="phone"]', "0700000000")
        fill(page, 'input[name="password1"]', SIGNUP_PASSWORD)
        fill(page, 'input[name="password2"]', SIGNUP_PASSWORD)
        page.locator('button:has-text("Create Account")').first.click()
        text(page, "Account Pending Approval")
        text(page, "awaiting approval by an administrator")
        text(page, "Back to Login")

    check("a valid registration lands on the pending-approval card", register)

    section("track")

    check("/notifications/track renders the public status card", lambda: (
        goto(page, f"/notifications/track/transport/{TR_APPROVE_ID}"),
        text(page, "Requisition Status"),
        text(page, "Pending Approval"),
        text(page, "Awaiting supervisor approval"),
        text(page, "Details"),
        text(page, "Request #"),
        text(page, MARK + "TR"),
        verify(page.locator(".sidebar").count() == 0,
               "signed-in sidebar rendered on a public page"),
    ))

    section("email action links")

    def approve():
        goto(page, f"/notifications/action/{TR_APPROVE_TOKEN}")
        # The page resolves on GET and applies on POST, so the success card is
        # what a user sees after the link has been opened.
        text(page, "Done")
        text(page, f"Requisition #{TR_APPROVE_ID} approved at")

    check("an approval link approves and shows main's success card", approve)

    def reject():
        goto(page, f"/notifications/action/{ICT_REJECT_TOKEN}")
        text(page, f"Reject Requisition {MARK}ICT")
        text(page, "Please provide a reason for rejecting this requisition.")
        fill(page, 'textarea[name="reason"]', "Tier three UI says no")
        page.locator('button:has-text("Reject")').first.click()
        text(page, "Done")
        text(page, f"Requisition #{ICT_REJECT_ID} rejected at")

    check("a reject link shows the reason form and then main's success card",
          reject)

    def broken_link():
        goto(page, "/notifications/action/not-a-real-token/")
        text(page, "Action Failed")
        text(page, "Invalid or expired link.")

    check("a broken link shows main's error card", broken_link)

    section("send reminder")

    def remind(module, marker, row_id, stage_name):
        goto(page, f"/{module}")
        row = page.locator("tbody tr", has_text=marker)
        verify(row.count() == 1, f"{marker} row not found on /{module}")
        row.locator('button[title="Send Email Reminder"]').first.click()
        text(page, f"Approval request sent to {stage_name} for #{row_id}.")

    check("the transport list offers Send Email Reminder",
          lambda: remind("transport", MARK + "REM-TR", REM_TR_ID,
                         "Supervisor Approval"))
    check("the ICT list offers Send Email Reminder",
          lambda: remind("ict", MARK + "REM-ICT", REM_ICT_ID, "First Approval"))
    check("the internal list offers Send Email Reminder",
          lambda: remind("internal", MARK + "REM-INT", REM_INT_ID,
                         "First Approval"))

    context.close()


# --------------------------------------------------------------------------
# Public area
# --------------------------------------------------------------------------
def public_area(browser):
    context = browser.new_context()
    page = context.new_page()
    page.on("pageerror", lambda e: PAGE_ERRORS.append(f"public: {e}"))

    section("signed-out email link")

    def bounce():
        page.goto(FRONTEND + f"/notifications/action/{ANON_TOKEN}",
                  wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_url("**/login**", timeout=WAIT)
        verify("/login" in page.url, f"expected /login, landed on {page.url}")
        verify("next=" in page.url,
               f"login did not carry ?next= back to the link: {page.url}")
        text(page, "Welcome Back")

    check("an anonymous hit on an approval link lands on login with ?next=",
          bounce)

    section("login")

    check("/login offers the Sign Up link", lambda: (
        goto(page, "/login"),
        text(page, "Don't have an account?"),
        verify(page.locator('a[href="/signup"]').count() >= 1,
               "Sign Up link missing"),
    ))

    def inactive_login():
        goto(page, "/login")
        fill(page, 'input[placeholder="Enter your username"]',
             USER_MARK + "inactive")
        fill(page, 'input[placeholder="Enter your password"]',
             INACTIVE_PASSWORD)
        page.locator('form button[type="submit"]').first.click()
        text(page, INACTIVE_SENTENCE)

    check("signing in while the account is pending shows main's sentence",
          inactive_login)

    context.close()


# --------------------------------------------------------------------------
def report():
    passed = sum(1 for ok, _, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\nPASSED: {passed} / FAILED: {failed} / TOTAL: {len(RESULTS)}")
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
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

    # A crashed run must not leave its rows behind, or the parameterised-route
    # proofs below would pass vacuously.
    purge_markers("pre-clean", quiet=True)
    seed_rows()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            try:
                signed_in_area(browser)
                public_area(browser)
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
