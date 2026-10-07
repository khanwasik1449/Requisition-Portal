"""Tier 3 backend probe: documentation, self-registration, the signed
email-action deep links, the public track page and send-reminder.

Every assertion mirrors the corresponding Django view sentence-for-sentence
(`requisition_portal.views.documentation`, `accounts.views.signup`,
`notifications.views.email_action_view` / `track_view` / `send_reminder`).

Run:  venv\\Scripts\\python.exe test_tier3_api.py
Exit code 0 = all green.
"""
import os
import sys

# Several assertions print the server's own copy verbatim, emoji and all;
# Windows' default console codepage would abort the run mid-print.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):  # pragma: no cover - exotic streams
    pass

sys.path.insert(0, r'D:\Requisition-Portal')
os.chdir(r'D:\Requisition-Portal')

# run.ps1 loads .env into the process; standalone scripts have to do it too
# (settings.py reads os.environ['DJANGO_SECRET_KEY'] unguarded).
_env = os.path.join(r'D:\Requisition-Portal', '.env')
if os.path.exists(_env):
    with open(_env, encoding='utf-8') as _fh:
        for _line in _fh:
            _line = _line.strip()
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _k, _, _v = _line.partition('=')
            os.environ.setdefault(_k.strip(), _v.strip())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'requisition_portal.settings')
import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

# The script talks to the views over the test client directly; without this
# the default `testserver` host is rejected by ALLOWED_HOSTS and every probe
# comes back as an HTML 400 instead of the response under test.
settings.ALLOWED_HOSTS = ['*']

# A real SMTP handshake cannot run here; swap in the in-memory backend so the
# "sent" branches are the ones under test.
settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

User = get_user_model()

from ict_requisition.models import ICTRequisition            # noqa: E402
from internal_requisition.models import InternalRequisition  # noqa: E402
from transport_requisition.models import TransportRequisition  # noqa: E402
from notifications.models import AuditLog, EmailLog          # noqa: E402
from notifications.utils import sign_action_token            # noqa: E402

# Row markers this script owns; cleanup keys off them and nothing else.
MARK = 'T3-'
USER_MARK = 'tier3_'

MAIN_DOCUMENTATION_SENTENCE = (
    'PDF generation requires weasyprint which is not installed. '
    'On Windows, install it via WSL2 or use the HTML download option.'
)
INACTIVE_SENTENCE = 'Your account is pending admin approval. Please try again later.'
WRONG_USER_SENTENCE = (
    'This approval link was sent to a different user. '
    'Sign in as that user, or open the requisition from your dashboard.'
)
NO_REASON_SENTENCE = 'Please give a reason so the requester knows what to fix.'

results = []


def section(title):
    print('\n' + title)


def check(name, passed, detail=''):
    results.append((name, bool(passed)))
    print(('  PASS  ' if passed else '  FAIL  ') + name
          + ('  ' + str(detail) if detail else ''))


def _purge_queue():
    """Empty django_q_ormq so no probe leaves a queued approval email behind."""
    from django_q.brokers import get_broker
    broker = get_broker()
    for name in ('purge_queue', 'purge', 'delete_queue'):
        method = getattr(broker, name, None)
        if callable(method):
            return method()
    return None


def _json(response):
    try:
        return response.json()
    except Exception:
        return {}


# ---------------------------------------------------------------- pre-clean
TransportRequisition.objects.filter(request_number__startswith=MARK).delete()
ICTRequisition.objects.filter(request_number__startswith=MARK).delete()
InternalRequisition.objects.filter(request_number__startswith=MARK).delete()
User.objects.filter(username__startswith=USER_MARK).delete()
try:
    _purge_queue()
except Exception as _exc:  # pragma: no cover - broker cleanup is best-effort
    print('  (queue purge skipped:', _exc, ')')

supervisor = User.objects.filter(is_superuser=True).first()
admin = User.objects.get(username='admin')

# A plain signed-in user: the "different user" branch and the reminder 403.
requester = User.objects.create_user(
    username=USER_MARK + 'requester', password='pass-12345',
    role=User.Role.REQUESTER)
# An approver whose role does not own the stage the link points at: the
# `engine.stage_allows` branch.
grants_user = User.objects.create_user(
    username=USER_MARK + 'grants', password='pass-12345',
    role=User.Role.GRANTS)

# ------------------------------------------------------------------ fixtures
def _transport(marker, status='pending_first'):
    return TransportRequisition.objects.create(
        request_number=marker, status=status,
        full_name='Tier three smoke', email_address='t3@example.com',
        mobile_number='0700000000', designation='Officer',
        pin='0000', num_passengers=1,
        pick_up_date='2030-01-10', pick_up_time='09:00',
        pick_up_location='Niketon', destination='Gulshan',
        drop_off_date='2030-01-10', drop_off_time='17:00',
        drop_off_location='Niketon', travelling_reason='Tier three proof',
        project_name_code='BUIED', budget_code='100')


tr_approve = _transport(MARK + 'TR')       # the happy-path approval
tr_authz = _transport(MARK + 'AUTHZ')      # wrong-user / not-authorised
tr_done = _transport(MARK + 'DONE', status='approved')  # terminal stage

ict_row = ICTRequisition.objects.create(
    request_number=MARK + 'ICT', status='pending_first',
    full_name='Tier three smoke', email_address='t3@example.com',
    designation='Officer', pin_number='0000', contact_number='0700000000',
    device_equipment='Tier three laptop', purpose='Tier three proof',
    requisition_date='2030-01-05', requirement_date='2030-01-20',
    supervisor=supervisor)

int_row = InternalRequisition.objects.create(
    request_number=MARK + 'INT', status='pending_first',
    full_name='Tier three smoke', email_address='t3@example.com',
    mobile_number='0700000000', designation='Officer',
    pin='0000', department='Tier three department')

FIXTURE_PKS = {
    'transport': [tr_approve.pk, tr_authz.pk, tr_done.pk],
    'ict': [ict_row.pk],
    'internal': [int_row.pk],
}

c = Client()
c.force_login(admin)
anon = Client()
as_requester = Client()
as_requester.force_login(requester)
as_grants = Client()
as_grants.force_login(grants_user)

any_pk = tr_approve.pk  # reused wherever a pk is only needed for routing


def action_url(token):
    return f'/api/notifications/action/{token}/'


# =============================================================================
section('A. documentation')
# =============================================================================
r = c.get('/api/documentation/')
body = _json(r)
html = body.get('html', '')
check('GET /api/documentation/ -> 200', r.status_code == 200, r.status_code)
check('page carries its own <h1>',
      '📖 BRAC IED Central Portal — System Documentation' in html)
check('all ten numbered sections are present',
      all(f'<h2 id="{anchor}">' in html for anchor in
          ('overview', 'tech', 'modules', 'roles', 'workflow', 'hr',
           'notifications', 'audit', 'deployment', 'urls')))
check('URL reference table kept', '/accounts/signup/' in html
      and '/notifications/track/' in html)
check("main's own download button markup preserved", '?download=1' in html)

r = c.get('/api/documentation/?download=html')
check('?download=html -> 200 attachment',
      r.status_code == 200, r.status_code)
check('html download filename matches main',
      r.get('Content-Disposition')
      == 'attachment; filename="Requisition_Portal_Documentation.html"',
      r.get('Content-Disposition'))
check('html download body is the rendered page',
      b'1. System Overview' in r.content)

r = c.get('/api/documentation/?download=pdf')
check('?download=pdf -> 501 on this host', r.status_code == 501, r.status_code)
check('pdf 501 keeps main\'s exact sentence',
      _json(r).get('detail') == MAIN_DOCUMENTATION_SENTENCE,
      _json(r).get('detail'))
check('pdf 501 is coded pdf_unavailable',
      _json(r).get('code') == 'pdf_unavailable', _json(r).get('code'))

# =============================================================================
section('B. signup + the pending-approval login')
# =============================================================================
SIGNUP = '/api/auth/signup/'
NEW = USER_MARK + 'new'
PW = 'Sup3rSecret!'

r = c.post(SIGNUP, {'username': NEW, 'password1': PW, 'password2': 'different'})
check('mismatched passwords -> 400', r.status_code == 400, r.status_code)
check("main's sentence: Passwords do not match",
      _json(r).get('error') == 'Passwords do not match', _json(r).get('error'))
check('no account written on mismatch',
      not User.objects.filter(username=NEW).exists())

r = c.post(SIGNUP, {'username': 'admin', 'password1': PW, 'password2': PW})
check('duplicate username -> 400', r.status_code == 400, r.status_code)
check("main's sentence: Username already exists",
      _json(r).get('error') == 'Username already exists', _json(r).get('error'))

r = c.post(SIGNUP, {'username': '', 'password1': PW, 'password2': PW})
check('empty username guarded (main 500s here)',
      r.status_code == 400 and _json(r).get('error') == 'Username is required.',
      _json(r))

r = c.post(SIGNUP, {'username': NEW, 'password1': PW, 'password2': PW,
                    'email': 't3@example.com', 'phone': '0700000000',
                    'role': 'requester'})
check('happy path -> 200', r.status_code == 200, r.status_code)
created = User.objects.filter(username=NEW).first()
check('account exists', created is not None)
check('account is created DISABLED (pending admin approval)',
      created is not None and created.is_active is False)
check('default role is requester',
      created is not None and created.role == 'requester')
check('password stored correctly',
      created is not None and created.check_password(PW))
check('profile fields stored',
      created is not None and created.email == 't3@example.com'
      and created.phone == '0700000000')

fresh = Client()
r = fresh.post('/api/auth/login/', {'username': NEW, 'password': PW})
check('signing in while inactive -> 400', r.status_code == 400, r.status_code)
check('inactive login carries main\'s sentence',
      _json(r).get('inactive', [None])[0] == INACTIVE_SENTENCE,
      _json(r).get('inactive'))

r = c.post('/api/auth/login/', {'username': 'admin', 'password': 'wrong'})
check('wrong password on an active account unchanged (401)',
      r.status_code == 401, r.status_code)

if created is not None:
    created.is_active = True
    created.save()
r = fresh.post('/api/auth/login/', {'username': NEW, 'password': PW})
check('once approved the account signs in', r.status_code == 200, r.status_code)
check('login response carries a JWT', bool(_json(r).get('access')))
check('login response carries the user', _json(r).get('user', {}).get('username') == NEW)

# =============================================================================
section('C. /notifications/action/<token>/ -- the signed email deep links')
# =============================================================================
# --- resolve only, nothing applied -----------------------------------------
tok_approve = sign_action_token('transport', tr_approve.pk, 'approve', admin.pk)
r = anon.get(action_url(tok_approve))
check('signed out -> login_required', r.status_code == 200
      and _json(r).get('kind') == 'login_required', _json(r))
check('login_required points back at the same link',
      _json(r).get('next') == f'/notifications/action/{tok_approve}',
      _json(r).get('next'))
check('resolve does NOT apply the approval',
      TransportRequisition.objects.get(pk=tr_approve.pk).status == 'pending_first')

r = anon.get(action_url('transport:1:approve:1:1xENAc:NotARealSignature'))
check('bad signature -> Invalid or expired link.',
      _json(r).get('error') == 'Invalid or expired link.', _json(r))

tok_bogus_type = sign_action_token('spaceship', any_pk, 'approve', admin.pk)
r = anon.get(action_url(tok_bogus_type))
check('unknown requisition type -> Invalid requisition type.',
      r.status_code == 200 and _json(r).get('error') == 'Invalid requisition type.',
      _json(r))

tok_missing_row = sign_action_token('transport', 999999, 'approve', admin.pk)
r = anon.get(action_url(tok_missing_row))
check('missing requisition -> 404 (main uses get_object_or_404)',
      r.status_code == 404, r.status_code)

tok_missing_user = sign_action_token('transport', any_pk, 'approve', 999999)
r = anon.get(action_url(tok_missing_user))
check('missing token owner -> 404', r.status_code == 404, r.status_code)

tok_action = sign_action_token('transport', any_pk, 'sideways', admin.pk)
check('action that is neither approve nor reject -> Invalid action.',
      _json(c.get(action_url(tok_action))).get('error') == 'Invalid action.')

# The token names who it was issued to, so the same link read by anyone else
# has to say so -- signed in here as a different, valid account.
tok_authz = sign_action_token('transport', tr_authz.pk, 'approve', admin.pk)
r = as_requester.get(action_url(tok_authz))
check('link opened by the wrong account -> main\'s sentence',
      _json(r).get('kind') == 'error'
      and _json(r).get('error') == WRONG_USER_SENTENCE, _json(r))

tok_authz2 = sign_action_token('transport', tr_authz.pk, 'approve', grants_user.pk)
r = as_grants.get(action_url(tok_authz2))
check('approver who does not own the stage ->',
      _json(r).get('error') == 'You are not authorised to act at "Supervisor Approval".',
      _json(r))

tok_terminal = sign_action_token('transport', tr_done.pk, 'approve', admin.pk)
check('terminal stage -> no longer awaiting approval',
      _json(c.get(action_url(tok_terminal))).get('error')
      == 'This requisition is no longer awaiting approval.')

# --- approve ----------------------------------------------------------------
r = c.get(action_url(tok_approve))
payload = _json(r)
check('resolve -> approve-ready', payload.get('kind') == 'approve-ready', payload)
check('approve message matches main byte for byte',
      payload.get('message')
      == f'Requisition #{tr_approve.pk} approved at "Supervisor Approval".',
      payload.get('message'))
check('resolve still applies nothing',
      TransportRequisition.objects.get(pk=tr_approve.pk).status == 'pending_first')

r = c.post(action_url(tok_approve))
row = TransportRequisition.objects.get(pk=tr_approve.pk)
check('POST approve -> 200 success', r.status_code == 200
      and _json(r).get('kind') == 'success', _json(r))
check('POST approve returns the same sentence',
      _json(r).get('message') == payload.get('message'), _json(r))
check('requisition advanced to the configured next stage',
      row.status == 'pending_grants', row.status)
check('audit entry written for the approval',
      AuditLog.objects.filter(req_id=tr_approve.pk,
                              req_type='transport').exists())

# --- reject -----------------------------------------------------------------
tok_reject = sign_action_token('ict', ict_row.pk, 'reject', admin.pk)
r = c.get(action_url(tok_reject))
payload = _json(r)
check('reject link -> reject-form', payload.get('kind') == 'reject-form', payload)
check('reject form carries the request number',
      payload.get('requisition', {}).get('request_number') == MARK + 'ICT',
      payload)
check('reject form carries the stage name',
      payload.get('stage', {}).get('name') == 'First Approval', payload)
check('reject message matches main byte for byte',
      payload.get('message')
      == f'Requisition #{ict_row.pk} rejected at "First Approval".',
      payload.get('message'))
check('this stage demands a reason',
      payload.get('require_reason') is True, payload)

r = c.post(action_url(tok_reject), {'reason': ''})
check('empty reason -> 400', r.status_code == 400, r.status_code)
check("main's sentence: please give a reason",
      _json(r).get('detail') == NO_REASON_SENTENCE, _json(r))
check('nothing was written by the refused reject',
      ICTRequisition.objects.get(pk=ict_row.pk).status == 'pending_first')

r = c.post(action_url(tok_reject), {'reason': 'Tier three says no'})
row = ICTRequisition.objects.get(pk=ict_row.pk)
check('POST reject -> 200 success', r.status_code == 200
      and _json(r).get('kind') == 'success', _json(r))
check('status is rejected', row.status == 'rejected', row.status)
check('reason stored', row.rejection_reason == 'Tier three says no',
      row.rejection_reason)
check('rejected_at stamped', row.rejected_at is not None)
check('reject audit entry written',
      AuditLog.objects.filter(req_id=ict_row.pk, action='rejected').exists())
check('the same link now reports it is no longer pending',
      _json(c.get(action_url(tok_reject))).get('error')
      == 'This requisition is no longer awaiting approval.')

# =============================================================================
section('D. /notifications/track/<type>/<id>/ -- the email "Track" button')
# =============================================================================
for req_type, row_obj, label in (
        ('transport', tr_approve, 'Transport'),
        ('ict', ict_row, 'ICT'),
        ('internal', int_row, 'Internal')):
    r = c.get(f'/api/notifications/track/{req_type}/{row_obj.pk}/')
    body = _json(r)
    fields = set((body.get('r') or {}).keys())
    check(f'{label}: 200 with a label', r.status_code == 200
          and body.get('label') == label, body)
    check(f'{label}: request_number echoed',
          (body.get('r') or {}).get('request_number') == row_obj.request_number)
    check(f'{label}: track.html\'s eight fields all present',
          fields == {'request_number', 'full_name', 'status', 'created_at',
                     'first_approved_at', 'second_approved_at', 'rejected_at',
                     'rejection_reason'}, sorted(fields))

r = c.get('/api/notifications/track/spaceman/1/')
check('unknown type -> Invalid requisition type.',
      r.status_code == 400 and _json(r).get('error') == 'Invalid requisition type.',
      _json(r))
r = c.get('/api/notifications/track/transport/999999/')
check('missing row -> 404', r.status_code == 404, _json(r))

# =============================================================================
section('E. /notifications/send-reminder/<type>/<id>/')
# =============================================================================
REMINDER = 'notifications/send-reminder'

r = as_requester.post(f'/api/{REMINDER}/transport/{tr_authz.pk}/')
check('non-admin is refused', r.status_code == 403, r.status_code)
check('refusal uses DRF\'s own wording',
      _json(r).get('detail')
      == 'You do not have permission to perform this action.', _json(r))

r = c.post(f'/api/{REMINDER}/spaceman/1/')
check('unknown type -> Invalid requisition type.',
      r.status_code == 400 and _json(r).get('detail') == 'Invalid requisition type.',
      _json(r))

r = c.post(f'/api/{REMINDER}/transport/999999/')
check('missing row -> 404', r.status_code == 404, _json(r))

r = c.post(f'/api/{REMINDER}/internal/{int_row.pk}/')
check('pending row -> reminder sent', r.status_code == 200, r.status_code)
check("main's success sentence",
      _json(r).get('detail')
      == f'Approval request sent to First Approval for #{int_row.pk}.',
      _json(r))
check('reported at success level', _json(r).get('level') == 'success', _json(r))

r = c.get(f'/api/{REMINDER}/transport/{tr_done.pk}/')
check('GET works too (main exposes it as a plain link)',
      r.status_code == 200, r.status_code)
check('terminal row -> main\'s info sentence',
      _json(r).get('detail')
      == f'Requisition #{tr_done.pk} is not pending approval.', _json(r))
check('reported at info level', _json(r).get('level') == 'info', _json(r))

# =============================================================================
section('F. cleanup -- nothing this run created is left behind')
# =============================================================================
pks_before = {k: list(v) for k, v in FIXTURE_PKS.items()}
AuditLog.objects.filter(
    req_id__in=pks_before['transport'], req_type='transport').delete()
AuditLog.objects.filter(req_id__in=pks_before['ict'], req_type='ict').delete()
AuditLog.objects.filter(req_id__in=pks_before['internal'],
                        req_type='internal').delete()
EmailLog.objects.filter(req_id__in=pks_before['transport'],
                        req_type='transport').delete()
EmailLog.objects.filter(req_id__in=pks_before['ict'], req_type='ict').delete()
EmailLog.objects.filter(req_id__in=pks_before['internal'],
                        req_type='internal').delete()

TransportRequisition.objects.filter(request_number__startswith=MARK).delete()
ICTRequisition.objects.filter(request_number__startswith=MARK).delete()
InternalRequisition.objects.filter(request_number__startswith=MARK).delete()
User.objects.filter(username__startswith=USER_MARK).delete()
try:
    _purge_queue()
except Exception as _exc:  # pragma: no cover
    print('  (queue purge skipped:', _exc, ')')

check('no requisition rows left',
      not TransportRequisition.objects.filter(request_number__startswith=MARK).exists()
      and not ICTRequisition.objects.filter(request_number__startswith=MARK).exists()
      and not InternalRequisition.objects.filter(request_number__startswith=MARK).exists())
check('no accounts left', not User.objects.filter(username__startswith=USER_MARK).exists())
check('no audit rows left',
      not AuditLog.objects.filter(req_id__in=pks_before['transport']).exists())
try:
    from django.db import connection as _conn
    with _conn.cursor() as _cur:
        _cur.execute('SELECT COUNT(*) FROM django_q_ormq')
        _qlen = _cur.fetchone()[0]
except Exception as _exc:  # pragma: no cover
    _qlen = f'unreadable: {_exc}'
check('django_q queue emptied', _qlen == 0, _qlen)

# =============================================================================
passed = sum(1 for _, ok in results if ok)
failed = len(results) - passed
print(f'\nPASSED: {passed} / FAILED: {failed} / TOTAL: {len(results)}')
sys.exit(1 if failed else 0)
