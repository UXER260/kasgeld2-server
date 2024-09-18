# server/models_and_imports.py
# gecombineerde file voor gemene dependencies en pydantic models

from pydantic import BaseModel
import sqlite3
from fastapi import FastAPI, Request, Response, responses, status, HTTPException
import json


class AdminLoginField(BaseModel):
    email: str
    password: str


class AdminSignupField(BaseModel):
    name: str
    email: str
    password: str


class AddUser(BaseModel):
    name: str
    saldo: float


class RawUserData(BaseModel):  # voor data direct uit database
    user_id: int
    name: str
    saldo: float
    last_salary_update_timestamp: int
    creation_timestamp: int


class TransactionField(BaseModel):
    saldo_after_transaction: float
    title: str
    description: str


class RawTransactionData(BaseModel):
    transaction_id: int
    title: str
    description: str
    amount: float
    saldo_after_transaction: float
    transaction_timestamp: int
    user_id: int


DEFAULT_CONFIG = """  


{
  "host": "127.0.0.1",
  "port": 8000,
  "database_path": "database.db",
  "month_salary_blacklist": [7, 8],
  "salary_amount": 5,
  "session_expire_time_seconds": 43200,
  "banned_list_is_whitelist": false,

  "system_email": {
    "addr": "uxer260@outlook.com",
    "pass": "123@Ux3rz6o!",
    "host": "smtp-mail.outlook.com",
    "port": 587
  }
}


    """  # fallback


def load_config(path="config.json", default_config: str | dict = DEFAULT_CONFIG):
    print(path)
    try:
        with open(path) as f:
            conf = json.load(f)
    except FileNotFoundError as e:
        print(f"{e}\nRestoring {path}")

        # maakt nieuwe configfile aan als het niet te vinden is
        with open(path, "w") as f:
            json.dump(default_config, f) if type(default_config) is dict else f.write(default_config)
        conf = default_config if type(default_config) is dict else json.loads(default_config)

    print(f"Config at `{path}` loaded.")
    return conf


config = load_config()
