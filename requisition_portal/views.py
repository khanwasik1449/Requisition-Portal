from itertools import chain
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from ict_requisition.models import ICTRequisition
from transport_requisition.models import TransportRequisition
from internal_requisition.models import InternalRequisition
from accounts.models import User

STATUS_LABELS = {
    'pending_first': 'Pending First Approval',
    'pending_second': 'Pending Second Approval',
    'approved': 'Approved',
    'rejected': 'Rejected',
}


@require_GET
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'public_home.html')


@login_required
def dashboard(request):
    context = {}

    if request.user.is_admin():
        ict_count = ICTRequisition.objects.count()
        transport_count = TransportRequisition.objects.count()
        internal_count = InternalRequisition.objects.count()
        ict_pending = ICTRequisition.objects.filter(status__in=['pending_first', 'pending_second']).count()
        transport_pending = TransportRequisition.objects.filter(status__in=['pending_first', 'pending_second']).count()
        internal_pending = InternalRequisition.objects.filter(status__in=['pending_first', 'pending_second']).count()
        pending_users = User.objects.filter(is_active=False).count()

        context.update({
            'ict_count': ict_count,
            'transport_count': transport_count,
            'internal_count': internal_count,
            'ict_pending': ict_pending,
            'transport_pending': transport_pending,
            'internal_pending': internal_pending,
            'pending_users': pending_users,
        })

    elif request.user.is_ict_admin():
        context['ict_count'] = ICTRequisition.objects.count()
        context['ict_pending'] = ICTRequisition.objects.filter(status__in=['pending_first', 'pending_second']).count()

    elif request.user.is_transport_admin():
        context['transport_count'] = TransportRequisition.objects.count()
        context['transport_pending'] = TransportRequisition.objects.filter(status__in=['pending_first', 'pending_second']).count()

    elif request.user.is_internal_admin():
        context['internal_count'] = InternalRequisition.objects.count()
        context['internal_pending'] = InternalRequisition.objects.filter(status__in=['pending_first', 'pending_second']).count()

    elif request.user.is_hr_admin():
        return redirect('contracts:dashboard')

    else:
        return render(request, 'selection.html')

    return render(request, 'admin_dashboard.html', context)


@login_required
def my_requisitions(request):
    ict_qs = ICTRequisition.objects.filter(user=request.user).values(
        'pk', 'request_number', 'device_equipment', 'status', 'created_at'
    )
    transport_qs = TransportRequisition.objects.filter(user=request.user).values(
        'pk', 'request_number', 'destination', 'status', 'created_at'
    )
    internal_qs = InternalRequisition.objects.filter(user=request.user).values(
        'pk', 'request_number', 'department', 'status', 'created_at'
    )

    items = []
    for r in ict_qs:
        items.append({
            'type': 'ICT',
            'type_icon': '💻',
            'pk': r['pk'],
            'request_number': r['request_number'],
            'summary': r['device_equipment'].split('\n')[0][:60] if r['device_equipment'] else '',
            'status': r['status'],
            'status_label': STATUS_LABELS.get(r['status'], r['status']),
            'created_at': r['created_at'],
            'url': 'ict_requisition:detail',
        })
    for r in transport_qs:
        items.append({
            'type': 'Transport',
            'type_icon': '🚗',
            'pk': r['pk'],
            'request_number': r['request_number'],
            'summary': r['destination'][:60] if r['destination'] else '',
            'status': r['status'],
            'status_label': STATUS_LABELS.get(r['status'], r['status']),
            'created_at': r['created_at'],
            'url': 'transport_requisition:detail',
        })
    for r in internal_qs:
        items.append({
            'type': 'Internal',
            'type_icon': '📋',
            'pk': r['pk'],
            'request_number': r['request_number'],
            'summary': r['department'][:60] if r['department'] else '',
            'status': r['status'],
            'status_label': STATUS_LABELS.get(r['status'], r['status']),
            'created_at': r['created_at'],
            'url': 'internal_requisition:detail',
        })

    items.sort(key=lambda x: x['created_at'], reverse=True)
    return render(request, 'my_requisitions.html', {'items': items})


def documentation(request):
    fmt = request.GET.get('download')
    html = render_to_string('documentation.html')
    if fmt == 'pdf':
        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Requisition_Portal_Documentation.pdf"'
        return response
    elif fmt == 'html':
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="Requisition_Portal_Documentation.html"'
        return response
    return render(request, 'documentation.html')
