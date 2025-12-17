from flask_mail import Message
from flask import render_template, current_app
import os

def send_templated_email(subject, recipients, template_name, **kwargs):
    """
    Send an HTML email rendered from a Jinja template.
    Optional: attachment_path=<full path to PDF>.
    """
    # Get mail instance from current app context
    mail = current_app.extensions['mail']

    if isinstance(recipients, str):
        recipients = [recipients]

    msg = Message(
        subject=subject,
        recipients=recipients,
    )

    html_body = render_template(template_name, **kwargs)
    msg.html = html_body

    attachment_path = kwargs.get("attachment_path")
    if attachment_path:
        try:
            with open(attachment_path, "rb") as f:
                msg.attach(
                    filename=os.path.basename(attachment_path),
                    content_type="application/pdf",
                    data=f.read()
                )
        except Exception as e:
            print("Error attaching file:", e)

    mail.send(msg)
