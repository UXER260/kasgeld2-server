# De functie van deze module is het authenticeren van admins.

import sqlite3
from functools import wraps

from fastapi import responses, status, HTTPException

from setup import load_config

config = load_config()


class Functionality:
    # @classmethod
    # def
    ...


class AdminAuth:

    @classmethod  # Bedoeld als decorator functie. Voeg toe aan endpoint wanneer als admin ingelogd moet zijn.
    def auth_required(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = kwargs["request"].client.host
            print("ip:", ip)
            admin_id = cls.admin_id_if_session_valid(ip=ip)
            if type(admin_id) is int:
                return func(*args, **kwargs)
            else:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "You must be logged in to view or make changes.")

        return wrapper

    @classmethod
    def create_admin_account(cls, admin_name: str, email: str, password: str):
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()

            c.execute(
                f"""
                INSERT OR IGNORE INTO admins (admin_name, email, password, banned)
                VALUES ('{admin_name}', '{email}', '{password}', '0')
                """
            )
            conn.commit()
        return True

    @classmethod
    def admin_id_if_logged_in(cls, ip: str):  # Geeft het admin_id alleen wanneer de admin is ingelogd
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute(f"SELECT admin_id FROM logins WHERE ip_address='{ip}'")
            output = c.fetchone()
        if output is not None:
            return output[0]
        else:
            return False

    @classmethod
    def create_session(cls, ip: str, email: str, password: str):
        cls.validate_credentials(email=email, password=password)

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            admin_id = cls.admin_id_by_email(email=email)
            already_logged_in = cls.admin_id_if_session_valid(ip=ip)
            if already_logged_in is False:
                c.execute(f"INSERT INTO logins (ip_address, admin_id) VALUES ('{ip}', '{admin_id}')")
                conn.commit()
            else:
                print("ALREADY LOGGED IN")

        return responses.Response(content=f"Successfully logged `{email}` in", status_code=status.HTTP_200_OK)

    @classmethod
    def admin_account_is_banned(cls, admin_id):
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()

            c.execute(f"SELECT banned FROM admins WHERE admin_id='{admin_id}'")
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
            return False

        return admin_id

    @classmethod
    def admin_id_by_email(cls, email: str):
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute(f"SELECT admin_id FROM admins WHERE email='{email}'")
            output = c.fetchone()
        if output is None:
            return output
        else:
            return output[0]

    @classmethod
    def validate_credentials(cls, email: str, password: str):
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute(f"SELECT password, banned FROM admins WHERE email='{email}'")
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
        if password != correct_password:
            print("verkeerd wachtwoord")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)

        print("goed gekeurd!")
        return True

    @classmethod
    def log_and_validate_ip(cls, ip: str):
        with sqlite3.connect("database.db") as conn:
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
