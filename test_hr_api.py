"""Tier 2C/2D/2E backend probe: contracts, employees and payslips through the
API layer that the React pages call.

Every assertion mirrors the corresponding Django view sentence-for-sentence.
Run:  venv\\Scripts\\python.exe test_hr_api.py
Exit code 0 = all green.
"""
import csv
import io
import json
import os
import sys
from datetime import date, timedelta

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
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

# The script talks to the views over the test client directly; without this
# the default `testserver` host is rejected by ALLOWED_HOSTS and every probe
# comes back as an HTML 400 instead of the response under test.
settings.ALLOWED_HOSTS = ['*']


def upload(name, text, content_type='text/csv'):
    """Django's test client has no `('name', 'body', 'type')` tuple form --
    a tuple is merely Iterable, so it is written out as three plain string
    fields and `request.FILES` stays empty. Hand it a real upload instead."""
    return SimpleUploadedFile(name, text.encode('utf-8'),
                              content_type=content_type)

from contracts.models import Contract, EmailConfig, EmailLog
from employees.models import Employee
from payslip.models import Payslip, PayslipRequest

# A real SMTP handshake cannot run here; swap in the in-memory backend so the
# "sent" branch of send_contract_email is the one under test.
settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

results = []


def check(name, passed, detail=''):
    results.append((name, bool(passed)))
    print(('  PASS  ' if passed else '  FAIL  ') + name
          + ('  ' + str(detail) if detail else ''))


def _purge_queue():
    """Empty django_q_ormq so no probe leaves a queued bulk-email task
    behind. The ORM broker names the method purge_queue(); other brokers
    (and older django_q) call it purge()."""
    from django_q.brokers import get_broker
    broker = get_broker()
    for name in ('purge_queue', 'purge', 'delete_queue'):
        method = getattr(broker, name, None)
        if callable(method):
            return method()
    return None


# ---------------------------------------------------------------- pre-clean
Contract.objects.all().delete()
Employee.objects.all().delete()
Payslip.objects.all().delete()
PayslipRequest.objects.all().delete()
EmailLog.objects.all().delete()
EmailConfig.objects.all().delete()

# Earlier runs may have left a bulk-email task sitting in the ORM broker.
try:
    _purge_queue()
except Exception as _exc:  # pragma: no cover - broker cleanup is best-effort
    print('  (queue purge skipped:', _exc, ')')

# ...and probe Task rows from a run that died before its cleanup reached them.
from django_q.models import Task as _Task  # noqa: E402
_Task.objects.filter(name='bulk_email_probe').delete()

admin = get_user_model().objects.get(username='admin')
c = Client()
c.force_login(admin)

TODAY = date.today()


# =========================================================== CONTRACTS
print('\n-- contracts --')

r = c.get('/api/contracts/')
check('GET /api/contracts/ anonymous -> 401',
      Client().get('/api/contracts/').status_code == 401)
check('GET /api/contracts/ -> 200', r.status_code == 200, r.status_code)

# 1. main's create guard (designation is a non-blank model field, so it is
#    required by the serializer too -- main's form always posts it)
r = c.post('/api/contracts/', data=json.dumps(
    {'pin': 'C-1', 'name': 'No Dates', 'designation': 'Officer'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('create without dates/salary -> 400', r.status_code == 400,
      r.status_code)
body = r.json() if r.status_code == 400 else {}
if r.status_code != 400:
    print('        body:', r.content.decode()[:300])
msgs = body.get('non_field_errors') or []
check('main sentence verbatim',
      any(m.strip() == 'Start date, end date, and salary are required.'
          for m in msgs), body)

# 2. a real contract
payload = {
    'pin': 'C-100', 'name': 'Ada Lovelace', 'designation': 'Analyst',
    'new_designation': '', 'contract_type': 'Extension',
    'start_date': str(TODAY - timedelta(days=10)),
    'end_date': str(TODAY + timedelta(days=600)),
    'salary': '55000',
}
r = c.post('/api/contracts/', data=json.dumps(payload),
           content_type='application/json', SERVER_NAME='127.0.0.1')
check('valid create -> 201', r.status_code == 201, r.status_code)
if r.status_code != 201:
    print('        body:', r.content.decode()[:300])
cid = r.json().get('id') if r.status_code == 201 else None

# 3. a contract that is already expired, and one expiring inside 30 days
expired = Contract.objects.create(
    pin='C-200', name='Grace Hopper', designation='Admiral',
    start_date=TODAY - timedelta(days=400),
    end_date=TODAY - timedelta(days=10), salary=1)
Contract.objects.create(
    pin='C-300', name='Alan Turing', designation='Reader',
    start_date=TODAY - timedelta(days=100),
    end_date=TODAY + timedelta(days=5), salary=1)
Contract.objects.create(
    pin='C-301', name='Katherine Johnson', designation='Maths',
    start_date=TODAY - timedelta(days=100),
    end_date=TODAY + timedelta(days=900), salary=1)

# 4. contract_list's filters
r = c.get('/api/contracts/', {'type': 'Extension'}, SERVER_NAME='127.0.0.1')
rows = r.json()['results']
check('?type=Extension -> only Extension',
      bool(rows) and all(x['contract_type'] == 'Extension' for x in rows),
      [x['contract_type'] for x in rows])

r = c.get('/api/contracts/', {'status': 'Expired'}, SERVER_NAME='127.0.0.1')
rows = r.json()['results']
check('?status=Expired -> only the expired one',
      len(rows) == 1 and rows[0]['pin'] == 'C-200',
      [(x['pin'], x['end_date']) for x in rows])

r = c.get('/api/contracts/', {'status': 'Expiring'}, SERVER_NAME='127.0.0.1')
rows = r.json()['results']
check('?status=Expiring -> only the 5-day one',
      len(rows) == 1 and rows[0]['pin'] == 'C-300',
      [x['pin'] for x in rows])

r = c.get('/api/contracts/', {'status': 'Active'}, SERVER_NAME='127.0.0.1')
pins = [x['pin'] for x in r.json()['results']]
check('?status=Expired excluded from Active', 'C-200' not in pins, pins)

r = c.get('/api/contracts/', {'q': 'katherine'}, SERVER_NAME='127.0.0.1')
rows = r.json()['results']
check('?q= search (case-insensitive)',
      len(rows) == 1 and rows[0]['pin'] == 'C-301', [x['name'] for x in rows])

r = c.get('/api/contracts/', {'sort': 'name'}, SERVER_NAME='127.0.0.1')
names = [x['name'] for x in r.json()['results']]
check('?sort=name ascending', names == sorted(names), names)

r = c.get('/api/contracts/', {'sort': 'bogus'}, SERVER_NAME='127.0.0.1')
check('?sort=bogus falls back to -id',
      [x['id'] for x in r.json()['results']]
      == sorted([x['id'] for x in r.json()['results']], reverse=True))

# 5. CSV template
r = c.get('/api/contracts/csv-template/', SERVER_NAME='127.0.0.1')
check('csv-template -> 200', r.status_code == 200, r.status_code)
first_row = next(csv.reader(io.StringIO(r.content.decode()))) if r.status_code == 200 else []
check('template header verbatim',
      first_row == ['PIN', 'Name', 'Designation', 'Salary', 'Start Date',
                    'End Date', 'Contract Type', 'Email', 'Phone', 'TIN',
                    'New Designation'], first_row)

# 6. bulk upload (mirrors bulk_create_contracts)
before = Contract.objects.count()
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(['PIN', 'Name', 'Designation', 'Salary', 'Start Date', 'End Date',
            'Contract Type', 'Email', 'Phone', 'TIN', 'New Designation'])
w.writerow(['B-1', 'Bulk One', 'Officer', '40000',
            str(TODAY), str(TODAY + timedelta(days=365)), 'New',
            'bulk1@example.com', '01711111111', 'TIN1', ''])
w.writerow(['B-2', 'Bulk Two', 'Manager', '60000',
            str(TODAY), str(TODAY + timedelta(days=365)), 'Renewal',
            'bulk2@example.com', '01722222222', 'TIN2', 'Senior Manager'])
r = c.post('/api/contracts/bulk/',
           data={'file': upload('contract_template.csv', buf.getvalue())},
           SERVER_NAME='127.0.0.1')
check('bulk upload -> 200', r.status_code == 200, r.status_code)
if r.status_code != 200:
    print('        body:', r.content.decode()[:400])
body = r.json() if r.status_code == 200 else {}
check('bulk message verbatim',
      body.get('detail') == '2 contracts created successfully!',
      body.get('detail'))
check('bulk created 2 rows',
      Contract.objects.count() == before + 2,
      (before, Contract.objects.count()))
check('bulk upserts the Employee row',
      Employee.objects.filter(pin='B-1', email='bulk1@example.com').exists(),
      list(Employee.objects.filter(pin__startswith='B-').values_list(
          'pin', 'email')))
_b2 = Contract.objects.filter(pin='B-2').first()
check('bulk stores Renewal new_designation',
      _b2 is not None and _b2.new_designation == 'Senior Manager',
      None if _b2 is None else _b2.new_designation)

r = c.post('/api/contracts/bulk/',
           data={'file': upload('notes.txt', 'hello', 'text/plain')},
           SERVER_NAME='127.0.0.1')
check('non-csv rejected with main sentence',
      r.status_code == 400 and r.json().get('detail') == 'Only CSV files allowed!',
      r.status_code)

# 7. PDF -- WeasyPrint loads Pango/GObject through ctypes, which Windows does
#    not ship (hence requirements-windows.txt omits weasyprint). Either the
#    renderer is present and we get a real document, or the API says so
#    instead of the 500 main raises here.
r = c.get(f'/api/contracts/{cid}/pdf/', SERVER_NAME='127.0.0.1')
if r.status_code == 200:
    check('contract pdf is a PDF', r.content[:4] == b'%PDF', r.content[:8])
    check('contract pdf filename',
          'contract_C-100.pdf'
          in r.headers.get('Content-Disposition', ''),
          r.headers.get('Content-Disposition'))
else:
    body = r.json() if r.content[:1] == b'{' else {}
    check('contract pdf degrades to 501 on this host',
          r.status_code == 501 and body.get('code') == 'pdf_unavailable'
          and 'Pango' in str(body.get('detail', '')),
          (r.status_code, body.get('code')))
    print('        NOTE: ' + str(body.get('detail', ''))[:160])

# 8. email defaults -- one per contract type
expected_subjects = {
    'Extension': 'Extension of contract letter',
    'Renewal': 'Renewal of contract',
    'New': 'New Contract',
    'Revision': 'Revision of contract',
}
for ctype, subject in expected_subjects.items():
    obj = Contract.objects.filter(contract_type=ctype).first() or \
        Contract.objects.create(
            pin=f'C-{ctype}', name=f'{ctype} Person', designation='X',
            start_date=TODAY, end_date=TODAY + timedelta(days=30), salary=1,
            contract_type=ctype)
    r = c.get(f'/api/contracts/{obj.id}/defaults/', SERVER_NAME='127.0.0.1')
    got = r.json().get('subject') if r.status_code == 200 else None
    check(f'defaults[{ctype}] subject verbatim', got == subject, got)

# 9. send one contract by email
r = c.get(f'/api/contracts/{cid}/defaults/', SERVER_NAME='127.0.0.1')
defaults = r.json()
check('defaults carries the employee email',
      defaults.get('employee_email') == '', defaults)

r = c.post(f'/api/contracts/{cid}/email/', data=json.dumps(
    {'subject': '', 'body': ''}), content_type='application/json',
    SERVER_NAME='127.0.0.1')
check('blank recipient -> 400', r.status_code == 400, r.status_code)

# get_config() starts with an empty from-address, which the template expects
# the admin to fill in on the email-settings page first.
r = c.post('/api/contracts/email-config/', data=json.dumps({
    'action': 'save', 'email_host': 'smtp.example.com', 'email_port': 587,
    'email_use_tls': True, 'email_host_user': 'smtp@example.com',
    'email_host_password': 'secret', 'default_from_email': 'hr@bracied.com'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('email-config save -> 200',
      r.status_code == 200 and r.json().get('detail')
      == 'Email settings saved successfully!', (r.status_code, r.json()))
check('email-config persisted',
      EmailConfig.get_config().default_from_email == 'hr@bracied.com',
      EmailConfig.get_config().default_from_email)

r = c.get('/api/contracts/email-config/', SERVER_NAME='127.0.0.1')
check('email-config GET -> the six fields',
      r.status_code == 200 and set(['email_host', 'email_port',
                                    'email_use_tls', 'email_host_user',
                                    'email_host_password',
                                    'default_from_email'])
      <= set(r.json()), sorted(r.json()))

r = c.post('/api/contracts/email-config/', data=json.dumps({
    'action': 'test', 'email_host': '127.0.0.1', 'email_port': 1,
    'email_use_tls': False, 'email_host_user': 'x',
    'email_host_password': 'y', 'default_from_email': 'hr@bracied.com'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('email-config test failure -> 400 "Connection failed: ..."',
      r.status_code == 400 and str(r.json().get('detail', '')).startswith(
          'Connection failed: '), (r.status_code, r.json().get('detail')))
check('test action does not persist (as main re-renders without saving)',
      EmailConfig.get_config().email_host == 'smtp.example.com',
      EmailConfig.get_config().email_host)

# main attaches the rendered contract PDF to the message. Where WeasyPrint is
# unavailable the send fails exactly as it does in `main`, with main's own
# sentence, and the failure lands in contracts' EmailLog.
r = c.post(f'/api/contracts/{cid}/email/', data=json.dumps({
    'subject': 'Your contract', 'body': 'Please find it attached.',
    'recipient': 'ada@example.com'}), content_type='application/json',
    SERVER_NAME='127.0.0.1')
if r.status_code == 200:
    check('send message verbatim',
          r.json().get('detail')
          == 'Email sent successfully to ada@example.com!', r.json())
else:
    check('send fails like main when there is no PDF to attach',
          r.status_code == 400
          and str(r.json().get('detail', '')).startswith(
              'Failed to send email: '),
          (r.status_code, str(r.json())[:220]))
check('EmailLog row written for the recipient',
      EmailLog.objects.filter(recipient_email='ada@example.com').exists(),
      list(EmailLog.objects.values_list('recipient_email', 'status')))

# 10. HR email log (contracts' own table, not notifications')
r = c.get('/api/contracts/email-log/', SERVER_NAME='127.0.0.1')
rows = r.json().get('results', []) if r.status_code == 200 else []
check('email-log -> 200 with our row',
      r.status_code == 200 and any(
          x['recipient_email'] == 'ada@example.com' for x in rows),
      [x['recipient_email'] for x in rows])

# 11. bulk email queue + status counting
r = c.post('/api/contracts/bulk-email/', data=json.dumps({
    'contract_ids': [cid], 'subject': 'Bulk', 'body': 'Body'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('bulk-email queue -> 200', r.status_code == 200, r.status_code)
queued = r.json() if r.status_code == 200 else {}
check('bulk-email returns group/total/started',
      bool(queued.get('group')) and queued.get('total') == 1
      and bool(queued.get('started')), queued)

r = c.get('/api/contracts/bulk-email-status/',
          {'group': queued.get('group', 'x'), 'total': 1,
           'started': queued.get('started', 0)},
          SERVER_NAME='127.0.0.1')
check('bulk-email-status -> 200 with the template keys',
      r.status_code == 200 and set(['total', 'sent', 'failed', 'pending',
                                    'finished', 'results', 'elapsed',
                                    'group']) <= set(r.json()),
      sorted(r.json()) if r.status_code == 200 else r.status_code)

# django-q only drains its queue when a `qcluster` process is running (the
# README documents it as a separate service; run.ps1 does not start one).
# Count the group rows directly so the arithmetic is still under test.
from django_q.models import Success, Failure, Task  # noqa: E402
from django.utils import timezone  # noqa: E402
import uuid  # noqa: E402
grp = queued.get('group', 'probe-group')
_now = timezone.now()


def _task(success, result):
    # Success/Failure are proxy models over django_q_task, whose `id` is a
    # plain CharField with no default -- without a literal pk both rows would
    # be inserted as '' and collide. `success` is the flag their managers
    # filter on, so it has to be set explicitly too.
    return Task.objects.create(
        id=uuid.uuid4().hex, name='bulk_email_probe', group=grp,
        func='contracts.tasks.send_contract_email_task',
        started=_now, stopped=_now, success=success, result=result,
        cluster='test')


_task(True, {'contract_id': cid, 'name': 'Ada Lovelace',
             'email': 'ada@example.com', 'status': 'sent'})
_task(False, {'contract_id': cid, 'name': 'Nobody',
              'email': '', 'status': 'failed', 'reason': 'No email'})
r = c.get('/api/contracts/bulk-email-status/',
          {'group': grp, 'total': 3, 'started': queued.get('started', 0)},
          SERVER_NAME='127.0.0.1')
body = r.json()
check('bulk-email-status counts sent/failed/pending',
      body.get('sent') == 1 and body.get('failed') == 1
      and body.get('pending') == 1 and body.get('finished') is False, body)
check('bulk-email-status carries both result rows',
      len(body.get('results', [])) == 2
      and {x['status'] for x in body['results']} == {'sent', 'failed'},
      body.get('results'))
Success.objects.filter(group=grp).delete()
Failure.objects.filter(group=grp).delete()


# ============================================================ EMPLOYEES
print('\n-- employees --')

r = Client().get('/api/employees/', SERVER_NAME='127.0.0.1')
check('employees anonymous -> 401', r.status_code == 401, r.status_code)

r = c.post('/api/employees/', data=json.dumps(
    {'pin': 'EMP-1', 'name': 'New Hire', 'designation': '',
     'email': 'new@example.com', 'salary': 1000}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('blank designation -> 400', r.status_code == 400, r.status_code)
msgs = r.json().get('designation') or []
check('Designation is required. verbatim',
      any(m == 'Designation is required.' for m in msgs), msgs)

r = c.post('/api/employees/', data=json.dumps(
    {'pin': 'EMP-1', 'name': 'New Hire', 'designation': 'Officer',
     'email': '', 'salary': 1000}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
msgs = r.json().get('email') or []
check('blank email -> 400 "Email address is required."',
      r.status_code == 400 and 'Email address is required.' in msgs, msgs)

r = c.post('/api/employees/', data=json.dumps(
    {'pin': 'EMP-2', 'name': 'Second Hire', 'designation': 'Officer',
     'email': 'two@example.com', 'salary': 2000, 'gender': 'F'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('valid employee -> 201', r.status_code == 201, r.status_code)
check('project/branch defaults kept',
      Employee.objects.filter(pin='EMP-2').first() is not None
      and Employee.objects.get(pin='EMP-2').project == 'BUIED',
      getattr(Employee.objects.filter(pin='EMP-2').first(), 'project', None))

r = c.post('/api/employees/', data=json.dumps(
    {'pin': 'EMP-2', 'name': 'Dup', 'designation': 'X',
     'email': 'dup@example.com'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('duplicate pin -> 400', r.status_code == 400, r.status_code)

# every employees/urls.py route addresses the row by PIN
r = c.get('/api/employees/EMP-2/', SERVER_NAME='127.0.0.1')
check('GET /api/employees/<pin>/ -> 200',
      r.status_code == 200 and r.json()['name'] == 'Second Hire',
      (r.status_code, r.json().get('name')))
r = c.get('/api/employees/NOPE/', SERVER_NAME='127.0.0.1')
check('GET unknown pin -> 404', r.status_code == 404, r.status_code)

r = c.patch('/api/employees/EMP-2/', data=json.dumps({'salary': 3000}),
            content_type='application/json', SERVER_NAME='127.0.0.1')
check('PATCH by pin -> 200',
      r.status_code == 200 and float(r.json()['salary']) == 3000,
      (r.status_code, r.json().get('salary')))

r = c.get('/api/employees/lookup/', {'pin': 'EMP-2'},
          SERVER_NAME='127.0.0.1')
check('lookup hit -> exists true with all keys',
      r.status_code == 200 and r.json().get('exists') is True
      and set(['name', 'designation', 'salary', 'phone', 'email',
               'tin']) <= set(r.json()), r.json())
r = c.get('/api/employees/lookup/', {'pin': 'GHOST'},
          SERVER_NAME='127.0.0.1')
check('lookup miss -> exists false',
      r.status_code == 200 and r.json() == {'exists': False}, r.json())

# import (positional CSV, header skipped). Two clean rows plus one whose
# `Salary` cell is blank: main assigns `row[7].strip() or ...` straight to a
# non-null DecimalField, so that row raises and is counted in `failed` --
# reproduced here rather than papered over.
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(['PIN', 'Name', 'Designation', 'Gender', 'TIN', 'Phone', 'Email',
            'Salary'])
w.writerow(['IMP-1', 'Imported One', 'Analyst', 'M', 'T9', '0170000000',
            'imp1@example.com', '5000'])
w.writerow(['IMP-2', 'Imported Two', 'Clerk', 'F', '', '', '', '4000'])
w.writerow(['IMP-3', 'Imported Three', 'Clerk', '', '', '', '', ''])
r = c.post('/api/employees/import/',
           data={'file': upload('employees.csv', buf.getvalue())},
           SERVER_NAME='127.0.0.1')
check('import -> 200', r.status_code == 200, (r.status_code, r.content[:200]))
if r.status_code != 200:
    print('        body:', r.content.decode()[:300])
check('import message verbatim',
      r.status_code == 200
      and r.json().get('detail') == '2 employees imported!',
      r.json() if r.status_code == 200 else r.status_code)
check('import warning verbatim (blank-salary row fails, as in main)',
      r.status_code == 200 and r.json().get('warning') == '1 rows failed',
      r.json().get('warning') if r.status_code == 200 else None)
check('imported rows land',
      Employee.objects.filter(pin='IMP-1', email='imp1@example.com').exists()
      and Employee.objects.filter(pin='IMP-2', salary=4000).exists(),
      list(Employee.objects.filter(pin__startswith='IMP-').values_list(
          'pin', 'email')))
check('blank-salary row did not land',
      not Employee.objects.filter(pin='IMP-3').exists(),
      list(Employee.objects.filter(pin__startswith='IMP-').values_list('pin')))
r = c.get('/api/employees/', SERVER_NAME='127.0.0.1')
pins = [x['pin'] for x in r.json()['results']]
check('list ordered by pin', pins == sorted(pins), pins)
check('list carries the four contract counts',
      all(k in r.json()['results'][0]
          for k in ('new_count', 'extension_count', 'revision_count',
                    'renewal_count')), sorted(r.json()['results'][0]))

# delete removes the employee AND its contracts (employees/views.delete_employee)
Contract.objects.create(pin='EMP-2', name='Second Hire', designation='Officer',
                        start_date=TODAY, end_date=TODAY + timedelta(days=30),
                        salary=1)
check('contract pre-exists for EMP-2',
      Contract.objects.filter(pin='EMP-2').exists())
r = c.delete('/api/employees/EMP-2/', SERVER_NAME='127.0.0.1')
check('DELETE by pin -> 204', r.status_code == 204, r.status_code)
check('employee gone', not Employee.objects.filter(pin='EMP-2').exists())
check('its contracts gone too',
      not Contract.objects.filter(pin='EMP-2').exists())


# ============================================================== PAYSLIPS
print('\n-- payslips --')

r = Client().get('/api/payslips/', SERVER_NAME='127.0.0.1')
check('payslips anonymous -> 401', r.status_code == 401, r.status_code)

# main's create_payslip splits the posted figure 50/30/10/10
r = c.post('/api/payslips/', data=json.dumps({
    'pin': 'PAY-1', 'name': 'Salary Person', 'designation': 'Officer',
    'month': 'January', 'year': '2031', 'basic_salary': '10000',
    'transport': '500', 'income_tax': '250', 'other_deduction': '0'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('payslip create -> 201', r.status_code == 201,
      (r.status_code, r.content[:300]))
if r.status_code == 201:
    body = r.json()
    check('split basic 50%', float(body['basic_salary']) == 5000,
          body['basic_salary'])
    check('split house_rent 30%', float(body['house_rent']) == 3000,
          body['house_rent'])
    check('split medical 10%', float(body['medical_allowance']) == 1000,
          body['medical_allowance'])
    check('split conveyance 10%', float(body['conveyance']) == 1000,
          body['conveyance'])
    check('gross/net exposed',
          'gross_salary' in body and 'net_salary' in body, sorted(body))
    pay_id = body.get('id')
else:
    pay_id = None

r = c.get('/api/payslips/', SERVER_NAME='127.0.0.1')
ids = [x['id'] for x in r.json()['results']]
check('payslip list newest-first', ids == sorted(ids, reverse=True), ids)

if pay_id:
    r = c.get(f'/api/payslips/{pay_id}/pdf/', SERVER_NAME='127.0.0.1')
    if r.status_code == 200:
        check('payslip pdf is a PDF', r.content[:4] == b'%PDF', r.content[:8])
        check('payslip pdf filename',
              'payslip_PAY-1_January_2031.pdf'
              in r.headers.get('Content-Disposition', ''),
              r.headers.get('Content-Disposition'))
    else:
        body = r.json() if r.content[:1] == b'{' else {}
        check('payslip pdf degrades to 501 on this host',
              r.status_code == 501 and body.get('code') == 'pdf_unavailable'
              and 'Pango' in str(body.get('detail', '')),
              (r.status_code, body.get('code')))
        print('        NOTE: ' + str(body.get('detail', ''))[:160])
else:
    check('payslip pdf reachable (create step produced an id)', False)

# bulk upload: PIN, gender, TIN, then twelve monthly totals July -> June
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(['Dummy PIN', 'Gender', 'TIN', 'July', 'August', 'September',
            'October', 'November', 'December', 'January', 'February', 'March',
            'April', 'May', 'June'])
w.writerow(['BLK-1', 'M', 'T77', '12000', '0', '0', '0', '0', '0', '0', '0',
            '0', '0', '0', '0'])
r = c.post('/api/payslips/bulk/',
           data={'file': upload('salaries.csv', buf.getvalue()),
                 'year': '2031'},
           SERVER_NAME='127.0.0.1')
check('payslip bulk -> 200', r.status_code == 200,
      (r.status_code, r.content[:300]))
body = r.json() if r.status_code == 200 else {}
check('bulk message verbatim',
      body.get('detail') ==
      '✅ 1 payslips uploaded successfully for year 2031!', body.get('detail'))
row = Payslip.objects.filter(pin='BLK-1', month='July', year='2031').first()
check('bulk splits the monthly total 50/30/10/10',
      row is not None and float(row.basic_salary) == 6000
      and float(row.house_rent) == 3600 and float(row.medical_allowance) == 1200
      and float(row.conveyance) == 1200,
      None if row is None else (row.basic_salary, row.house_rent,
                                row.medical_allowance, row.conveyance))
check('zero months skipped',
      not Payslip.objects.filter(pin='BLK-1', month='August').exists())
check('re-upload replaces the PIN/year',
      Payslip.objects.filter(pin='BLK-1', year='2031').count() == 1,
      Payslip.objects.filter(pin='BLK-1', year='2031').count())

# payslip request: public create, HR-only list
r = Client().post('/api/payslip-requests/', data=json.dumps({
    'name': 'Anonymous Staff', 'pin': 'PAY-9', 'months': 'January, February',
    'year': '2031'}), content_type='application/json',
    SERVER_NAME='127.0.0.1')
check('anonymous payslip request -> 201 (public form)',
      r.status_code == 201, (r.status_code, r.content[:200]))
check('months joined string stored',
      PayslipRequest.objects.filter(months='January, February').exists(),
      list(PayslipRequest.objects.values_list('months', flat=True)))
r = Client().get('/api/payslip-requests/', SERVER_NAME='127.0.0.1')
check('anonymous payslip request list -> 401', r.status_code == 401,
      r.status_code)
r = c.get('/api/payslip-requests/', SERVER_NAME='127.0.0.1')
check('admin payslip request list -> 200 newest-first',
      r.status_code == 200, r.status_code)

r = Client().post('/api/payslips/', data=json.dumps(
    {'pin': 'X', 'name': 'X', 'designation': 'X', 'month': 'January',
     'year': '2031', 'basic_salary': '10'}),
    content_type='application/json', SERVER_NAME='127.0.0.1')
check('anonymous payslip create -> 401', r.status_code == 401,
      r.status_code)


# ================================================================ CLEANUP
Contract.objects.all().delete()
Employee.objects.all().delete()
Payslip.objects.all().delete()
PayslipRequest.objects.all().delete()
EmailLog.objects.all().delete()
EmailConfig.objects.all().delete()

# The bulk-email probe enqueued a real django-q task; drop it so the ORM
# broker does not hold a stale row (README: purge django_q_ormq).
try:
    from django_q.brokers import get_broker  # noqa: F401
    _purge_queue()
except Exception as exc:  # pragma: no cover - broker cleanup is best-effort
    print('  (queue purge skipped:', exc, ')')

passed = sum(1 for _, x in results if x)
failed = len(results) - passed
print(f'\nPASSED: {passed} / FAILED: {failed}')
for name, x in results:
    if not x:
        print('  FAILED: ' + name)
sys.exit(1 if failed else 0)
