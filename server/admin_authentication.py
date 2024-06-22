# De functie van deze module is het authenticeren van admins.

from functools import wraps
from main import *


# Bedoeld als decorator functie. Voeg toe aan endpoint wanneer als admin ingelogd moet zijn.
def auth_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = kwargs["request"].client.host
        print("ip:", ip)
        admin_id = admin_id_if_login_valid(ip=ip)
        if type(admin_id) is int:
            return func(*args, **kwargs)

    return wrapper


def logout_id(admin_id):  # logt overal op elk IP uit
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


def logout_ip(ip: str):  # logt alleen op een specifiek IP uit
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(
            f"""
                DELETE FROM logins where ip={ip};
                """
        )
        conn.commit()
    return True


def admin_name_by_id(admin_id):
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(
            f"""
            SELECT name FROM admins WHERE id="{admin_id}"
            """
        )
        output = c.fetchone()
        if not output:
            return None
        else:
            return output[0]


def create_admin_account(admin_signup_info: AdminSignupField):
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


def admin_id_by_login(ip: str) -> None | str:  # Geeft het admin_id alleen wanneer de admin is ingelogd
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(f"SELECT admin_id FROM logins WHERE ip_address='{ip}'")
        output = c.fetchone()
    if output is not None:
        return output[0]
    else:
        print("kan id niet vinden omdat admin niet is ingelogd")
        return None


def create_login(ip: str, admin_login_info: AdminLoginField):  # login functie
    email = admin_login_info.email
    valid = validate_credentials(admin_login_info=admin_login_info)
    if valid is not True:
        return valid

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        admin_id = admin_id_by_email(email=email)
        already_logged_in = admin_id_by_login(ip=ip)
        if not already_logged_in:
            c.execute(f"INSERT INTO logins (ip_address, admin_id) VALUES ('{ip}', '{admin_id}')")
            conn.commit()
        else:
            print("ALREADY LOGGED IN")

    return responses.Response(content=f"Successfully login for`{email}`", status_code=status.HTTP_200_OK)


def admin_account_is_banned(admin_id):
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"SELECT banned FROM admins WHERE id='{admin_id}'")
        output = c.fetchone()
        print(output)
        if output is not None:
            return output[0] == 1


def admin_id_if_login_valid(ip):
    admin_id = admin_id_by_login(ip=ip)
    if not admin_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "You must be logged in as an admin to view content or make changes.")
    banned = admin_account_is_banned(admin_id=admin_id)
    if banned:
        logout_id(admin_id=admin_id)
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    return admin_id


def admin_id_by_email(email: str):
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(f"SELECT id FROM admins WHERE email='{email}'")
        output = c.fetchone()
    if output is None:
        return output
    else:
        return output[0]


def validate_credentials(admin_login_info: AdminLoginField):
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


def log_and_validate_ip(ip: str):
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
