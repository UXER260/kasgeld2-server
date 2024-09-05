# server/main.py
import os

import uvicorn

import authentication
import kasgeld
import setup_db
import updater
from models_and_imports import *

setup_db.setup()

app = FastAPI()


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


async def middleware(request: Request, next_call):
    if not log_and_validate_ip(ip=request.client.host):
        # ip-adres is verbannen
        return responses.RedirectResponse("https://www.youtube.com/watch?v=oHg5SJYRHA0", status.HTTP_403_FORBIDDEN)

    # manage_login_expires()

    response = await next_call(request)

    # starlette.middleware.base._StreamingResponse
    print("HEADERS:", dict(response.headers))
    return response


app.middleware("http")(middleware)


@app.get("/")
@authentication.auth_required
def home(request: Request):
    admin_id = authentication.admin_id_by_session_ip(ip=request.client.host)
    name = authentication.admin_name_by_id(admin_id=admin_id)
    return f"Ingelogd als admin `{name}`!"


# endpoints voor kasgeld functionaliteit

@app.get("/get_userdata")
@authentication.auth_required
def get_userdata(request: Request, user_id: int):
    return kasgeld.get_raw_userdata(user_id=user_id)


@app.get("/get_userdata_by_username")
@authentication.auth_required
def get_userdata_by_username(request: Request, username: str):
    return kasgeld.get_raw_userdata(username=username)


@app.post("/add_user")
@authentication.auth_required
def add_user(request: Request, userdata: AddUser, transaction_made_timestamp: float = None):
    return kasgeld.add_user(userdata=userdata, transaction_made_timestamp=transaction_made_timestamp)


@app.delete("/delete_user")
@authentication.auth_required
def delete_user(request: Request, user_id: int, leave_transactions: bool = False):
    return kasgeld.delete_user(user_id=user_id, leave_transactions=leave_transactions)


@app.put("/set_saldo")
@authentication.auth_required
def set_saldo(request: Request, user_id: int, transaction_info: TransactionField,
              transaction_made_timestamp: float = None):
    kasgeld.set_saldo(user_id=user_id, transaction_info=transaction_info,
                      transaction_made_timestamp=transaction_made_timestamp)


@app.get("/get_username_list")
@authentication.auth_required
def get_username_list(request: Request, use_optional_admin_login_info: bool = False):
    return kasgeld.get_username_list()


@app.get("/get_transaction_list")
@authentication.auth_required
def get_transaction_list(request: Request, user_id):
    return kasgeld.get_transaction_list(user_id=user_id)


@app.get("/get_user_exists_by_id")
@authentication.auth_required
def get_user_exists_by_id(request: Request, user_id: int):
    return bool(kasgeld.username_if_exists(user_id=user_id))


@app.get("/get_user_exists_by_username")
@authentication.auth_required
def get_user_exists_by_username(request: Request, username: str):
    return bool(kasgeld.user_id_if_exists(username=username))


@app.get("/get_username_by_id")
@authentication.auth_required
def get_username_exists_by_id(request: Request, user_id: int):
    return kasgeld.username_if_exists(user_id=user_id)


@app.get("/get_user_id_by_username")
@authentication.auth_required
def get_user_id_by_username(request: Request, username: str):
    return kasgeld.user_id_if_exists(username=username)


@app.put("/rename_user")
@authentication.auth_required
def rename_user(request: Request, user_id: int, new_username: str):
    return kasgeld.rename_user(user_id=user_id, new_username=new_username)


# endpoints voor admins
@app.post("/add_admin")
@authentication.auth_required
def add_admin(request: Request, admin_signup_info: AdminSignupField,
              optional_admin_login_info: None | AdminLoginField,
              use_optional_admin_login_info: bool = False):
    authentication.create_admin_account(admin_signup_info=admin_signup_info)


@app.post("/login")
def login(request: Request, admin_login_info: AdminLoginField):
    return authentication.create_session(request=request, admin_login_info=admin_login_info)


@app.get("/logout")
def logout(request: Request):
    return authentication.logout_ip(ip=request.client.host)


@app.get("/global_logout")
def global_logout(request: Request):
    admin_id = authentication.admin_id_by_session_ip(ip=request.client.host)
    if admin_id is None:  # was al uitgelogd:
        return responses.Response(status_code=status.HTTP_200_OK)
    # fixme: voeg informatieve return text toe maar zorg ervoor dat cookie alsnog word verwijderd
    return authentication.logout_id(admin_id=admin_id)


# just for updating code
@app.get("/dev/update_and_reload")
def update_and_reload():
    updater.deploy_latest_update()


if __name__ == "__main__":
    setup_db.setup()
    uvicorn.run(app, host=config["host"], port=config["port"], log_level="info")
    # uvicorn.run("main:app", reload=True, host=config["host"], port=config["port"], log_level="info")
