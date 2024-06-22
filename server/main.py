import json
from pydantic import BaseModel
import sqlite3
from fastapi import FastAPI, Request, responses, status, HTTPException


class AdminLoginField(BaseModel):
    email: str
    password: str


class AdminSignupField(BaseModel):
    name: str
    email: str
    password: str


class AccountData(BaseModel):
    ...


def load_config(path="config.json"):
    try:
        with open(path) as f:
            conf = json.load(f)
    except FileNotFoundError as e:
        print(f"{e}\nRestoring {path}")

        # maakt nieuwe configfile aan als het niet te vinden is
        with open(path, "w") as f:
            f.write(DEFAULT_CONFIG)
        conf = json.loads(DEFAULT_CONFIG)

    # print(f"Config at `{path}` loaded.")
    return conf


config = load_config()

if __name__ == "__main__":
    import uvicorn

    import setup_db
    import endpoints

    DEFAULT_CONFIG = """  

    {
      "host": "0.0.0.0",
      "port": 8000,
      "accounts_path": "accounts.db",
      "month_salary_blacklist": [7, 8],
      "salary_amount": 5,

      "banned_list_is_whitelist": false,∑∑

      "system_email": {
        "addr": "uxer260@outlook.com",
        "pass": "123@Ux3rz6o!",
        "host": "smtp-mail.outlook.com",
        "port": 587
      }
    }

    """  # fallback

    setup_db.setup()

    uvicorn.run(endpoints.app, host=config["host"], port=config["port"], log_level="info")
