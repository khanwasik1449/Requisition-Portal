"""Background tasks for django-q — email sending moved off the request thread.

All email sending goes through these tasks so the HTTP response returns
immediately and SMTP latency/failures don't block the user.
"""

from django_q.tasks import async_task


def send_email_task(department, subject, message, to_emails, html=False,
                    email_type='notification', req_type='', req_id=None):
    """Actual SMTP send — runs in a worker process.

    Mirrors the old send_department_email but without any HTTP context.
    """
    from .models import EmailLog, EmailConfig
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    to_list = to_emails if isinstance(to_emails, list) else [to_emails]
    primary = to_list[0] if to_list else ''

    try:
        config = EmailConfig.objects.get(department=department, is_active=True)
    except EmailConfig.DoesNotExist:
        EmailLog.objects.create(
            department=department, email_type=email_type,
            req_type=req_type, req_id=req_id,
            recipient=primary, subject=subject,
            status=EmailLog.Status.FAILED,
            error_message='No active email config found.',
        )
        return

    msg = MIMEMultipart('alternative')
    msg['From'] = config.from_email
    msg['To'] = ', '.join(to_list)
    msg['Subject'] = subject

    if html:
        msg.attach(MIMEText(message, 'html', 'utf-8'))
    else:
        msg.attach(MIMEText(message, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP(config.email_host, config.email_port)
        if config.email_use_tls:
            server.starttls()
        server.login(config.email_host_user, config.email_host_password)
        server.sendmail(config.from_email, to_list, msg.as_string())
        server.quit()
        EmailLog.objects.create(
            department=department, email_type=email_type,
            req_type=req_type, req_id=req_id,
            recipient=primary, subject=subject,
            status=EmailLog.Status.SUCCESS,
        )
    except Exception as e:
        EmailLog.objects.create(
            department=department, email_type=email_type,
            req_type=req_type, req_id=req_id,
            recipient=primary, subject=subject,
            status=EmailLog.Status.FAILED,
            error_message=str(e),
        )


def queue_approval_emails(req_type, requisition_pk, status):
    """Queue approval-request emails for all approvers at this stage."""
    from .utils import _approvers_for_stage, _build_approval_email, BASE_URL
    from accounts.models import User

    approvers = _approvers_for_stage(req_type, status)
    if not approvers:
        return

    if req_type == 'ict':
        dept, label = 'ict', 'ICT'
    elif req_type == 'transport':
        dept, label = 'transport', 'Transport'
    elif req_type == 'meetspace':
        dept, label = 'hr', 'MeetSpace'
    else:
        dept, label = 'internal', 'Internal'

    for approver in approvers:
        token = async_task('notifications.utils.sign_action_token', req_type, requisition_pk, 'approve', approver.pk)
        # Note: we can't get the token value here because it's async.
        # Instead, each worker will re-sign the token when it runs.
        # The worker will call queue_approval_email_for_approver with the approver PK.
        pass

    # Delegate to per-approver tasks
    for approver in approvers:
        async_task(
            'notifications.tasks.queue_approval_email_for_approver',
            req_type, requisition_pk, status, approver.pk, dept, label,
            hook='notifications.tasks.on_email_failure'
        )


def queue_approval_email_for_approver(req_type, requisition_pk, status, approver_pk, dept, label):
    """Worker task: build and send a single approval email for one approver."""
    from .utils import _build_approval_email, BASE_URL, sign_action_token
    from accounts.models import User
    from .models import EmailConfig

    try:
        approver = User.objects.get(pk=approver_pk)
    except User.DoesNotExist:
        return

    if req_type == 'meetspace':
        from meetspace.models import Booking
        requisition = Booking.objects.get(pk=requisition_pk)
    elif req_type == 'transport':
        from transport_requisition.models import TransportRequisition
        requisition = TransportRequisition.objects.get(pk=requisition_pk)
    elif req_type == 'ict':
        from ict_requisition.models import ICTRequisition
        requisition = ICTRequisition.objects.get(pk=requisition_pk)
    else:
        from internal_requisition.models import InternalRequisition
        requisition = InternalRequisition.objects.get(pk=requisition_pk)

    token = sign_action_token(req_type, requisition_pk, 'approve', approver_pk)
    reject_token = sign_action_token(req_type, requisition_pk, 'reject', approver_pk)
    approve_link = f'{BASE_URL}/notifications/action/{token}/'
    reject_link = f'{BASE_URL}/notifications/action/{reject_token}/'

    subject = f'{label} Requisition {requisition.request_number} — Action Required'
    html = _build_approval_email(approver.username, label, requisition, status, approve_link, reject_link)

    async_task(
        'notifications.tasks.send_email_task',
        dept, subject, html, [approver.email] if approver.email else [],
        True, 'approval_request', req_type, requisition_pk
    )


def queue_notification_email(req_type, requisition_pk, status, email_type, subject, html, recipients):
    """Queue a notification email (created/rejected/assigned/etc.) for the requester."""
    dept = {'transport': 'transport', 'ict': 'ict', 'internal': 'internal', 'meetspace': 'hr'}.get(req_type, 'internal')
    for email in recipients:
        async_task(
            'notifications.tasks.send_email_task',
            dept, subject, html, [email], True, email_type, req_type, requisition_pk
        )


def on_email_failure(task):
    """Hook called when an email task fails — logs are already written in send_email_task."""
    pass