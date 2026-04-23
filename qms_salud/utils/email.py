import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _config():
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", "")),
        "app_url": os.getenv("APP_URL", "http://localhost:8000"),
    }


def enviar_notificacion_acta(nombre: str, email_destino: str, numero_acta: str,
                              nombre_comite: str, token: str, comite_id: int, acta_id: int,
                              pdf_bytes: bytes = None, pdf_name: str = "Acta.pdf") -> bool:
    cfg = _config()
    if not cfg["host"] or not cfg["user"] or not email_destino:
        return False

    link = f"{cfg['app_url']}/comites/firmar?token={token}"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <div style="background:#1a56a0;padding:24px;text-align:center;">
        <h2 style="color:#fff;margin:0;font-size:18px;">QMS Salud</h2>
        <p style="color:rgba(255,255,255,0.8);margin:4px 0 0;font-size:13px;">Sistema de Gestión de Calidad</p>
      </div>
      <div style="padding:28px 32px;">
        <p style="font-size:15px;color:#111;">Hola, <strong>{nombre}</strong></p>
        <p style="color:#374151;font-size:14px;line-height:1.6;">
          Tienes un <strong>acta pendiente por validar y firmar</strong> en el sistema QMS Salud:
        </p>
        <div style="background:#f3f4f6;border-radius:8px;padding:16px 20px;margin:20px 0;">
          <p style="margin:0 0 6px;font-size:13px;color:#6b7280;">Comité</p>
          <p style="margin:0 0 14px;font-size:15px;font-weight:600;color:#111;">{nombre_comite}</p>
          <p style="margin:0 0 6px;font-size:13px;color:#6b7280;">Número de acta</p>
          <p style="margin:0;font-size:15px;font-weight:600;color:#1a56a0;">N° {numero_acta}</p>
        </div>
        <p style="color:#374151;font-size:14px;">
          Hemos adjuntado una copia del acta en formato PDF para tu revisión.<br><br>
          Haz clic en el botón a continuación para registrar tu firma (puedes firmar directamente desde la página usando una imagen o dibujándola):
        </p>
        <div style="text-align:center;margin:24px 0;">
          <a href="{link}"
             style="background:#1a56a0;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:600;display:inline-block;">
            ✍️ Revisar y firmar acta
          </a>
        </div>
        <p style="color:#9ca3af;font-size:12px;">
          Si el botón no funciona, copia este enlace en tu navegador:<br>
          <a href="{link}" style="color:#1a56a0;">{link}</a>
        </p>
      </div>
      <div style="background:#f9fafb;padding:14px 32px;text-align:center;border-top:1px solid #e5e7eb;">
        <p style="margin:0;font-size:11px;color:#9ca3af;">
          Desarrollado por <strong>Korex Solutions SAS</strong> · QMS Salud
        </p>
      </div>
    </div>
    """

    try:
        from email.mime.application import MIMEApplication
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📋 Acta pendiente por firmar — {nombre_comite} N° {numero_acta}"
        msg["From"] = cfg["from"]
        msg["To"] = email_destino
        msg.attach(MIMEText(html, "html"))

        if pdf_bytes:
            pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_name)
            msg.attach(pdf_attachment)

        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from"], email_destino, msg.as_string())
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False
