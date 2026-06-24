from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from accounts.models import User

from .models import Payslip, PayslipRequest


@login_required
def create_payslip(request):
    if request.method == "POST":
        total_salary = float(request.POST.get("basic_salary") or 0)
        basic = total_salary * 0.50
        house_rent = total_salary * 0.30
        medical_allowance = total_salary * 0.10
        conveyance = total_salary * 0.10
        
        payslip = Payslip.objects.create(
            pin=request.POST.get("pin"),
            name=request.POST.get("name"),
            designation=request.POST.get("designation"),
            month=request.POST.get("month"),
            year=request.POST.get("year"),
            project=request.POST.get("project") or "BUIED",
            branch=request.POST.get("branch") or "Niketon Housing, Gulshan",
            basic_salary=basic,
            house_rent=house_rent,
            medical_allowance=medical_allowance,
            conveyance=conveyance,
            transport=request.POST.get("transport") or 0,
            income_tax=request.POST.get("income_tax") or 0,
            other_deduction=request.POST.get("other_deduction") or 0,
        )
        request.session["payslip_id"] = payslip.id
        return redirect("payslip:create_payslip")

    payslip_id = request.session.pop("payslip_id", None)
    payslip = None

    if payslip_id:
        payslip = Payslip.objects.filter(id=payslip_id).first()

    return render(request, "payslip/form.html", {"created_payslip": payslip})


@login_required
def payslip_list(request):
    payslips = Payslip.objects.all().order_by('-id')
    return render(request, "payslip/list.html", {"payslips": payslips})


@login_required
def generate_payslip_pdf(request, id):
    payslip = get_object_or_404(Payslip, id=id)

    html_string = render_to_string(
        "payslip/pdf/payslip.html",
        {"payslip": payslip}
    )

    from weasyprint import HTML
    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf()

    return HttpResponse(
        pdf,
        content_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="payslip_{payslip.pin}_{payslip.month}_{payslip.year}.pdf"'
        }
    )


MONTHS_LIST = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@require_http_methods(["GET", "POST"])
def request_payslip(request):
    if request.method == "POST":
        selected = request.POST.getlist("selected_months")
        months_str = ", ".join(selected) if selected else request.POST.get("months", "")
        year = request.POST.get("year", "2026")
        PayslipRequest.objects.create(
            name=request.POST.get("name"),
            pin=request.POST.get("pin"),
            months=months_str,
            year=year,
        )
        messages.success(request, "Your payslip request has been submitted successfully!")
        return redirect("payslip:request_payslip")
    from datetime import date
    current_year = date.today().year
    years = range(current_year - 2, current_year + 3)
    return render(request, "payslip/request_form.html", {
        "months": MONTHS_LIST,
        "years": years,
        "current_year": current_year,
    })


@login_required
def payslip_requests(request):
    if not request.user.is_hr_admin():
        messages.error(request, "Access denied. HR admin only.")
        return redirect("contracts:dashboard")
    requests_list = PayslipRequest.objects.all().order_by("-created_at")
    return render(request, "payslip/requests_list.html", {"requests": requests_list})