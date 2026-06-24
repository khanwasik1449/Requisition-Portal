from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from .models import TransportRequisition, Driver
from notifications.utils import send_approval_request, notify_requester, log_audit


@login_required
def list_view(request):
    if request.user.is_admin() or request.user.is_transport_admin():
        requisitions = TransportRequisition.objects.all()
    elif request.user.is_approver():
        requisitions = TransportRequisition.objects.filter(
            status__in=[TransportRequisition.Status.PENDING_FIRST, TransportRequisition.Status.PENDING_SECOND]
        ) | TransportRequisition.objects.filter(user=request.user)
    else:
        requisitions = TransportRequisition.objects.filter(user=request.user)
    return render(request, 'transport_requisition/list.html', {'requisitions': requisitions})


@login_required
def create_view(request):
    if request.method == 'POST':
        requisition = TransportRequisition.objects.create(
            user=request.user,
            full_name=request.POST['full_name'],
            email_address=request.POST['email_address'],
            mobile_number=request.POST['mobile_number'],
            designation=request.POST['designation'],
            pin=request.POST['pin'],
            num_passengers=request.POST['num_passengers'],
            vehicle_type=request.POST['vehicle_type'],
            vehicle_type_other=request.POST.get('vehicle_type_other', ''),
            pick_up_date=request.POST['pick_up_date'],
            pick_up_time=request.POST['pick_up_time'],
            pick_up_location=request.POST['pick_up_location'],
            destination=request.POST['destination'],
            drop_off_date=request.POST['drop_off_date'],
            drop_off_time=request.POST['drop_off_time'],
            drop_off_location=request.POST['drop_off_location'],
            travelling_reason=request.POST['travelling_reason'],
            project_name_code=request.POST.get('project_name_code_other') or request.POST['project_name_code'],
            budget_code=request.POST.get('budget_code_other') or request.POST['budget_code'],
            supervisor_acknowledged=request.POST.get('supervisor_acknowledged') == 'on',
            comments_remarks=request.POST.get('comments_remarks', ''),
        )
        log_audit('transport', requisition.pk, requisition.request_number, 'created', request.user)
        send_approval_request('transport', requisition, 'transport', 'pending_first')
        notify_requester('transport', requisition, 'transport', 'created')
        return redirect('transport_requisition:list')
    return render(request, 'transport_requisition/form.html')


@login_required
def detail_view(request, pk):
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    if not (request.user.is_admin() or request.user.is_approver() or requisition.user == request.user):
        return redirect('transport_requisition:list')
    return render(request, 'transport_requisition/detail.html', {'r': requisition})


@login_required
def approve_view(request, pk):
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    if not (request.user.is_approver() or request.user.is_admin()):
        return redirect('transport_requisition:list')

    if requisition.status == TransportRequisition.Status.PENDING_FIRST:
        if not request.user.is_first_approver():
            return redirect('transport_requisition:list')
        requisition.status = TransportRequisition.Status.PENDING_SECOND
        requisition.first_approver = request.user
        requisition.first_approved_at = timezone.now()
    elif requisition.status == TransportRequisition.Status.PENDING_SECOND:
        if not request.user.is_second_approver():
            return redirect('transport_requisition:list')
        requisition.status = TransportRequisition.Status.APPROVED
        requisition.second_approver = request.user
        requisition.second_approved_at = timezone.now()

    requisition.save()

    if requisition.status == TransportRequisition.Status.PENDING_SECOND:
        log_audit('transport', requisition.pk, requisition.request_number, 'pending_second', request.user)
        send_approval_request('transport', requisition, 'transport', 'pending_second')
        notify_requester('transport', requisition, 'transport', 'pending_second')
    elif requisition.status == TransportRequisition.Status.APPROVED:
        log_audit('transport', requisition.pk, requisition.request_number, 'approved', request.user)
        notify_requester('transport', requisition, 'transport', 'approved')

    return redirect('transport_requisition:list')


@login_required
def reject_view(request, pk):
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    if not (request.user.is_approver() or request.user.is_admin()):
        return redirect('transport_requisition:list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        requisition.status = TransportRequisition.Status.REJECTED
        requisition.rejection_reason = reason
        requisition.rejected_at = timezone.now()
        requisition.save()

        log_audit('transport', requisition.pk, requisition.request_number, 'rejected', request.user, reason)
        notify_requester('transport', requisition, 'transport', 'rejected')
        return redirect('transport_requisition:list')

    return render(request, 'transport_requisition/reject.html', {'r': requisition})


@login_required
def report_view(request):
    if not (request.user.is_admin() or request.user.is_transport_admin()):
        return redirect('transport_requisition:list')

    qs = TransportRequisition.objects.all()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')

    if date_from:
        qs = qs.filter(pick_up_date__gte=date_from)
    if date_to:
        qs = qs.filter(pick_up_date__lte=date_to)
    if status_filter:
        qs = qs.filter(status=status_filter)

    total = qs.count()
    approved = qs.filter(status=TransportRequisition.Status.APPROVED).count()
    rejected = qs.filter(status=TransportRequisition.Status.REJECTED).count()
    pending = qs.filter(status__in=[TransportRequisition.Status.PENDING_FIRST, TransportRequisition.Status.PENDING_SECOND]).count()

    return render(request, 'transport_requisition/report.html', {
        'requisitions': qs,
        'total': total,
        'approved': approved,
        'rejected': rejected,
        'pending': pending,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'Status': TransportRequisition.Status,
    })


@login_required
def export_excel_view(request):
    if not (request.user.is_admin() or request.user.is_transport_admin()):
        return redirect('transport_requisition:list')

    qs = TransportRequisition.objects.all()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')

    if date_from:
        qs = qs.filter(pick_up_date__gte=date_from)
    if date_to:
        qs = qs.filter(pick_up_date__lte=date_to)
    if status_filter:
        qs = qs.filter(status=status_filter)

    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Transport Requisitions'

    headers = ['Request #', 'Name', 'Email', 'Mobile', 'Designation', 'PIN', 'Passengers',
               'Vehicle Type', 'Pick-up Date', 'Pick-up Time', 'Pick-up Location',
               'Destination', 'Drop-off Date', 'Drop-off Time', 'Drop-off Location',
               'Travelling Reason', 'Project Name/Code', 'Budget Code',
               'Driver', 'Car No', 'Driver Cell', 'Status']

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = openpyxl.styles.PatternFill(start_color='D97706', end_color='D97706', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    for row, r in enumerate(qs, 2):
        data = [
            r.request_number, r.full_name, r.email_address, r.mobile_number, r.designation, r.pin,
            r.num_passengers, r.get_vehicle_type_display(),
            r.pick_up_date, str(r.pick_up_time), r.pick_up_location,
            r.destination, r.drop_off_date, str(r.drop_off_time), r.drop_off_location,
            r.travelling_reason, r.project_name_code, r.budget_code,
            r.driver.name if r.driver else '', r.driver.car_no if r.driver else '',
            r.driver.cell_number if r.driver else '',
            r.get_status_display()
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = thin_border

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="transport_requisitions_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    return response


@login_required
def assign_driver_view(request, pk):
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    if not (request.user.is_admin() or request.user.is_transport_admin()):
        return redirect('transport_requisition:list')
    if requisition.status != TransportRequisition.Status.APPROVED:
        return redirect('transport_requisition:list')

    drivers = Driver.objects.all()

    if request.method == 'POST':
        driver_id = request.POST.get('driver')
        if driver_id:
            requisition.driver_id = driver_id
            requisition.assigned_by = request.user
            requisition.assigned_at = timezone.now()
            requisition.save()

            notify_requester('transport', requisition, 'transport', 'driver_assigned')

        return redirect('transport_requisition:detail', pk=requisition.pk)

    return render(request, 'transport_requisition/assign_driver.html', {'r': requisition, 'drivers': drivers})
