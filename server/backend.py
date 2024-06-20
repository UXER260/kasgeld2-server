# De functie van deze module is het authenticeren van admins.

import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

from fastapi import responses, status, HTTPException
from pydantic import BaseModel

from setup import load_config

config = load_config()


class AdminLoginField(BaseModel):
    email: str
    password: str


class AdminSignupField(BaseModel):
    name: str
    email: str
    password: str


class EmailField(BaseModel):
    receiver: str
    title: str
    text_body: str = None
    html_body: str = None


class Functionality:
    def __init__(self):
        pass

    # @classmethod
    # def

    ...


class AdminAuth:
    def __init__(self):
        pass

    @classmethod  # Bedoeld als decorator functie. Voeg toe aan endpoint wanneer als admin ingelogd moet zijn.
    def auth_required(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = kwargs["request"].client.host
            print("ip:", ip)
            admin_id = cls.admin_id_if_session_valid(ip=ip)
            # if type(admin_id) is dict:
            #     AdminAuth.logout_id(admin_id=admin_id["banned"]["id"])
            #     raise HTTPException(status.HTTP_403_FORBIDDEN)
            # el \
            if type(admin_id) is int:
                return func(*args, **kwargs)
            else:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                    "You must be logged in as an admin to view content or make changes.")

        return wrapper

    @classmethod
    def logout_id(cls, admin_id):  # logt overal op elk IP uit
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            print("ADMIN_ID:", admin_id)
            c.execute(
                f"""
                DELETE FROM logins where admin_id={admin_id};
                """
            )
            conn.commit()
        return True

    @classmethod
    def logout_ip(cls, ip: str):  # logt alleen op een specifiek IP uit
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute(
                f"""
                    DELETE FROM logins where ip={ip};
                    """
            )
            conn.commit()
        return True

    @classmethod
    def admin_name_by_id(cls, admin_id):
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute(
                f"""
                SELECT name FROM admins WHERE id="{admin_id}"
                """
            )
            output = c.fetchone()
            if not output:
                return False
            else:
                return output[0]

    @classmethod
    def create_admin_account(cls, admin_signup_info: AdminSignupField):
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute(
                f"""
                INSERT OR IGNORE INTO admins (name, email, password, banned)
                VALUES ("{admin_signup_info.name}", "{admin_signup_info.email}", "{admin_signup_info.password}", '0')
                """
            )
            conn.commit()
        return True

    @classmethod
    def admin_id_if_logged_in(cls, ip: str):  # Geeft het admin_id alleen wanneer de admin is ingelogd
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute(f"SELECT admin_id FROM logins WHERE ip_address='{ip}'")
            output = c.fetchone()
        if output is not None:
            return output[0]
        else:
            return False

    @classmethod
    def create_session(cls, ip: str, admin_login_info: AdminLoginField):  # login functie
        email = admin_login_info.email
        valid = cls.validate_credentials(admin_login_info=admin_login_info)
        if valid is not True:
            return valid

        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            admin_id = cls.admin_id_by_email(email=email)
            already_logged_in = cls.admin_id_if_session_valid(ip=ip)
            if not already_logged_in:
                c.execute(f"INSERT INTO logins (ip_address, admin_id) VALUES ('{ip}', '{admin_id}')")
                conn.commit()
            else:
                print("ALREADY LOGGED IN")

        return responses.Response(content=f"Successfully login for`{email}`", status_code=status.HTTP_200_OK)

    @classmethod
    def admin_account_is_banned(cls, admin_id):
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()

            c.execute(f"SELECT banned FROM admins WHERE id='{admin_id}'")
            output = c.fetchone()
            print(output)
            if output is not None:
                return output[0] == 1

    @classmethod
    def admin_id_if_session_valid(cls, ip):
        admin_id = cls.admin_id_if_logged_in(ip=ip)
        if admin_id is False:
            return False
        banned = cls.admin_account_is_banned(admin_id=admin_id)
        if banned:
            return {"banned": {"id": admin_id, "ip": ip}}

        return admin_id

    @classmethod
    def admin_id_by_email(cls, email: str):
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute(f"SELECT id FROM admins WHERE email='{email}'")
            output = c.fetchone()
        if output is None:
            return output
        else:
            return output[0]

    @classmethod
    def validate_credentials(cls, admin_login_info: AdminLoginField):
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute(f"SELECT password, banned FROM admins WHERE email='{admin_login_info.email}'")
            output = c.fetchone()

        if output is None:  # wanneer het admin_account niet bestaat
            print("admin_account bestaat niet")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)

        correct_password, banned = output
        banned = banned == 1
        banned = banned if not config["banned_list_is_whitelist"] else (not banned)
        if banned:
            print("admin_account is verbannen")
            raise HTTPException(status.HTTP_403_FORBIDDEN)
        if admin_login_info.password != correct_password:
            print("verkeerd wachtwoord")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)

        print("goed gekeurd!")
        return True

    @classmethod
    def log_and_validate_ip(cls, ip: str):
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute(f"SELECT request_count, banned from ips WHERE ip_address='{ip}'")
            data = c.fetchone()

            if data:
                request_count, banned = data
                banned = banned == 1
                banned = banned if not config["banned_list_is_whitelist"] else (not banned)
                if not banned:
                    c.execute(f"UPDATE ips SET request_count={request_count + 1} WHERE ip_address='{ip}';")
                    conn.commit()
                    return True
                else:
                    return False
            else:
                c.execute(f"INSERT INTO ips (ip_address, request_count, banned) VALUES ('{ip}', 1, 0)")
                conn.commit()
                return True


class Email:
    def __init__(self, email_field: EmailField):
        self.receiver = email_field.receiver
        self.title = email_field.title
        self.text_body = email_field.text_body
        self.html_body = email_field.html_body

    def send(self):
        #  voorbereiding
        debug = {}

        receiver, title, text_body, html_body = (
            self.receiver,
            self.title,
            self.text_body,
            self.html_body
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
