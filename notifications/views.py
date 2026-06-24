import itertools
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import EmailConfig, Department, EmailLog, AuditLog
from .utils import unsign_action_token, send_approval_request
from accounts.models import User


@login_required
def config_list(request):
    if not request.user.is_admin():
        return redirect('dashboard')
    configs = EmailConfig.objects.all()
    return render(request, 'notifications/config_list.html', {'configs': configs})


@login_required
def config_create(request):
    if not request.user.is_admin():
        return redirect('dashboard')
    used_depts = EmailConfig.objects.values_list('department', flat=True)
    available = [d for d in Department.choices if d[0] not in used_depts]

    if not available:
        messages.warning(request, 'All departments already have email configurations.')
        return redirect('notifications:config_list')

    if request.method == 'POST':
        config = EmailConfig.objects.create(
            department=request.POST['department'],
            email_host=request.POST['email_host'],
            email_port=int(request.POST['email_port']),
            email_host_user=request.POST['email_host_user'],
            email_host_password=request.POST['email_host_password'],
            email_use_tls=request.POST.get('email_use_tls') == 'on',
            from_email=request.POST['from_email'],
            notification_email=request.POST['notification_email'],
            is_active=request.POST.get('is_active') == 'on',
        )
        messages.success(request, f'{config.get_department_display()} email configuration created.')
        return redirect('notifications:config_list')

    return render(request, 'notifications/config_edit.html', {'config': None, 'available': available})


@login_required
def config_edit(request, pk):
    if not request.user.is_admin():
        return redirect('dashboard')
    config = get_object_or_404(EmailConfig, pk=pk)

    if request.method == 'POST':
        config.email_host = request.POST['email_host']
        config.email_port = int(request.POST['email_port'])
        config.email_host_user = request.POST['email_host_user']
        if request.POST.get('email_host_password'):
            config.email_host_password = request.POST['email_host_password']
        config.email_use_tls = request.POST.get('email_use_tls') == 'on'
        config.from_email = request.POST['from_email']
        config.notification_email = request.POST['notification_email']
        config.is_active = request.POST.get('is_active') == 'on'
        config.save()
        messages.success(request, f'{config.get_department_display()} email configuration updated.')
        return redirect('notifications:config_list')

    return render(request, 'notifications/config_edit.html', {'config': config})


@login_required
def config_delete(request, pk):
    if not request.user.is_admin():
        return redirect('dashboard')
    config = get_object_or_404(EmailConfig, pk=pk)
    dept = config.get_department_display()
    config.delete()
    messages.success(request, f'{dept} email configuration deleted.')
    return redirect('notifications:config_list')


REQUISITION_MODELS = {}


def get_requisition_model(req_type):
    if req_type not in REQUISITION_MODELS:
        if req_type == 'ict':
            from ict_requisition.models import ICTRequisition
            REQUISITION_MODELS['ict'] = ICTRequisition
        elif req_type == 'transport':
            from transport_requisition.models import TransportRequisition
            REQUISITION_MODELS['transport'] = TransportRequisition
        elif req_type == 'internal':
            from internal_requisition.models import InternalRequisition
            REQUISITION_MODELS['internal'] = InternalRequisition
    return REQUISITION_MODELS.get(req_type)


def email_action_view(request, token):
    data = unsign_action_token(token)
    if not data:
        return render(request, 'notifications/action_error.html', {'error': 'Invalid or expired link.'})

    model = get_requisition_model(data['type'])
    if not model:
        return render(request, 'notifications/action_error.html', {'error': 'Invalid requisition type.'})

    requisition = get_object_or_404(model, pk=data['id'])
    actor = get_object_or_404(User, pk=data['user_id'])

    if data['action'] == 'approve':
        if requisition.status not in (model.Status.PENDING_FIRST, model.Status.PENDING_SECOND):
            return render(request, 'notifications/action_error.html', {'error': 'This requisition is no longer pending approval.'})

        if requisition.status == model.Status.PENDING_FIRST:
            if not (actor.is_first_approver() or actor.is_admin()):
                return render(request, 'notifications/action_error.html', {'error': 'You are not authorized for first-level approval.'})
            requisition.status = model.Status.PENDING_SECOND
            requisition.first_approver = actor
            requisition.first_approved_at = timezone.now()
        elif requisition.status == model.Status.PENDING_SECOND:
            if not (actor.is_second_approver() or actor.is_admin()):
                return render(request, 'notifications/action_error.html', {'error': 'You are not authorized for second-level approval.'})
            requisition.status = model.Status.APPROVED
            requisition.second_approver = actor
            requisition.second_approved_at = timezone.now()

        requisition.save()
        return render(request, 'notifications/action_success.html', {'message': f'Requisition #{requisition.pk} has been approved.'})

    elif data['action'] == 'reject':
        if request.method == 'POST':
            reason = request.POST.get('reason', '')
            requisition.status = model.Status.REJECTED
            requisition.rejection_reason = reason
            requisition.rejected_at = timezone.now()
            requisition.save()
            return render(request, 'notifications/action_success.html', {'message': f'Requisition #{requisition.pk} has been rejected.'})
        return render(request, 'notifications/reject_reason.html', {'r': requisition, 'token': token, 'portal_url': '/'})

    return render(request, 'notifications/action_error.html', {'error': 'Invalid action.'})


REQUISITION_LOOKUP = {}


def _get_req_model(req_type):
    if req_type not in REQUISITION_LOOKUP:
        if req_type == 'ict':
            from ict_requisition.models import ICTRequisition
            REQUISITION_LOOKUP[req_type] = ICTRequisition
        elif req_type == 'transport':
            from transport_requisition.models import TransportRequisition
            REQUISITION_LOOKUP[req_type] = TransportRequisition
        elif req_type == 'internal':
            from internal_requisition.models import InternalRequisition
            REQUISITION_LOOKUP[req_type] = InternalRequisition
    return REQUISITION_LOOKUP.get(req_type)


@login_required
def email_logs(request):
    if not request.user.is_admin():
        return redirect('dashboard')
    logs = EmailLog.objects.all()[:100]
    failed_count = EmailLog.objects.filter(status=EmailLog.Status.FAILED).count()
    return render(request, 'notifications/email_logs.html', {'logs': logs, 'failed_count': failed_count})


@login_required
def retry_email(request, pk):
    if not request.user.is_admin():
        return redirect('dashboard')
    log = get_object_or_404(EmailLog, pk=pk)
    if log.status == EmailLog.Status.SUCCESS:
        messages.info(request, 'This email was already sent successfully.')
        return redirect('notifications:email_logs')

    new_log = None
    if log.email_type == 'approval_request' and log.req_type and log.req_id:
        model = _get_req_model(log.req_type)
        if model:
            try:
                requisition = model.objects.get(pk=log.req_id)
                send_approval_request(log.department, requisition, log.req_type,
                                      'pending_second' if requisition.status in ['pending_second'] else 'pending_first')
                messages.success(request, f'Retry initiated for #{log.req_id}.')
            except model.DoesNotExist:
                messages.error(request, 'Requisition not found.')
    else:
        messages.warning(request, 'Cannot retry this email automatically.')
    return redirect('notifications:email_logs')


@login_required
def retry_all_failed(request):
    if not request.user.is_admin():
        return redirect('dashboard')
    failed = EmailLog.objects.filter(status=EmailLog.Status.FAILED)
    retried = 0
    for log in failed:
        if log.email_type == 'approval_request' and log.req_type and log.req_id:
            model = _get_req_model(log.req_type)
            if model:
                try:
                    requisition = model.objects.get(pk=log.req_id)
                    send_approval_request(log.department, requisition, log.req_type,
                                          'pending_second' if requisition.status in ['pending_second'] else 'pending_first')
                    retried += 1
                except model.DoesNotExist:
                    pass
    messages.success(request, f'Retried {retried} failed email(s).')
    return redirect('notifications:email_logs')


def track_view(request, req_type, pk):
    model = get_requisition_model(req_type)
    if not model:
        return render(request, 'notifications/action_error.html', {'error': 'Invalid requisition type.'})
    requisition = get_object_or_404(model, pk=pk)
    labels = {'ict': 'ICT', 'transport': 'Transport', 'internal': 'Internal'}
    return render(request, 'notifications/track.html', {
        'r': requisition,
        'label': labels.get(req_type, 'Requisition'),
    })


@login_required
def audit_log_view(request):
    if request.user.is_admin():
        logs = AuditLog.objects.all()[:200]
    else:
        logs = AuditLog.objects.filter(
            req_id__in=list(
                itertools.chain(
                    request.user.ict_requisitions.values_list('pk', flat=True),
                    request.user.transport_requisitions.values_list('pk', flat=True),
                    request.user.internal_requisitions.values_list('pk', flat=True),
                )
            )
        )[:200]
    return render(request, 'notifications/audit_log.html', {'logs': logs})


@login_required
def send_reminder(request, req_type, pk):
    if not (request.user.is_admin() or
            request.user.is_ict_admin() or
            request.user.is_transport_admin() or
            request.user.is_internal_admin()):
        return redirect('dashboard')

    model = _get_req_model(req_type)
    if not model:
        messages.error(request, 'Invalid requisition type.')
        return redirect('dashboard')

    requisition = get_object_or_404(model, pk=pk)
    if requisition.status == model.Status.PENDING_FIRST:
        send_approval_request(req_type, requisition, req_type, 'pending_first')
        messages.success(request, f'Approval request sent for #{requisition.pk}.')
    elif requisition.status == model.Status.PENDING_SECOND:
        send_approval_request(req_type, requisition, req_type, 'pending_second')
        messages.success(request, f'Second-level approval request sent for #{requisition.pk}.')
    else:
        messages.info(request, f'Requisition #{requisition.pk} is not pending.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
