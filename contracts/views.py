from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse
from datetime import date, timedelta
from django.core.mail import EmailMessage

from django_q.tasks import async_task
from .models import Contract, EmailLog, EmailConfig
import csv
import pandas as pd
import time


# =========================
# LOGIN / LOGOUT
# =========================

# =========================
# CONTRACT CREATE (HOME)
# =========================

@login_required
def create_contract(request):
    if request.method == "POST":
        pin = request.POST.get("pin")
        name = request.POST.get("name")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        salary = request.POST.get("salary")
        
        # Validate required fields
        if not start_date or not end_date or not salary or float(salary or 0) <= 0:
            messages.error(request, "Start date, end date, and salary are required.")
            return render(request, "contracts/form.html", {})
        
        contract = Contract.objects.create(
            pin=pin,
            name=name,
            designation=request.POST.get("designation"),
            new_designation=request.POST.get("new_designation"),
            start_date=start_date,
            end_date=end_date,
            salary=salary,
            contract_type=request.POST.get("contract_type"),
        )
        
        # Update or create employee with latest details from contract form
        try:
            from employees.models import Employee
            emp, created = Employee.objects.update_or_create(
                pin=contract.pin,
                defaults={
                    'name': contract.name,
                    'designation': contract.new_designation if contract.contract_type == "Renewal" and contract.new_designation else contract.designation,
                    'salary': contract.salary,
                    'phone': request.POST.get("phone") or '',
                    'email': request.POST.get("email") or '',
                    'tin': request.POST.get("tin") or '',
                }
            )
            print(f"Employee {'created' if created else 'updated'}: {emp.name}, TIN: {emp.tin}")
        except Exception as e:
            print(f"Error updating employee: {e}")
        
        request.session["contract_id"] = contract.id
        return redirect("contracts:create_contract")

    contract_id = request.session.pop("contract_id", None)
    contract = None

    if contract_id:
        contract = Contract.objects.filter(id=contract_id).first()

    return render(request, "contracts/form.html", {
        "created_contract": contract
    })


# =========================
# CONTRACT LIST / DASHBOARD
# =========================

@login_required
def contracts_dashboard(request):
    contracts = Contract.objects.all().order_by('-id')
    return render(request, 'contracts/list.html', {'contracts': contracts})


@login_required
def contract_list(request):
    page_size = 15
    page = int(request.GET.get('page', 1))
    search = request.GET.get('q', '').strip()
    contract_type = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    sort_key = request.GET.get('sort', '-id')
    
    valid_sorts = {'id', '-id', 'pin', '-pin', 'name', '-name', 'salary', '-salary', 'start_date', '-start_date'}
    if sort_key not in valid_sorts:
        sort_key = '-id'
    
    qs = Contract.objects.all()
    
    if search:
        qs = qs.filter(
            Q(pin__icontains=search) |
            Q(name__icontains=search) |
            Q(designation__icontains=search) |
            Q(new_designation__icontains=search)
        )
    
    if contract_type:
        qs = qs.filter(contract_type=contract_type)
    
    if status_filter == 'Expired':
        qs = qs.filter(end_date__lt=date.today())
    elif status_filter == 'Expiring':
        qs = qs.filter(end_date__gte=date.today(), end_date__lte=date.today() + timedelta(days=30))
    elif status_filter == 'Active':
        qs = qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=date.today()))
    
    total = qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * page_size
    
    order_by = sort_key.lstrip('-')
    if sort_key.startswith('-'):
        qs = qs.order_by(f'-{order_by}')
    else:
        qs = qs.order_by(order_by)
    
    contracts = qs[offset:offset + page_size]
    
    return render(request, "contracts/list.html", {
        "contracts": list(contracts.values(
            'id', 'pin', 'name', 'designation', 'new_designation',
            'salary', 'contract_type', 'start_date', 'end_date'
        )),
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "search": search,
        "contract_type": contract_type,
        "status_filter": status_filter,
        "sort_key": sort_key,
    })


# =========================
# PDF GENERATION
# =========================

@login_required
def generate_pdf(request, id):
    contract = get_object_or_404(Contract, id=id)

    if contract.contract_type == "Renewal":
        template_name = "contracts/pdf/renewal.html"

    elif contract.contract_type == "Extension":
        template_name = "contracts/pdf/extension.html"

    elif contract.contract_type == "Revision":
        template_name = "contracts/pdf/revision.html"

    elif contract.contract_type == "New":
        template_name = "contracts/pdf/new.html"

    else:
        template_name = "contracts/pdf/new.html"

    print("🔥 TEMPLATE USED:", template_name)

    html_string = render_to_string(
        template_name,
        {"contract": contract}
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
            'Content-Disposition': f'attachment; filename="contract_{contract.pin}.pdf"'
        }
    )

# =========================
# BULK CREATE CONTRACT (CSV)
# =========================

@login_required
def bulk_create_contracts(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        
        if not file:
            messages.error(request, "No file uploaded!")
            return redirect("contracts:bulk_upload_contracts")
        
        if not file.name.endswith('.csv'):
            messages.error(request, "Only CSV files allowed!")
            return redirect("contracts:bulk_upload_contracts")
        
        try:
            from employees.models import Employee  # ✅ FIX 1

            decoded_file = file.read().decode('utf-8-sig').splitlines()  # ✅ FIX 3
            reader = csv.DictReader(decoded_file)

            # ✅ FIX 4
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            from datetime import datetime

            def parse_date(date_str):
                if not date_str:
                    return None
                try:
                    return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
                except:
                    return None

            created, failed, updated = 0, 0, 0
            
            for row in reader:
                try:
                    row = {k.strip(): (v.strip() if v else '') for k, v in row.items()}

                    pin = row.get("PIN")
                    name = row.get("Name")
                    designation = row.get("Designation")
                    salary = float(row.get("Salary") or 0)
                    start_date = parse_date(row.get("Start Date"))  # ✅ FIX 2
                    end_date = parse_date(row.get("End Date"))
                    contract_type = row.get("Contract Type") or "New"
                    new_designation = row.get("New Designation") or None
                    email = row.get("Email") or None
                    phone = row.get("Phone") or None
                    tin = row.get("TIN") or None
                    
                    if not pin:
                        failed += 1
                        continue
                    
                    employee, is_new = Employee.objects.get_or_create(pin=pin)
                    
                    if name:
                        employee.name = name
                    if designation:
                        employee.designation = designation
                    if salary:
                        employee.salary = salary
                    if email:
                        employee.email = email
                    if phone:
                        employee.phone = phone
                    if tin:
                        employee.tin = tin

                    employee.save()

                    if not is_new:
                        updated += 1
                    
                    Contract.objects.create(
                        pin=pin,
                        name=employee.name,
                        designation=designation or employee.designation,
                        salary=salary or employee.salary,
                        start_date=start_date,
                        end_date=end_date,
                        contract_type=contract_type,
                        new_designation=new_designation if contract_type == "Renewal" else None,
                    )

                    created += 1

                except Exception as e:
                    print(f"Row error: {e}")
                    failed += 1
            
            msg = f"{created} contracts created successfully!"
            if updated:
                msg += f" {updated} employees updated."
            messages.success(request, msg)

            if failed:
                messages.warning(request, f"{failed} rows failed!")

            return redirect("contracts:contract_list")

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f"Upload failed: {str(e)}")
    
    return render(request, "contracts/bulk_upload.html")


# =========================
# BULK EMAIL CONTRACTS
# =========================

@login_required
def bulk_email_contracts(request):
    if request.method == "POST":
        contract_ids = request.POST.get('contract_ids', '').split(',')
        subject = request.POST.get('subject', 'Contract Document')
        body = request.POST.get('body', '')

        if not contract_ids or not contract_ids[0]:
            messages.error(request, "No contracts selected!")
            return redirect('contract_list')

        base_url = request.build_absolute_uri('/')

        group_name = f"bulk_email_{request.user.id}_{int(time.time())}"
        request.session['bulk_email_group'] = group_name
        request.session['bulk_email_total'] = len(contract_ids)
        request.session['bulk_email_contract_ids'] = contract_ids
        request.session['bulk_email_started'] = time.time()
        request.session['bulk_email_finished'] = False

        for contract_id in contract_ids:
            async_task(
                'contracts.tasks.send_contract_email_task',
                contract_id, subject, body, base_url, group_name,
                group=group_name
            )

        return redirect('contracts:bulk_email_status')

    return redirect('contract_list')


# =========================
# BULK EMAIL STATUS
# =========================

@login_required
def bulk_email_status(request):
    from django_q.models import Success, Failure, Task

    group = request.session.get('bulk_email_group')
    total = request.session.get('bulk_email_total', 0)
    contract_ids = request.session.get('bulk_email_contract_ids', [])
    started = request.session.get('bulk_email_started', time.time())

    sent = 0
    failed = 0
    pending = total
    results = []

    if group and total > 0:
        success_qs = Success.objects.filter(group=group)
        failure_qs = Failure.objects.filter(group=group)
        sent = success_qs.count()
        failed = failure_qs.count()
        pending = total - sent - failed

        for s in success_qs.all()[:50]:
            result = s.result if isinstance(s.result, dict) else {}
            results.append({
                'contract_id': result.get('contract_id', '?'),
                'name': result.get('name', ''),
                'email': result.get('email', ''),
                'status': 'sent',
            })
        for f in failure_qs.all()[:10]:
            result = f.result if isinstance(f.result, dict) else {}
            results.append({
                'contract_id': result.get('contract_id', '?'),
                'name': result.get('name', ''),
                'email': result.get('email', ''),
                'status': 'failed',
                'reason': result.get('reason', str(f.result)[:200]),
            })

    finished = pending <= 0
    elapsed = round(time.time() - started, 1)

    if finished:
        request.session['bulk_email_finished'] = True

    return render(request, 'contracts/bulk_email_status.html', {
        'total': total,
        'sent': sent,
        'failed': failed,
        'pending': pending,
        'finished': finished,
        'results': results,
        'elapsed': elapsed,
        'group': group,
    })


# =========================
# DOWNLOAD CSV TEMPLATE
# =========================

@login_required
def download_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contract_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['PIN', 'Name', 'Designation', 'Salary', 'Start Date', 'End Date', 'Contract Type', 'Email', 'Phone', 'TIN', 'New Designation'])
    writer.writerow(['123', 'John Doe', 'Senior Analyst', '50000', '2025-07-01', '2026-06-30', 'Renewal', 'john@company.com', '01712345678', '123456789', 'Lead Analyst'])
    writer.writerow(['124', 'Jane Smith', 'Manager', '60000', '2025-07-01', '2026-06-30', 'Extension', 'jane@company.com', '01723456789', '987654321', ''])
    writer.writerow(['125', 'Alex Lee', 'Analyst', '45000', '2025-07-01', '2026-06-30', 'Revision', 'alex@company.com', '01734567890', '456789123', ''])
    
    return response


# =========================
# DELETE CONTRACT
# =========================

@login_required
def delete_contract(request, id):
    contract = get_object_or_404(Contract, id=id)

    if request.method == "POST":
        contract.delete()
        messages.success(request, "Contract deleted successfully.")
        return redirect('contracts_dashboard')

    return redirect('contracts_dashboard')


# =========================
# SEND CONTRACT VIA EMAIL
# =========================

@login_required
def send_contract_email(request, id):
    contract = get_object_or_404(Contract, id=id)
    
    # Auto-fill subject and body based on contract type
    if contract.contract_type == "Extension":
        default_subject = "Extension of contract letter"
        default_body = f"""Dear {contract.name},

I hope this email finds you well. Please find your extension of contract letter attached with this email.

You are requested to preserve a copy of the letter with yourself and send a copy to us via email with your signature in the letter.

Please let us know if any further information is required."""
    elif contract.contract_type == "Renewal":
        default_subject = "Renewal of contract"
        default_body = f"Please find attached the renewal contract for {contract.name} (PIN: {contract.pin}).\n\nContract Period: {contract.start_date} to {contract.end_date}\n\nBest regards,\nHR Department"
    elif contract.contract_type == "New":
        default_subject = "New Contract"
        default_body = f"Please find attached the new contract for {contract.name} (PIN: {contract.pin}).\n\nContract Period: {contract.start_date} to {contract.end_date}\n\nBest regards,\nHR Department"
    elif contract.contract_type == "Revision":
        default_subject = "Revision of contract"
        default_body = f"Please find attached the revised contract for {contract.name} (PIN: {contract.pin}).\n\nContract Period: {contract.start_date} to {contract.end_date}\n\nBest regards,\nHR Department"
    else:
        default_subject = "Contract Document"
        default_body = f"Please find attached the contract for {contract.name}."
    
    if request.method == "POST":
        subject = request.POST.get('subject', default_subject)
        body = request.POST.get('body', default_body)
        recipient = request.POST.get('recipient', '')
        
        if not recipient:
            messages.error(request, "Recipient email is required")
            return redirect('contracts:send_contract_email', id=id)
        
        try:
            # Use the same template logic as generate_pdf
            if contract.contract_type == "Renewal":
                template_name = "contracts/pdf/renewal.html"
            elif contract.contract_type == "Extension":
                template_name = "contracts/pdf/extension.html"
            elif contract.contract_type == "Revision":
                template_name = "contracts/pdf/revision.html"
            elif contract.contract_type == "New":
                template_name = "contracts/pdf/new.html"
            else:
                template_name = "contracts/pdf/new.html"
            
            html_string = render_to_string(
                template_name,
                {"contract": contract}
            )
            from weasyprint import HTML
            pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
            
            # Send email
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=EmailConfig.get_config().default_from_email,
                to=[recipient],
            )
            email.attach(f'contract_{contract.pin}_{contract.id}.pdf', pdf_file, 'application/pdf')
            email.send()

            EmailLog.objects.create(
                contract=contract,
                recipient_email=recipient,
                recipient_name=contract.name,
                subject=subject,
                status='sent',
            )

            messages.success(request, f"Email sent successfully to {recipient}!")
            return redirect('contract_list')
        except Exception as e:
            EmailLog.objects.create(
                contract=contract,
                recipient_email=recipient,
                recipient_name=contract.name,
                subject=subject,
                status='failed',
                error_message=str(e),
            )
            messages.error(request, f"Failed to send email: {str(e)}")
            return redirect('contracts:send_contract_email', id=id)
    
    # Try to get employee email
    employee_email = ''
    try:
        from employees.models import Employee
        employee = Employee.objects.filter(pin=contract.pin).first()
        if employee and employee.email:
            employee_email = employee.email
    except:
        pass
    
    # Pass default subject and body based on contract type
    return render(request, 'contracts/email_form.html', {
        'contract': contract,
        'employee_email': employee_email,
        'subject': default_subject,
        'body': default_body
    })


# =========================
# SYSTEM MANUAL
# =========================

@login_required
def system_manual(request):
    return render(request, 'contracts/manual.html')


# =========================
# EMAIL LOG
# =========================

@login_required
def email_log(request):
    from contracts.models import EmailLog

    logs = EmailLog.objects.all()[:200]
    return render(request, 'contracts/email_log.html', {'logs': logs})


# =========================
# EMAIL SETTINGS
# =========================

@login_required
def email_settings(request):
    from contracts.models import EmailConfig

    config = EmailConfig.get_config()

    if request.method == "POST":
        action = request.POST.get('action', 'save')

        if action == 'test':
            config.email_host = request.POST.get('email_host', '').strip()
            config.email_port = int(request.POST.get('email_port', 587))
            config.email_use_tls = request.POST.get('email_use_tls') == 'on'
            config.email_host_user = request.POST.get('email_host_user', '').strip()
            config.email_host_password = request.POST.get('email_host_password', '').strip()
            config.default_from_email = request.POST.get('default_from_email', '').strip()

            try:
                import smtplib
                server = smtplib.SMTP(config.email_host, config.email_port, timeout=10)
                if config.email_use_tls:
                    server.starttls()
                server.login(config.email_host_user, config.email_host_password)
                server.quit()
                messages.success(request, "Connection successful! SMTP server is reachable.")
            except Exception as e:
                messages.error(request, f"Connection failed: {str(e)}")

            return render(request, 'contracts/email_settings.html', {'config': config})

        config.email_host = request.POST.get('email_host', '').strip()
        config.email_port = int(request.POST.get('email_port', 587))
        config.email_use_tls = request.POST.get('email_use_tls') == 'on'
        config.email_host_user = request.POST.get('email_host_user', '').strip()
        config.email_host_password = request.POST.get('email_host_password', '').strip()
        config.default_from_email = request.POST.get('default_from_email', '').strip()
        config.save()

        messages.success(request, "Email settings saved successfully!")
        return redirect('contracts:email_settings')

    return render(request, 'contracts/email_settings.html', {'config': config})

