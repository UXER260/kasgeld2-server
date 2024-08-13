# server/authentication.py
# De functie van deze module is het authenticeren van admins.

import hashlib
import time
from functools import wraps
from cryptography import fernet

from models_and_imports import *


def auth_required(func):  # Bedoeld als decorator functie. Voeg toe aan endpoint wanneer als admin ingelogd moet zijn.
    @wraps(func)
    def wrapper(*args, **kwargs):
        valid = session_valid(
            request=kwargs["request"],
            optional_admin_login_info=kwargs.get("optional_admin_login_info"),
            use_optional_admin_login_info=kwargs.get("use_optional_admin_login_info")
        )
        if valid is True:
            return func(*args, **kwargs)

    return wrapper


def create_hash(plain_text: str):  # Maakt hash aan
    return hashlib.sha512(plain_text.encode()).hexdigest()


def remove_session_token(response: Response):  # Verwijderd sessie token van client
    response.set_cookie(key="session_token", value="")


def logout_id(admin_id, response: Response = None):  # Logt overal op elk IP uit
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE admin_id=?", (admin_id,))
        conn.commit()
    if not response:
        response = Response(status_code=status.HTTP_200_OK)
    remove_session_token(response=response)
    return response


def logout_ip(ip: str, response: Response = None):  # Logt alleen op een specifiek IP uit
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE ip_address=?", (ip,))
        conn.commit()

    if not response:
        response = Response(status_code=status.HTTP_200_OK)
    remove_session_token(response=response)
    return response


def admin_name_by_id(admin_id) -> str | None:  # Verkrijgt admin naam met admin id
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM admins WHERE id=?", (admin_id,))
        output = c.fetchone()
    if output:
        return output[0]
    return None  # gebruiker bestaat niet


def create_admin_account(admin_signup_info: AdminSignupField):  # Creëert een admin account
    hashed_password = create_hash(admin_signup_info.password)  # Bewaar hashed versie van wachtwoord
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO admins (name, email, hashed_password, banned)
            VALUES (?, ?, ?, 0)
        """, (admin_signup_info.name, admin_signup_info.email, hashed_password))
        conn.commit()
    return responses.Response(status_code=status.HTTP_200_OK)


def admin_id_by_session_ip(ip: str) -> int | None:  # Geeft het admin_id alleen wanneer de admin is ingelogd
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT admin_id FROM sessions WHERE ip_address = ?", (ip,))
        output = c.fetchone()
    if output:
        return output[0]
    print("kan id niet vinden omdat admin niet is ingelogd")
    return None


def validate_session_token(admin_id: int, session_token: str):  # Valideert een sessie token
    if not session_token:
        return False

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT token, creation_timestamp FROM sessions WHERE admin_id = ?", (admin_id,))
        output = c.fetchone()

    if not output:  # sessie bestaat niet
        print("Geen output")
        return False

    token_in_db = output[0]
    token_in_db_creation_timestamp = output[1]
    if session_token != token_in_db:  # token komt niet overeen
        print("Incorrecte token")
        return False

    token_used_seconds = time.time() - token_in_db_creation_timestamp
    if token_used_seconds < 0:  # Dit kan gebeuren wanneer de gebruiker de tijd heeft verzet
        print("Ongeldige tijd")
        return False
    if token_used_seconds > config["session_expire_time_seconds"]:  # De token is verlopen
        print("Token verlopen")
        return False

    return True


def create_session(request: Request, admin_login_info: AdminLoginField):  # Login functie

    admin_id = admin_id_by_email(admin_login_info.email)
    if not admin_id:  # admin bestaat niet
        print(f"admin {admin_login_info.email} bestaat niet")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    banned = check_admin_account_banned(admin_id=admin_id)
    if banned:  # admin is verbannen
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    already_logged_in = bool(admin_id_by_session_ip(request.client.host))

    current_token = request.cookies.get("session_token")
    current_token_valid = validate_session_token(admin_id=admin_id, session_token=current_token)
    if current_token_valid:  # sessie is al geldig
        return current_token

    valid_normal_credentials = validate_normal_credentials(admin_login_info=admin_login_info)
    if callable(valid_normal_credentials):  # lambda function met exception is ge-returned
        raise valid_normal_credentials()  # Credentials waren niet geldig

    new_session_token = generate_session_token()

    if not already_logged_in:
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO sessions (ip_address, admin_id, token) VALUES (?, ?, ?)",
                      (request.client.host, admin_id, new_session_token))
            conn.commit()

    else:
        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            # Vervang sessie
            c.execute("DELETE FROM sessions WHERE admin_id = ?", (admin_id,))
            conn.commit()
            c.execute("INSERT INTO sessions (token, admin_id, ip_address) VALUES (?, ?, ?)",
                      (new_session_token, admin_id, request.client.host))
            conn.commit()
            print("Al ingelogd. Session token hernieuwd")

    response = Response(content=f"Succesvolle login for`{admin_login_info.email}`", status_code=status.HTTP_200_OK)
    response.set_cookie(key="session_token", value=new_session_token)
    return response


def check_admin_account_banned(admin_id):  # Checkt of admin account is verbannen
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"SELECT banned FROM admins WHERE id='{admin_id}'")
        output = c.fetchone()

    if output:
        return output[0] == 1
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Admin met id `{admin_id}` bestaat niet")


def session_valid(request: Request, optional_admin_login_info=None,
                  use_optional_admin_login_info: bool = False):
    admin_id = admin_id_by_session_ip(request.client.host)  # Checkt of een sessie geldig is

    if admin_id:
        banned = check_admin_account_banned(admin_id=admin_id)
        if banned:  # admin is verbannen
            raise HTTPException(status.HTTP_403_FORBIDDEN)

    current_token_valid = validate_session_token(admin_id=admin_id, session_token=request.cookies.get("session_token"))
    current_session_valid = admin_id and current_token_valid
    if current_session_valid:  # sessie is geldig
        return True

    # als sessie token niet geldig is
    # dan probeert programma met optionele inlog info in te loggen
    if use_optional_admin_login_info is True and optional_admin_login_info:
        create_session(request=request, admin_login_info=optional_admin_login_info)
        return True
    else:
        # als dat niet beschikbaar is:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "You are not logged in as an admin. Your session could have expired.")


def admin_id_by_email(email: str) -> int | None:  # Verkrijgt admin id met bijbehorend email
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM admins WHERE email=?", (email,))
        output = c.fetchone()

    if output:
        return output[0]
    return None


def generate_session_token():  # Genereert sessie token
    return fernet.Fernet.generate_key()


def validate_normal_credentials(admin_login_info: AdminLoginField):  # Checkt of email en wachtwoord geldig zijn
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT hashed_password, banned FROM admins WHERE email=?", (admin_login_info.email,))
        output = c.fetchone()

    if output is None:  # wanneer het admin_account niet bestaat:
        return lambda: HTTPException(status.HTTP_401_UNAUTHORIZED,
                                     detail=f"Admin account met email `{admin_login_info.email}` bestaat niet")

    correct_hashed_password, banned = output
    banned = banned == 1
    banned = banned if not config["banned_list_is_whitelist"] else (not banned)
    if banned:  # Account is verbannen
        print("admin_account is verbannen")
        return lambda: HTTPException(status.HTTP_403_FORBIDDEN)
        # raise HTTPException(status.HTTP_403_FORBIDDEN)

    hashed_password = create_hash(admin_login_info.password)
    if hashed_password != correct_hashed_password:  # verkeerd wachtwoord
        print("verkeerd wachtwoord")
        return lambda: HTTPException(status.HTTP_401_UNAUTHORIZED)

    print("goed gekeurd!")
    return True
