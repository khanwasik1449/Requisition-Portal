from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from payslip.models import Payslip
import csv


@login_required
def bulk_upload_payslip(request):
    if request.method == "POST":
        year = request.POST.get("year", "2025")
        file = request.FILES.get("file")
        
        if not file:
            messages.error(request, "No file uploaded! Please select a CSV file.")
            return render(request, "payslip/bulk_upload.html")
        
        try:
            decoded = file.read().decode("utf-8")
            reader = csv.reader(decoded.splitlines())
            
            next(reader, None)  # Skip header
            
            pin_mapping = {}
            employee_file = request.FILES.get("employee_file")
            if employee_file:
                emp_data = employee_file.read().decode("utf-8")
                emp_reader = csv.reader(emp_data.splitlines())
                next(emp_reader, None)
                for emp_row in emp_reader:
                    if len(emp_row) >= 4:
                        dummy_pin = emp_row[0].strip()
                        real_pin = emp_row[1].strip()
                        name = emp_row[2].strip()
                        designation = emp_row[3].strip() if len(emp_row) > 3 else "Staff"
                        pin_mapping[dummy_pin] = {'real_pin': real_pin, 'name': name, 'designation': designation}
            
            months = ["July", "August", "September", "October", "November", "December",
                    "January", "February", "March", "April", "May", "June"]
            
            created = 0
            failed = 0
            error_details = []
            
            for row_idx, row in enumerate(reader, start=2):  # Start from row 2 (after header)
                if len(row) < 4:
                    failed += 1
                    error_details.append(f"Row {row_idx}: Insufficient columns (need at least 4, got {len(row)})")
                    continue
                try:
                    dummy_pin = row[0].strip()
                    gender = row[1].strip() if len(row) > 1 else ""
                    tin = row[2].strip() if len(row) > 2 else ""
                    
                    emp_info = pin_mapping.get(dummy_pin, {})
                    real_pin = emp_info.get('real_pin', dummy_pin)
                    name = emp_info.get('name', f"Employee {real_pin}")
                    designation = emp_info.get('designation', "Staff")
                    
                    values = []
                    for i in range(3, 15):
                        v = row[i].replace(",", "").replace("BDT", "").strip() if i < len(row) else "0"
                        try:
                            values.append(int(float(v)))
                        except:
                            values.append(0)
                    
                    Payslip.objects.filter(pin=real_pin, year=year).delete()
                    
                    for idx, m in enumerate(months):
                        total = values[idx]
                        if total > 0:
                            Payslip.objects.create(
                                pin=real_pin, name=name, designation=designation,
                                gender=gender, tin=tin, month=m, year=year,
                                basic_salary=total * 0.50,
                                house_rent=total * 0.30,
                                medical_allowance=total * 0.10,
                                conveyance=total * 0.10,
                            )
                            created += 1
                except Exception as e:
                    failed += 1
                    error_details.append(f"Row {row_idx}: {str(e)}")
            
            if created > 0:
                messages.success(request, f"✅ {created} payslips uploaded successfully for year {year}!")
            
            if failed > 0:
                error_msg = f"⚠️ {failed} rows failed. "
                if error_details:
                    error_msg += "First 3 errors: " + "; ".join(error_details[:3])
                messages.warning(request, error_msg)
            
            return redirect("payslip:payslip_list")
        except Exception as e:
            messages.error(request, f"❌ Upload failed: {str(e)}")
    
    return render(request, "payslip/bulk_upload.html")