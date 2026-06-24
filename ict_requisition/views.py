from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import ICTRequisition
from accounts.models import User
from notifications.utils import send_approval_request, notify_requester, log_audit


@login_required
def list_view(request):
    if request.user.is_admin() or request.user.is_ict_admin():
        requisitions = ICTRequisition.objects.all()
    elif request.user.is_approver():
        requisitions = ICTRequisition.objects.filter(
            status__in=[ICTRequisition.Status.PENDING_FIRST, ICTRequisition.Status.PENDING_SECOND]
        ) | ICTRequisition.objects.filter(user=request.user)
    else:
        requisitions = ICTRequisition.objects.filter(user=request.user)
    return render(request, 'ict_requisition/list.html', {'requisitions': requisitions})


@login_required
def create_view(request):
    supervisors = User.objects.filter(role='supervisor', is_active=True)
    if request.method == 'POST':
        supervisor_id = request.POST.get('supervisor')
        equipment_list = request.POST.getlist('device_equipment')
        if not equipment_list:
            return render(request, 'ict_requisition/form.html', {
                'supervisors': User.objects.filter(role='supervisor', is_active=True),
                'error': 'Please select at least one equipment item.',
            })
        requisition = ICTRequisition.objects.create(
            user=request.user,
            full_name=request.POST['full_name'],
            email_address=request.POST['email_address'],
            designation=request.POST['designation'],
            pin_number=request.POST['pin_number'],
            contact_number=request.POST['contact_number'],
            device_equipment='\n'.join(equipment_list),
            equipment_specification=request.POST.get('equipment_specification', ''),
            purpose=request.POST['purpose'],
            requisition_date=request.POST['requisition_date'],
            requirement_date=request.POST['requirement_date'],
            return_date=request.POST.get('return_date') or None,
            supervisor_id=supervisor_id if supervisor_id else None,
        )
        log_audit('ict', requisition.pk, requisition.request_number, 'created', request.user)
        send_approval_request('ict', requisition, 'ict', 'pending_first')
        notify_requester('ict', requisition, 'ict', 'created')
        return redirect('ict_requisition:list')
    return render(request, 'ict_requisition/form.html', {'supervisors': supervisors})


@login_required
def detail_view(request, pk):
    requisition = get_object_or_404(ICTRequisition, pk=pk)
    if not (request.user.is_admin() or request.user.is_approver() or requisition.user == request.user):
        return redirect('ict_requisition:list')
    return render(request, 'ict_requisition/detail.html', {'r': requisition})


@login_required
def approve_view(request, pk):
    requisition = get_object_or_404(ICTRequisition, pk=pk)
    if not (request.user.is_approver() or request.user.is_admin()):
        return redirect('ict_requisition:list')

    if requisition.status == ICTRequisition.Status.PENDING_FIRST:
        if not request.user.is_first_approver():
            return redirect('ict_requisition:list')
        requisition.status = ICTRequisition.Status.PENDING_SECOND
        requisition.first_approver = request.user
        requisition.first_approved_at = timezone.now()
    elif requisition.status == ICTRequisition.Status.PENDING_SECOND:
        if not request.user.is_second_approver():
            return redirect('ict_requisition:list')
        requisition.status = ICTRequisition.Status.APPROVED
        requisition.second_approver = request.user
        requisition.second_approved_at = timezone.now()

    requisition.save()

    if requisition.status == ICTRequisition.Status.PENDING_SECOND:
        log_audit('ict', requisition.pk, requisition.request_number, 'pending_second', request.user)
        send_approval_request('ict', requisition, 'ict', 'pending_second')
        notify_requester('ict', requisition, 'ict', 'pending_second')
    elif requisition.status == ICTRequisition.Status.APPROVED:
        log_audit('ict', requisition.pk, requisition.request_number, 'approved', request.user)
        notify_requester('ict', requisition, 'ict', 'approved')

    return redirect('ict_requisition:list')


@login_required
def reject_view(request, pk):
    requisition = get_object_or_404(ICTRequisition, pk=pk)
    if not (request.user.is_approver() or request.user.is_admin()):
        return redirect('ict_requisition:list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        requisition.status = ICTRequisition.Status.REJECTED
        requisition.rejection_reason = reason
        requisition.rejected_at = timezone.now()
        requisition.save()

        log_audit('ict', requisition.pk, requisition.request_number, 'rejected', request.user, reason)
        notify_requester('ict', requisition, 'ict', 'rejected')
        return redirect('ict_requisition:list')

    return render(request, 'ict_requisition/reject.html', {'r': requisition})
