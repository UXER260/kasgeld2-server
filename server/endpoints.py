# TODO: Schrijf logout functie
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import FastAPI, Request, responses, status, HTTPException
from pydantic import BaseModel

from backend import AdminAuth, Functionality
from setup import load_config

app = FastAPI()

config = load_config()


class UserInfo(BaseModel):
    admin_name: str
    password: str


class MailInfo(BaseModel):
    receiver: str
    title: str
    text_body: str = None
    html_body: str = None


async def middleware(request: Request, next_call):
    # todo: validate ip
    ip = request.client.host
    ip_allowed_acces = AdminAuth.log_and_validate_ip(ip=ip)

    if not ip_allowed_acces:
        return responses.RedirectResponse(
            url="https://www.youtube.com/watch?v=oHg5SJYRHA0",
            status_code=status.HTTP_403_FORBIDDEN
        )
        # return responses.Response(status_code=status.HTTP_403_FORBIDDEN)
        # return responses.HTMLResponse(html.FORBIDDEN_PAGE)

    response = await next_call(request)

    # na manipuleer response
    # print(response)

    return response


app.middleware("http")(middleware)


# endpoints

@app.get("/")
@AdminAuth.auth_required
def home(request: Request):
    return {"detail": "logged in!"}


@app.get("/backend/add_account")
@AdminAuth.auth_required
def backend_add_account(admin_name: str, email: str, password: str, request: Request):
    AdminAuth.create_admin_account(admin_name=admin_name, email=email, password=password)
    # backend_login(email=email, password=password, request=request)
    return responses.Response(content=f"Successfully created account `{email}`", status_code=status.HTTP_200_OK)


@app.get("/backend/login")
def backend_login(email: str, password: str, request: Request):
    ip = request.client.host

    return AdminAuth.create_session(ip=ip, email=email, password=password)


#     ...


def send_email(mail_info: MailInfo):
    debug = {}

    receiver, title, text_body, html_body = (
        mail_info.receiver,
        mail_info.title,
        mail_info.text_body,
        mail_info.html_body
    )

    host, port, syst_addr, password = config["system_email"]["host"], config["system_email"]["port"], \
        config["system_email"]["addr"], config["system_email"]["pass"]

    msg = MIMEMultipart('alternative')
    msg["Subject"] = title
    msg["From"] = syst_addr
    msg["To"] = receiver

    if all([text_body, html_body]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You must either provide text or html content. Not both.")

    if html_body:
        print("HTML:", html_body)
        msg.attach(MIMEText(html_body, 'html'))
    else:
        print("TEXT:", text_body)
        msg.set_payload(text_body)

    smtp = smtplib.SMTP(host=host, port=port)

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
