import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from models_and_imports import *


class EmailField(BaseModel):
    receiver: str
    title: str
    text_body: str = None
    html_body: str = None


def send(mail: EmailField):
    #  voorbereiding
    debug = {}

    receiver, title, text_body, html_body = (
        mail.receiver,
        mail.title,
        mail.text_body,
        mail.html_body
    )

    if text_body and html_body:  # Mag alleen 1 van de twee in vullen. Niet beide.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You must either provide text or html content. Not both.")

    host, port, syst_addr, password = config["system_email"]["host"], config["system_email"]["port"], \
        config["system_email"]["addr"], config["system_email"]["pass"]

    msg = MIMEMultipart('alternative')
    msg["Subject"] = title
    msg["From"] = syst_addr
    msg["To"] = receiver

    if html_body:
        print("HTML:", html_body)
        msg.attach(MIMEText(html_body, 'html'))
    else:
        print("TEXT:", text_body)
        msg.set_payload(text_body)

    smtp = smtplib.SMTP(host=host, port=port)

    # verzend proces met debug
    debug["echlo"] = smtp.ehlo()
    print("echlo:", debug["echlo"])
    debug["tls"] = smtp.starttls()
    print("tls:", debug["tls"])
    debug["login"] = smtp.login(user=syst_addr, password=password)
    print("login:", debug["login"])
    debug["send"] = smtp.sendmail(from_addr=syst_addr, to_addrs=receiver, msg=msg.as_string())
    print("send!")

    smtp.quit()

    return debug
