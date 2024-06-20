# TODO: Schrijf logout functie

from fastapi import FastAPI, Request, responses, status, HTTPException

import backend
from setup import load_config

app = FastAPI()
config = load_config()


async def middleware(request: Request, next_call):
    # todo: validate ip
    ip = request.client.host
    ip_allowed_acces = backend.AdminAuth.log_and_validate_ip(ip=ip)

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
@backend.AdminAuth.auth_required
def home(request: Request):
    admin_id = backend.AdminAuth.admin_id_if_session_valid(ip=request.client.host)
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Dit zou niet moeten kunnen gebeuren...")

    name = backend.AdminAuth.admin_name_by_id(admin_id=admin_id)
    return f"Ingelogd als admin `{name}`!"


@app.post("/backend/add_account")
@backend.AdminAuth.auth_required
def backend_add_admin_account(admin_signup_info: backend.AdminSignupField, request: Request):
    backend.AdminAuth.create_admin_account(admin_signup_info=admin_signup_info)
    # backend_login(email=email, password=password, request=request)
    return responses.Response(content=f"Successfully created account", status_code=status.HTTP_200_OK)


@app.post("/backend/login")
def backend_admin_login(admin_login_info: backend.AdminLoginField, request: Request):
    return backend.AdminAuth.create_session(
        ip=request.client.host,
        admin_login_info=admin_login_info
    )

#     ...
