from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import InternalRequisition, InternalEquipmentItem
from notifications.utils import send_approval_request, notify_requester, log_audit


@login_required
def list_view(request):
    if request.user.is_admin() or request.user.is_internal_admin():
        requisitions = InternalRequisition.objects.all()
    elif request.user.is_approver():
        requisitions = InternalRequisition.objects.filter(
            status__in=[InternalRequisition.Status.PENDING_FIRST, InternalRequisition.Status.PENDING_SECOND]
        ) | InternalRequisition.objects.filter(user=request.user)
    else:
        requisitions = InternalRequisition.objects.filter(user=request.user)
    return render(request, 'internal_requisition/list.html', {'requisitions': requisitions})


@login_required
def create_view(request):
    if request.method == 'POST':
        requisition = InternalRequisition.objects.create(
            user=request.user,
            full_name=request.POST['full_name'],
            email_address=request.POST['email_address'],
            mobile_number=request.POST['mobile_number'],
            designation=request.POST['designation'],
            pin=request.POST['pin'],
            department=request.POST['department'],
        )
        names = request.POST.getlist('eq_name[]')
        quantities = request.POST.getlist('eq_quantity[]')
        purposes = request.POST.getlist('eq_purpose[]')
        for name, qty, purpose in zip(names, quantities, purposes):
            if name.strip():
                InternalEquipmentItem.objects.create(
                    requisition=requisition,
                    name=name.strip(),
                    quantity=int(qty) if qty else 1,
                    purpose=purpose.strip(),
                )
        log_audit('internal', requisition.pk, requisition.request_number, 'created', request.user)
        send_approval_request('internal', requisition, 'internal', 'pending_first')
        notify_requester('internal', requisition, 'internal', 'created')
        return redirect('internal_requisition:list')
    return render(request, 'internal_requisition/form.html')


@login_required
def detail_view(request, pk):
    requisition = get_object_or_404(InternalRequisition, pk=pk)
    if not (request.user.is_admin() or request.user.is_approver() or requisition.user == request.user):
        return redirect('internal_requisition:list')
    return render(request, 'internal_requisition/detail.html', {'r': requisition})


@login_required
def approve_view(request, pk):
    requisition = get_object_or_404(InternalRequisition, pk=pk)
    if not (request.user.is_approver() or request.user.is_admin()):
        return redirect('internal_requisition:list')

    if requisition.status == InternalRequisition.Status.PENDING_FIRST:
        if not request.user.is_first_approver():
            return redirect('internal_requisition:list')
        requisition.status = InternalRequisition.Status.PENDING_SECOND
        requisition.first_approver = request.user
        requisition.first_approved_at = timezone.now()
    elif requisition.status == InternalRequisition.Status.PENDING_SECOND:
        if not request.user.is_second_approver():
            return redirect('internal_requisition:list')
        requisition.status = InternalRequisition.Status.APPROVED
        requisition.second_approver = request.user
        requisition.second_approved_at = timezone.now()

    requisition.save()

    if requisition.status == InternalRequisition.Status.PENDING_SECOND:
        log_audit('internal', requisition.pk, requisition.request_number, 'pending_second', request.user)
        send_approval_request('internal', requisition, 'internal', 'pending_second')
        notify_requester('internal', requisition, 'internal', 'pending_second')
    elif requisition.status == InternalRequisition.Status.APPROVED:
        log_audit('internal', requisition.pk, requisition.request_number, 'approved', request.user)
        notify_requester('internal', requisition, 'internal', 'approved')

    return redirect('internal_requisition:list')


@login_required
def reject_view(request, pk):
    requisition = get_object_or_404(InternalRequisition, pk=pk)
    if not (request.user.is_approver() or request.user.is_admin()):
        return redirect('internal_requisition:list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        requisition.status = InternalRequisition.Status.REJECTED
        requisition.rejection_reason = reason
        requisition.rejected_at = timezone.now()
        requisition.save()

        log_audit('internal', requisition.pk, requisition.request_number, 'rejected', request.user, reason)
        notify_requester('internal', requisition, 'internal', 'rejected')
        return redirect('internal_requisition:list')

    return render(request, 'internal_requisition/reject.html', {'r': requisition})
