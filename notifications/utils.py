import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db.models import Q
from django.urls import reverse
from .models import EmailConfig

signer = TimestampSigner(salt='requisition-action')

# Where the portal is reachable from a browser. Action links are signed with
# SECRET_KEY, so they only work on an instance running the same key -- a link
# built for the dev server on :8000 is rejected by gunicorn behind nginx on
# :80, and vice versa. Override with DJANGO_BASE_URL in .env.
BASE_URL = os.environ.get('DJANGO_BASE_URL', 'http://10.10.11.201').rstrip('/')


def sign_action_token(requisition_type, requisition_id, action, user_id):
    value = f'{requisition_type}:{requisition_id}:{action}:{user_id}'
    return signer.sign(value)


def unsign_action_token(token, max_age=604800):
    try:
        value = signer.unsign(token, max_age=max_age)
        parts = value.split(':')
        if len(parts) != 4:
            return None
        return {
            'type': parts[0],
            'id': int(parts[1]),
            'action': parts[2],
            'user_id': int(parts[3]),
        }
    except (BadSignature, SignatureExpired, ValueError):
        return None


def _build_approval_email(recipient_name, label, requisition, status, approve_link, reject_link):
    status_label = 'first-level approval' if status == 'pending_first' else 'second-level approval'

    fields_html = ''
    if label == 'ICT':
        fields_html = f'''
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;width:140px;">Equipment</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;">{requisition.device_equipment.replace(chr(10), '<br>')}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Purpose</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.purpose}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Requester</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.full_name}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Email</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.email_address}</td></tr>
        <tr><td style="padding:8px 12px;color:#6b7280;">Designation</td><td style="padding:8px 12px;">{requisition.designation}</td></tr>
        '''
    elif label == 'Transport':
        fields_html = f'''
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;width:140px;">Destination</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;">{requisition.destination}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Pick-up</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.pick_up_location} on {requisition.pick_up_date} at {requisition.pick_up_time}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Drop-off</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.drop_off_location} on {requisition.drop_off_date} at {requisition.drop_off_time}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Vehicle</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.get_vehicle_type_display()}{' — ' + requisition.vehicle_type_other if requisition.vehicle_type == 'other' and requisition.vehicle_type_other else ''}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Requester</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.full_name}</td></tr>
        <tr><td style="padding:8px 12px;color:#6b7280;">Travelling Reason</td><td style="padding:8px 12px;">{requisition.travelling_reason}</td></tr>
        '''
    elif label == 'Internal':
        items = requisition.equipment_items.all()
        items_html = '<br>'.join(f'• {item.name} x{item.quantity} — {item.purpose}' for item in items)
        fields_html = f'''
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;width:140px;">Department</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;">{requisition.department}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Items</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{items_html}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Requester</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.full_name}</td></tr>
        <tr><td style="padding:8px 12px;color:#6b7280;">Email</td><td style="padding:8px 12px;">{requisition.email_address}</td></tr>
        '''

    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f6;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
<tr><td style="padding:30px 40px;background:linear-gradient(135deg,#2563eb,#1d4ed8);text-align:center;">
<h1 style="margin:0;color:#ffffff;font-size:22px;">{label} Requisition {requisition.request_number}</h1>
<p style="margin:8px 0 0;color:#bfdbfe;font-size:14px;">Action Required — {status_label}</p>
</td></tr>
<tr><td style="padding:30px 40px;">
<p style="margin:0 0 20px;font-size:15px;color:#374151;">Dear <strong>{recipient_name}</strong>,</p>
<p style="margin:0 0 20px;font-size:15px;color:#374151;line-height:1.6;">
A {label} Requisition ({requisition.request_number}) requires your <strong>{status_label}</strong>.
Please review the details below and take action.
</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border-radius:8px;margin-bottom:24px;">
{fields_html}
</table>
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
<td width="50%" style="padding-right:8px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="background:#16a34a;border-radius:8px;padding:12px 20px;">
<a href="{approve_link}" style="color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;display:block;">✓ Approve</a>
</td></tr>
</table>
</td>
<td width="50%" style="padding-left:8px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="background:#dc2626;border-radius:8px;padding:12px 20px;">
<a href="{reject_link}" style="color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;display:block;">✗ Reject</a>
</td></tr>
</table>
</td>
</tr>
</table>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #e5e7eb;text-align:center;">
<p style="margin:0;font-size:12px;color:#9ca3af;">This link expires in 7 days. If you did not expect this email, please ignore it.</p>
<p style="margin:8px 0 0;font-size:12px;color:#9ca3af;">Requisition Portal &bull; BRAC</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>'''


def _build_notification_email(recipient_name, label, requisition, subject_line, extra_lines=''):
    fields_html = ''
    if label == 'ICT':
        fields_html = f'''
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;width:140px;">Equipment</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;">{requisition.device_equipment.replace(chr(10), '<br>')}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Purpose</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.purpose}</td></tr>
        <tr><td style="padding:8px 12px;color:#6b7280;">Specification</td><td style="padding:8px 12px;">{requisition.equipment_specification}</td></tr>
        '''
    elif label == 'Transport':
        vehicle = requisition.get_vehicle_type_display()
        if requisition.vehicle_type == 'other' and requisition.vehicle_type_other:
            vehicle += f' — {requisition.vehicle_type_other}'
        driver_info = ''
        if requisition.driver:
            driver_info = f'<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Driver</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.driver.name} ({requisition.driver.car_no}) — {requisition.driver.cell_number}</td></tr>'
        fields_html = f'''
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;width:140px;">Destination</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;">{requisition.destination}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Pick-up</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.pick_up_location} on {requisition.pick_up_date} at {requisition.pick_up_time}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Drop-off</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.drop_off_location} on {requisition.drop_off_date} at {requisition.drop_off_time}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Vehicle</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{vehicle}</td></tr>
        {driver_info}
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Project</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{requisition.project_name_code}</td></tr>
        <tr><td style="padding:8px 12px;color:#6b7280;">Budget Code</td><td style="padding:8px 12px;">{requisition.budget_code}</td></tr>
        '''
    elif label == 'Internal':
        items = requisition.equipment_items.all()
        items_html = '<br>'.join(f'• {item.name} x{item.quantity} — {item.purpose}' for item in items)
        fields_html = f'''
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;width:140px;">Department</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;">{requisition.department}</td></tr>
        <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;">Items</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">{items_html}</td></tr>
        <tr><td style="padding:8px 12px;color:#6b7280;">Requester</td><td style="padding:8px 12px;">{requisition.full_name}</td></tr>
        '''

    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f6;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
<tr><td style="padding:30px 40px;background:linear-gradient(135deg,#2563eb,#1d4ed8);text-align:center;">
<h1 style="margin:0;color:#ffffff;font-size:22px;">{label} Requisition {requisition.request_number}</h1>
<p style="margin:8px 0 0;color:#bfdbfe;font-size:14px;">{subject_line}</p>
</td></tr>
<tr><td style="padding:30px 40px;">
<p style="margin:0 0 20px;font-size:15px;color:#374151;">Dear <strong>{recipient_name}</strong>,</p>
<p style="margin:0 0 20px;font-size:15px;color:#374151;line-height:1.6;">{extra_lines}</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border-radius:8px;margin-bottom:10px;">
{fields_html}
</table>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #e5e7eb;text-align:center;">
<p style="margin:0;font-size:12px;color:#9ca3af;">Requisition Portal &bull; BRAC</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>'''


def _approvers_for_stage(module_key, stage_key):
    """Work out who should be asked to act at a given stage.

    Read from the workflow configuration: the stage names the role that is
    allowed to act, and we email every active user holding it. Returns an empty
    list when the stage is unknown, which is what makes a misconfigured chain
    fail quietly in the email log rather than crash a submission.
    """
    from portal_config import engine
    from accounts.models import User

    stage = engine.get_stage(module_key, stage_key)
    if stage is None:
        return []
    if not stage.approver_role:
        # No role pinned: fall back to anyone who can approve at all.
        return list(User.objects.filter(is_active=True).exclude(role=User.Role.REQUESTER))

    # Admins hold every stage role implicitly (engine.stage_allows lets them
    # through), so they have to be on the mailing list too — otherwise a chain
    # configured for a role nobody holds would have no recipient at all.
    return list(
        User.objects.filter(is_active=True)
        .filter(Q(role=stage.approver_role) | Q(role=User.Role.ADMIN))
        .distinct()
    )


def send_approval_request(department, requisition, req_type, status, request=None):
    """Ask the role that owns ``status`` to act.

    ``status`` is the stage key the requisition is now sitting at, so the
    recipient list follows whatever chain is configured rather than a hardcoded
    two-step approval.
    """
    from accounts.models import User

    approvers = _approvers_for_stage(req_type, status)
    if not approvers:
        return

    if req_type == 'ict':
        dept = 'ict'
        label = 'ICT'
    elif req_type == 'transport':
        dept = 'transport'
        label = 'Transport'
    else:
        dept = 'internal'
        label = 'Internal'

    dept_config = EmailConfig.objects.filter(department=dept).first()

    for approver in approvers:
        to_email = approver.email or (dept_config.notification_email if dept_config else None)
        if not to_email:
            continue
        token = sign_action_token(req_type, requisition.pk, 'approve', approver.pk)
        reject_token = sign_action_token(req_type, requisition.pk, 'reject', approver.pk)
        approve_link = f'{BASE_URL}/notifications/action/{token}/'
        reject_link = f'{BASE_URL}/notifications/action/{reject_token}/'

        subject = f'{label} Requisition {requisition.request_number} — Action Required'
        html = _build_approval_email(approver.username, label, requisition, status, approve_link, reject_link)
        # Queue the email instead of sending synchronously
        from .tasks import queue_approval_email_for_approver
        queue_approval_email_for_approver(req_type, requisition.pk, status, approver.pk, dept, label)


def send_department_email(department, subject, message, to_emails, html=False, email_type='notification', req_type='', req_id=None):
    """Queue an email for background delivery.

    Replaces the synchronous SMTP call with a django-q task so the
    HTTP response returns immediately.
    """
    from .tasks import send_email_task

    to_list = to_emails if isinstance(to_emails, list) else [to_emails]
    for email in to_list:
        async_task(
            'notifications.tasks.send_email_task',
            department, subject, message, [email], html,
            email_type, req_type, req_id
        )


def log_audit(req_type, req_id, request_number, action, performed_by, details=''):
    from .models import AuditLog
    AuditLog.objects.create(
        req_type=req_type,
        req_id=req_id,
        request_number=request_number,
        action=action,
        performed_by=performed_by,
        details=details,
    )


def notify_requester(department, requisition, req_type, new_status):
    if req_type == 'ict':
        label = 'ICT'
    elif req_type == 'transport':
        label = 'Transport'
    else:
        label = 'Internal'

    from django.urls import reverse
    track_url = f'{BASE_URL}{reverse("notifications:track", args=[req_type, requisition.pk])}'

    track_button = f'<br><br><table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center"><a href="{track_url}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">Track Request Status</a></td></tr></table>'

    if new_status == 'pending_second':
        subject_line = 'First Level Approval Granted'
        extra = f'Your requisition has received first-level approval and is now pending second-level approval.{track_button}'
    elif new_status == 'approved':
        subject_line = 'Fully Approved'
        extra = f'Your requisition has been fully approved.{track_button}'
    elif new_status == 'rejected':
        subject_line = 'Rejected'
        extra = f'Your requisition has been rejected.<br><br>Reason: {requisition.rejection_reason}{track_button}'
    elif new_status == 'driver_assigned':
        subject_line = 'Driver Assigned'
        d = requisition.driver
        if d:
            extra = f'A driver has been assigned to your trip.<br><br>Driver: {d.name}<br>Car No: {d.car_no}<br>Cell: {d.cell_number}{track_button}'
        else:
            extra = f'A driver has been assigned to your trip.{track_button}'
    elif new_status == 'created':
        subject_line = 'Request Submitted Successfully'
        extra = f'Your {label} Requisition ({requisition.request_number}) has been submitted successfully.{track_button}'
    else:
        return

    html = _build_notification_email(requisition.full_name, label, requisition, subject_line, extra)
    subject = f'{label} Requisition {requisition.request_number} — {subject_line}'
    send_department_email(department, subject, html, [requisition.email_address], html=True, email_type='notification', req_type=req_type, req_id=requisition.pk)
