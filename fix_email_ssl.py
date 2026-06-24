# fix_email_ssl.py
with open('app/services/email_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(
                    settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                    to_email,
                    msg.as_string(),
                )'''

new = '''            # Для SSL (порт 465) используем SMTP_SSL, для STARTTLS (587) — SMTP + starttls
            if settings.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(
                        settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                        to_email,
                        msg.as_string(),
                    )
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    if settings.SMTP_TLS:
                        server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(
                        settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                        to_email,
                        msg.as_string(),
                    )'''

if old in content:
    content = content.replace(old, new)
    with open('app/services/email_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SSL support added!")
else:
    print("ERROR")
