from contracts.models import Contract, EmailLog, EmailConfig
from employees.models import Employee
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def send_contract_email_task(contract_id, subject, body, base_url, batch_id=''):
    try:
        contract = Contract.objects.get(id=contract_id)

        employee = Employee.objects.filter(pin=contract.pin).first()
        if not employee or not employee.email:
            EmailLog.objects.create(
                contract=contract,
                recipient_email='',
                recipient_name=contract.name,
                subject=subject,
                status='failed',
                error_message='No email found',
                batch_id=batch_id,
            )
            return {
                'contract_id': contract_id,
                'status': 'failed',
                'reason': 'No email',
                'name': contract.name,
                'email': '',
            }

        if contract.contract_type == "Renewal":
            template_name = "contracts/pdf/renewal.html"
        elif contract.contract_type == "Extension":
            template_name = "contracts/pdf/extension.html"
        elif contract.contract_type == "Revision":
            template_name = "contracts/pdf/revision.html"
        else:
            template_name = "contracts/pdf/new.html"

        html_string = render_to_string(template_name, {"contract": contract})
        from weasyprint import HTML
        pdf_file = HTML(string=html_string, base_url=base_url).write_pdf()

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=EmailConfig.get_config().default_from_email,
            to=[employee.email],
        )
        email.attach(f'contract_{contract.pin}_{contract.id}.pdf', pdf_file, 'application/pdf')
        email.send()

        EmailLog.objects.create(
            contract=contract,
            recipient_email=employee.email,
            recipient_name=employee.name or contract.name,
            subject=subject,
            status='sent',
            batch_id=batch_id,
        )

        return {
            'contract_id': contract_id,
            'status': 'sent',
            'name': employee.name or contract.name,
            'email': employee.email,
        }

    except Exception as e:
        try:
            contract = Contract.objects.get(id=contract_id)
            EmailLog.objects.create(
                contract=contract,
                recipient_email='',
                recipient_name=contract.name,
                subject=subject,
                status='failed',
                error_message=str(e),
                batch_id=batch_id,
            )
        except Exception:
            pass
        return {'contract_id': contract_id, 'status': 'failed', 'reason': str(e)}
