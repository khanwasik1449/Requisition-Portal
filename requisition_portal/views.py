from itertools import chain
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import HttpResponse
from django.template.loader import render_to_string
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML = None
from ict_requisition.models import ICTRequisition
from transport_requisition.models import TransportRequisition
from internal_requisition.models import InternalRequisition
from accounts.models import User

STATUS_LABELS = {
    'pending_first': 'Pending Supervisor Approval',
    'pending_grants': 'Pending Grants Approval',
    'pending_transport': 'Pending Transport Admin',
    'approved': 'Approved',
    'assigned': 'Vehicle and Driver Assigned',
    'rejected': 'Rejected',
    # Legacy value kept so requisitions created before the Grants stage existed
    # still render a sensible label.
    'pending_second': 'Pending Grants Approval',
}

PENDING = ['pending_first', 'pending_grants', 'pending_transport']

# req_type -> (model, human label, emoji, summary field, url name)
REQUISITION_TYPES = {
    'ict': (ICTRequisition, 'ICT', '💻', 'device_equipment', 'ict_requisition:detail'),
    'transport': (TransportRequisition, 'Transport', '🚗', 'destination', 'transport_requisition:detail'),
    'internal': (InternalRequisition, 'Internal', '📋', 'department', 'internal_requisition:detail'),
}


def visible_types():
    """Requisition types to surface in the UI (enabled AND visible)."""
    from portal_config.engine import visible_module_keys
    visible = set(visible_module_keys())
    return [k for k in ('ict', 'transport', 'internal') if k in visible]


@require_GET
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'public_home.html')


@login_required
def dashboard(request):
    context = {}
    from portal_config.engine import visible_module_keys
    visible = set(visible_module_keys())

    if request.user.is_admin():
        for key in visible_types():
            model, _label, _emoji, _field, _url = REQUISITION_TYPES[key]
            context[f'{key}_count'] = model.objects.count()
            context[f'{key}_pending'] = model.objects.filter(status__in=PENDING).count()
        # MeetSpace
        if 'meetspace' in visible:
            from meetspace.models import Booking
            context['meetspace_count'] = Booking.objects.count()
            context['meetspace_pending'] = Booking.objects.filter(status__in=['pending']).count()
        context['pending_users'] = User.objects.filter(is_active=False).count()

    elif 'ict' in visible and request.user.is_ict_admin():
        context['ict_count'] = ICTRequisition.objects.count()
        context['ict_pending'] = ICTRequisition.objects.filter(status__in=PENDING).count()

    elif 'transport' in visible and request.user.is_transport_admin():
        context['transport_count'] = TransportRequisition.objects.count()
        context['transport_pending'] = TransportRequisition.objects.filter(status__in=PENDING).count()

    elif 'internal' in visible and request.user.is_internal_admin():
        context['internal_count'] = InternalRequisition.objects.count()
        context['internal_pending'] = InternalRequisition.objects.filter(status__in=PENDING).count()

    elif 'meetspace' in visible and request.user.is_hr_admin():
        from meetspace.models import Booking
        context['meetspace_count'] = Booking.objects.count()
        context['meetspace_pending'] = Booking.objects.filter(status__in=['pending']).count()

    elif 'hr' in visible and request.user.is_hr_admin():
        return redirect('contracts:dashboard')

    else:
        if visible_types():
            return render(request, 'selection.html')
        context['no_modules'] = True
        return render(request, 'selection.html')

    return render(request, 'admin_dashboard.html', context)


@login_required
def my_requisitions(request):
    items = []
    for key in visible_types():
        model, label, icon, field, url_name = REQUISITION_TYPES[key]
        for r in model.objects.filter(user=request.user).values(
            'pk', 'request_number', field, 'status', 'created_at'
        ):
            raw = r[field] or ''
            items.append({
                'type': label,
                'type_icon': icon,
                'pk': r['pk'],
                'request_number': r['request_number'],
                'summary': raw.split('\n')[0][:60],
                'status': r['status'],
                'status_label': STATUS_LABELS.get(r['status'], r['status']),
                'created_at': r['created_at'],
                'url': url_name,
            })

    items.sort(key=lambda x: x['created_at'], reverse=True)
    return render(request, 'my_requisitions.html', {'items': items})


def documentation(request):
    fmt = request.GET.get('download')
    html = render_to_string('documentation.html')
    if fmt == 'pdf':
        if not WEASYPRINT_AVAILABLE:
            return HttpResponse(
                'PDF generation requires weasyprint which is not installed. '
                'On Windows, install it via WSL2 or use the HTML download option.',
                content_type='text/plain',
                status=501
            )
        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Requisition_Portal_Documentation.pdf"'
        return response
    elif fmt == 'html':
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="Requisition_Portal_Documentation.html"'
        return response
    return render(request, 'documentation.html')
