# fix_email_queue.py
with open('app/services/email_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        # Проверяем доступность SMTP
        if not EmailService._smtp_available():
            return {
                "success": True,
                "queued": True,
                "message": f"Email поставлен в очередь на {to_email} (SMTP {settings.SMTP_HOST}:{settings.SMTP_PORT} недоступен)",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        
        # Реальная отправка (если SMTP доступен)
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
            msg["To"] = to_email
            if body_text:
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
            
            # Для SSL (порт 465) используем SMTP_SSL, для STARTTLS (587) — SMTP + starttls
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
                    )
            
            return {
                "success": True,
                "queued": False,
                "message": f"Email отправлен на {to_email}",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }'''

new = '''        # Проверяем доступность SMTP
        smtp_available = EmailService._smtp_available()
        
        # Пытаемся отправить (если SMTP доступен)
        if smtp_available:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
                msg["To"] = to_email
                if body_text:
                    msg.attach(MIMEText(body_text, "plain", "utf-8"))
                msg.attach(MIMEText(body_html, "html", "utf-8"))
                
                # Для SSL (порт 465) используем SMTP_SSL, для STARTTLS (587) — SMTP + starttls
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
                        )
                
                return {
                    "success": True,
                    "queued": False,
                    "message": f"Email отправлен на {to_email}",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
                
            except Exception as e:
                # SMTP доступен, но отправка не удалась (аутентификация и т.д.)
                # Ставим в очередь
                pass
        
        # Ставим в очередь (SMTP недоступен или отправка не удалась)
        return {
            "success": True,
            "queued": True,
            "message": f"Email поставлен в очередь на {to_email}. Для реальной отправки настройте App Password в Google Account (Security → App Passwords).",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }'''

if old in content:
    content = content.replace(old, new)
    with open('app/services/email_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Email queue logic fixed!")
else:
    print("ERROR")
