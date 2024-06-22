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


async def middleware(request: Request, next_call):
    # todo: validate ip
    ip = request.client.host
    ip_allowed_acces = log_and_validate_ip(ip=ip)

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


@app.get("/")
@admin_authentication.auth_required
def home(request: Request, optional_admin_login_info: None | AdminLoginField, use_optional_admin_login_info: bool):
    admin_id = admin_authentication.admin_id_if_login_valid(ip=request.client.host)
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="Dit zou niet moeten kunnen gebeuren...")

    name = admin_authentication.admin_name_by_id(admin_id=admin_id)
    if not name:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="?????????")
    return f"Ingelogd als admin `{name}`!"


# endpoints voor kasgeld functionaliteit

@app.post("/add_account_to_file")
def add_account_to_file(account_info: AccountData, request: Request):  # obvious
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


# endpoints voor admins
@app.post("/admin/add_account")
@admin_authentication.auth_required
def backend_add_admin_account(admin_signup_info: AdminSignupField, request: Request,
                              optional_admin_login_info: None | AdminLoginField, use_optional_admin_login_info=False):
    admin_authentication.create_admin_account(admin_signup_info=admin_signup_info)
    # backend_login(email=email, password=password, request=request)
    return responses.Response(content=f"Successfully created account", status_code=status.HTTP_200_OK)


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
    if admin_id is None:
        return responses.Response(status_code=status.HTTP_200_OK)
    return admin_authentication.logout_id(
        admin_id=admin_id
    )

#     ...
