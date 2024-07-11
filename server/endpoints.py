# TODO: Schrijf logout functie

import admin_authentication
from main import *

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


def manage_login_expires():
    with open(config["last_session_wipe_path"]) as f:
        last_session_wipe = json.load(f)

    time_since_session_wipe = int(time.time()) - last_session_wipe["timestamp"]
    print(f"time_since last session wipe: {time_since_session_wipe}/{config['session_expire_time_seconds']} seconds")
    if abs(time_since_session_wipe) > config["session_expire_time_seconds"]:  # is langer dan vervaltijd ingelogd:

        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM logins;")  # delete alle sessies

        with open(config["last_session_wipe_path"], 'w') as f:
            last_session_wipe["timestamp"] = int(time.time())
            print(last_session_wipe)
            json.dump(last_session_wipe, f)

        print("wiped all logins")


async def middleware(request: Request, next_call):
    if not log_and_validate_ip(ip=request.client.host):
        # ip-adres is verbannen
        return responses.RedirectResponse("https://www.youtube.com/watch?v=oHg5SJYRHA0", status.HTTP_403_FORBIDDEN)

    manage_login_expires()

    response = await next_call(request)

    # starlette.middleware.base._StreamingResponse
    print("HEADERS:", dict(response.headers))
    return response


app.middleware("http")(middleware)


@app.post("/")
@admin_authentication.auth_required
def home(request: Request, optional_admin_login_info: None | AdminLoginField,
         use_optional_admin_login_info: bool = False):
    admin_id = admin_authentication.admin_id_if_login_valid(ip=request.client.host)
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="Dit zou niet moeten kunnen gebeuren...")

    name = admin_authentication.admin_name_by_id(admin_id=admin_id)
    if not name:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="?????????")
    return f"Ingelogd als admin `{name}`!"


# endpoints voor kasgeld functionaliteit

@app.get("/get_userdata")
def get_userdata(user_id: int):
    return backend.get_raw_userdata(user_id=user_id)


@app.get("/get_userdata_by_username")
def get_userdata_by_username(username: str):
    return backend.get_raw_userdata(username=username)


@app.post("/add_user")
def add_user(request: Request, userdata: AddUser, transaction_made_timestamp: float = None):
    return backend.add_user(userdata=userdata, transaction_made_timestamp=transaction_made_timestamp)


@app.delete("/delete_user")
def delete_user(user_id: int, leave_transactions: bool = False):
    return backend.delete_user(user_id=user_id, leave_transactions=leave_transactions)


@app.put("/set_saldo")
def set_saldo(user_id: int, transaction_info: TransactionField, transaction_made_timestamp: float = None):
    backend.set_saldo(user_id=user_id, transaction_info=transaction_info,
                      transaction_made_timestamp=transaction_made_timestamp)


@app.get("/get_username_list")
# @admin_authentication.auth_required
def get_username_list(request: Request, use_optional_admin_login_info: bool = False):
    return backend.get_username_list()


@app.get("/get_transaction_list")
def get_transaction_list(user_id, request: Request):
    return backend.get_transaction_list(user_id=user_id)


@app.get("/get_user_exists_by_id")
def get_user_exists_by_id(user_id: int, request: Request):
    return bool(backend.username_if_exists(user_id=user_id))


@app.get("/get_user_exists_by_username")
def get_user_exists_by_username(username: str, request: Request):
    return bool(backend.user_id_if_exists(username=username))


@app.get("/get_username_by_id")
def get_username_exists_by_id(user_id: int, request: Request):
    return backend.username_if_exists(user_id=user_id)


@app.get("/get_user_id_by_username")
def get_user_id_by_username(username: str, request: Request):
    return backend.user_id_if_exists(username=username)


@app.put("/rename_user")
def rename_user(request: Request, user_id: int, new_username: str):
    return backend.rename_user(user_id=user_id, new_username=new_username)


# endpoints voor admins
@app.post("/admin/add_user")
@admin_authentication.auth_required
def backend_add_admin_user(admin_signup_info: AdminSignupField, request: Request,
                           optional_admin_login_info: None | AdminLoginField,
                           use_optional_admin_login_info: bool = False):
    admin_authentication.create_admin_account(admin_signup_info=admin_signup_info)
    # backend_login(email=email, password=password, request=request)
    return responses.Response(content=f"Successfully created user", status_code=status.HTTP_200_OK)


@app.post("/admin/login")
def backend_admin_login(admin_login_info: AdminLoginField, request: Request):
    return admin_authentication.create_login(
        ip=request.client.host,
        admin_login_info=admin_login_info
    )


@app.get("/admin/logout")
def backend_admin_login(request: Request):
    return admin_authentication.logout_ip(ip=request.client.host)


@app.get("/admin/global_logout")
def backend_admin_login(request: Request):
    admin_id = admin_authentication.admin_id_by_login(ip=request.client.host)
    if admin_id is None:  # was al uitgelogd:
        return responses.Response(status_code=status.HTTP_200_OK)
    return admin_authentication.logout_id(
        admin_id=admin_id
    )
