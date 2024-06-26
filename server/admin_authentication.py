# De functie van deze module is het authenticeren van admins.
from functools import wraps

from main import *


# Bedoeld als decorator functie. Voeg toe aan endpoint wanneer als admin ingelogd moet zijn.
def auth_required(func):
    # (use_)optional_admin_login_info kan worden meegegeven voor het geval dat de #todo login is vervallen
    # dit kan benut worden om als client geen onverwachtse error responses terug te krijgen
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = kwargs["request"].client.host
        # json string "true" of "false" is al geconverteerd naar python bool `True` of `False`
        kwargs["use_optional_admin_login_info"] = kwargs["use_optional_admin_login_info"]
        admin_id = admin_id_if_login_valid(ip=ip, optional_admin_login_info=kwargs["optional_admin_login_info"],
                                           use_optional_admin_login_info=kwargs["use_optional_admin_login_info"])
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
    return responses.Response(status_code=status.HTTP_200_OK)


def logout_ip(ip: str):  # logt alleen op een specifiek IP uit
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(
            f"""
                DELETE FROM logins where ip_address="{ip}";
                """
        )
        conn.commit()
    return responses.Response(status_code=status.HTTP_200_OK)


def admin_name_by_id(admin_id) -> str | None:
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(
            f"""
            SELECT name FROM admins WHERE id="{admin_id}"
            """
        )
        output = c.fetchone()
    if output:
        return output[0]
    return None  # gebruiker bestaat niet


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
    return responses.Response(status_code=status.HTTP_200_OK)


def admin_id_by_login(ip: str) -> int | None:  # Geeft het admin_id alleen wanneer de admin is ingelogd
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(f"SELECT admin_id FROM logins WHERE ip_address='{ip}'")
        output = c.fetchone()
    if output:
        return output[0]
    print("kan id niet vinden omdat admin niet is ingelogd")
    return None


def create_login(ip: str, admin_login_info: AdminLoginField):  # login functie
    email = admin_login_info.email
    valid = validate_credentials(admin_login_info=admin_login_info)
    if valid is not True:
        return valid

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        # hoeft niet te checken of niet None omdat bestaan van account al is gecheckt bij
        # `valid = validate_credentials(admin_login_info=admin_login_info)` (aan begin van functie)
        admin_id = admin_id_by_email(email=email)
        already_logged_in = admin_id_by_login(ip=ip)
        if not already_logged_in:
            c.execute(f"INSERT INTO logins (ip_address, admin_id) VALUES ('{ip}', '{admin_id}')")
        else:
            print("ALREADY LOGGED IN")
        conn.commit()

    return responses.Response(content=f"Successfully login for`{email}`", status_code=status.HTTP_200_OK)


def check_admin_account_banned(admin_id):
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"SELECT banned FROM admins WHERE id='{admin_id}'")
        output = c.fetchone()

    if output:
        return output[0] == 1
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Admin met id `{admin_id}` bestaat niet")


def admin_id_if_login_valid(ip, optional_admin_login_info=None, use_optional_admin_login_info: bool = False):
    admin_id = admin_id_by_login(ip=ip)

    if not admin_id:  # als niet ingelogd
        if use_optional_admin_login_info is True:
            # (als niet is ingelogd of inlog is vervallen) MAAR er zijn inloggegevens meegegeven:
            create_login(ip=ip, admin_login_info=optional_admin_login_info)
        else:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                "You are not logged in as an admin. Your session could have expired.")
    else:
        banned = check_admin_account_banned(admin_id=admin_id)
        print("BANNED:", banned)
        if banned:
            raise HTTPException(status.HTTP_403_FORBIDDEN)
        # hoeft alleen te checken of is ge-banned als ingelogd is

    return admin_id


def admin_id_by_email(email: str) -> int | None:
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(f"SELECT id FROM admins WHERE email='{email}'")
        output = c.fetchone()

    if output:
        return output[0]
    return None


def validate_credentials(admin_login_info: AdminLoginField):
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(f"SELECT password, banned FROM admins WHERE email='{admin_login_info.email}'")
        output = c.fetchone()

    if output is None:  # wanneer het admin_account niet bestaat:
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
