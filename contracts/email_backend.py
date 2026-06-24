from django.core.mail.backends.smtp import EmailBackend

from contracts.models import EmailConfig


class DynamicEmailBackend(EmailBackend):
    def __init__(self, **kwargs):
        config = EmailConfig.get_config()

        host = kwargs.pop('host', None) or config.email_host
        port = kwargs.pop('port', None) or config.email_port
        username = kwargs.pop('username', None) or config.email_host_user
        password = kwargs.pop('password', None) or config.email_host_password
        use_tls = kwargs.pop('use_tls', config.email_use_tls)
        fail_silently = kwargs.pop('fail_silently', False)

        super().__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            fail_silently=fail_silently,
            **kwargs,
        )
