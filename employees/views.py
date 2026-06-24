from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from employees.models import Employee
from contracts.models import Contract
from django.http import JsonResponse
import csv


@login_required
def employee_list(request):
    employees = Employee.objects.all().order_by('pin')
    
    # Get contract history for each employee
    employee_data = []
    for emp in employees:
        contracts = Contract.objects.filter(pin=emp.pin).order_by('-created_at')
        emp.contracts = contracts
        emp.new_count = contracts.filter(contract_type='New').count()
        emp.extension_count = contracts.filter(contract_type='Extension').count()
        emp.revision_count = contracts.filter(contract_type='Revision').count()
        emp.renewal_count = contracts.filter(contract_type='Renewal').count()
        employee_data.append(emp)
    
    return render(request, "employees/list.html", {"employees": employee_data})


@login_required
def add_employee(request):
    if request.method == "POST":
        designation = request.POST.get("designation", "").strip()
        email = request.POST.get("email", "").strip()

        errors = []
        if not designation:
            errors.append("Designation is required.")
        if not email:
            errors.append("Email address is required.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "employees/add.html", {
                'form_data': request.POST,
            })

        Employee.objects.create(
            pin=request.POST.get("pin"),
            name=request.POST.get("name"),
            designation=designation,
            gender=request.POST.get("gender") or None,
            tin=request.POST.get("tin") or None,
            phone=request.POST.get("phone") or None,
            email=email,
            salary=request.POST.get("salary") or 0,
        )
        messages.success(request, "Employee added successfully!")
        return redirect("employees:employee_list")
    return render(request, "employees/add.html")


@login_required
def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        designation = request.POST.get("designation", "").strip()
        email = request.POST.get("email", "").strip()

        errors = []
        if not designation:
            errors.append("Designation is required.")
        if not email:
            errors.append("Email address is required.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "employees/edit.html", {
                'employee': employee,
                'form_data': request.POST,
            })

        employee.pin = request.POST.get("pin")
        employee.name = request.POST.get("name")
        employee.designation = designation
        employee.gender = request.POST.get("gender") or None
        employee.tin = request.POST.get("tin") or None
        employee.phone = request.POST.get("phone") or None
        employee.email = email
        employee.salary = request.POST.get("salary") or 0
        employee.save()
        messages.success(request, "Employee updated successfully!")
        return redirect("employees:employee_list")

    return render(request, "employees/edit.html", {"employee": employee})


@login_required
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == "POST":
        # Delete all contracts associated with this employee's PIN
        from contracts.models import Contract
        Contract.objects.filter(pin=employee.pin).delete()
        
        employee.delete()
        messages.success(request, "Employee and all related contracts deleted successfully!")
        return redirect("employees:employee_list")
    
    return render(request, "employees/delete.html", {"employee": employee})


@login_required
def import_employees(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        
        if not file:
            messages.error(request, "No file uploaded!")
            return render(request, "employees/import.html")
        
        try:
            decoded = file.read().decode("utf-8")
            reader = csv.reader(decoded.splitlines())
            
            next(reader, None)
            
            created = 0
            failed = 0
            
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    pin = row[0].strip()
                    name = row[1].strip()
                    designation = row[2].strip() if len(row) > 2 else "Staff"
                    gender = row[3].strip() if len(row) > 3 else ""
                    tin = row[4].strip() if len(row) > 4 else ""
                    phone = row[5].strip() if len(row) > 5 else ""
                    email = row[6].strip() if len(row) > 6 else ""
                    salary = row[7].strip() if len(row) > 7 else 0
                    
                    Employee.objects.update_or_create(
                        pin=pin,
                        defaults={
                            'name': name,
                            'designation': designation,
                            'gender': gender,
                            'tin': tin,
                            'phone': phone,
                            'email': email,
                            'salary': salary,
                        }
                    )
                    created += 1
                except Exception:
                    failed += 1
            
            messages.success(request, f"{created} employees imported!")
            if failed:
                messages.warning(request, f"{failed} rows failed")
            return redirect("employees:employee_list")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return render(request, "employees/import.html")

@login_required
def employee_api(request, pin):
    try:
        emp = Employee.objects.get(pin=pin)
        return JsonResponse({
            'exists': True,
            'name': emp.name,
            'designation': emp.designation,
            'salary': float(emp.salary) if emp.salary else 0,
            'phone': emp.phone or '',
            'email': emp.email or '',
            'tin': emp.tin or '',
        })
    except Employee.DoesNotExist:
        return JsonResponse({'exists': False})


@login_required
def employee_detail(request, pin):
    employee = get_object_or_404(Employee, pin=pin)
    contracts = Contract.objects.filter(pin=pin).order_by('-start_date')
    
    return render(request, "employees/detail.html", {
        "employee": employee,
        "contracts": contracts
    })