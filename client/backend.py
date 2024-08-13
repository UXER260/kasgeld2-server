# client/backend.py
# Bevat alle functies voor communicatie met server

# Van ~/PycharmProjects/PythonProjects/BankKasGeldSchool/api/client/old4_fail/bank.py

import copy
import sys

import PySimpleGUI as pysgui

import requests

from models import *
from pathlib import Path

import json

with open('config.json', 'r') as f:
    config = json.load(f)

session = requests.session()

# to save cookies:
# cookies = requests.utils.dict_from_cookiejar(session.cookies)  # turn cookiejar into dict
# Path("cookies.json").write_text(json.dumps(cookies))  # save them to file as JSON

# to retrieve cookies:
cookies = json.loads(Path("cookies.json").read_text())  # save them to file as JSON
cookies = requests.utils.cookiejar_from_dict(cookies)  # turn dict to cookiejar
session.cookies.update(cookies)  # load cookiejar to current session


def default_font(scale: float = 1, font_type: str = None):
    return " ".join((
        config["font"][0] if not font_type else font_type,
        str(int(config["font"][1] * scale))
    ))


def check_string_valid_float(string: str):
    try:
        return float(string)
    except ValueError:
        return False


def check_valid_saldo(saldo: float):
    if -7320 > float(saldo) or float(saldo) > 7320:
        pysgui.popup("Houd u dat bedrag eventjes realistisch?", font=config["font"], keep_on_top=True,
                     title="Fout")
        return False
    return True


class User:

    @staticmethod
    def get_user_exists_by_username(username: str):
        response = session.get(config["request_url"] + "get_user_exists_by_username", params={"username": username})
        return response.json()

    @staticmethod
    def get_user_exists_by_id(user_id: int):
        return session.get(config["request_url"] + "get_user_exists_by_id", params={"user_id": user_id}).json()

    @staticmethod
    def add_user(userdata: AddUser):
        output = session.post(config["request_url"] + "add_user", json=userdata.model_dump())
        output.raise_for_status()
        return True

    @staticmethod
    def get_all_userdata():
        return session.get(config["request_url"] + "get_all_userdata").json()

    @staticmethod
    def get_userdata(user_id: int):
        response = session.get(config["request_url"] + "get_userdata", params={"user_id": user_id})
        if response.status_code != 200:
            raise IOError(
                f"\nCONTENT: {response.content}\nJSON: {response.json()}\nSTATUS CODE: {response.status_code}")
        return RawUserData(**response.json())

    @staticmethod
    def get_userdata_by_username(username: str):
        response = session.get(config["request_url"] + "get_userdata_by_username", params={"username": username})
        if response.status_code != 200:
            raise IOError(f"CONTENT: {response.content}\nJSON: {response.json()}\nSTATUS CODE: {response.status_code}")
        return RawUserData(**response.json())

    @staticmethod
    def get_username_list():
        result = session.get(config["request_url"] + "get_username_list").json()
        print(result)
        return result

    @staticmethod
    def get_transaction_list(user_id: int):
        return ([
            RawTransactionData(**transaction) for transaction in
            session.get(config["request_url"] + "get_transaction_list", params={"user_id": user_id}).json()
        ])

    @staticmethod
    def generate_transaction(current_money: float, transaction_details: TransactionField):
        params = {"current_money": current_money}
        return session.post(config["request_url"] + "generate_transaction",
                            params=params, json=transaction_details.model_dump()).json()

    @staticmethod
    def set_saldo(user_id: int, transaction_details: TransactionField):
        data = transaction_details.model_dump()
        return session.put(config["request_url"] + "set_saldo",
                           params={"user_id": user_id}, json=data).json()

    @staticmethod
    def delete_user(user_id: int):
        response = session.delete(config["request_url"] + "delete_user", params={"user_id": user_id})
        return response.status_code == 200

    @staticmethod
    def rename_user(user_id: int, new_username: str):
        params = {"user_id": user_id, "new_username": new_username}
        response = session.put(config["request_url"] + "rename_user", params=params)
        response.raise_for_status()
        return response.status_code == 200


# todo: add to Camillib
def filter_list(search: str, seq: list[str], case_sensitive: bool = False, order_alphabetically: bool = True) -> list:
    if order_alphabetically:
        seq.sort()

    result = []
    for item in seq:
        if item == search:
            result.insert(0, item)
        elif (search in item) if case_sensitive else (search.casefold() in item.casefold()):
            result.append(item)

    return result


def reverse(seq):  # todo: replace with build in function
    t = copy.deepcopy(seq)
    t.reverse()
    return t


def overwrite_dict_with_dict(original_dict: dict, overwriter_dict):
    for key, value in overwriter_dict.items():
        original_dict[key] = value
    return original_dict


def on_exit(message=None) -> None:
    if message is None:
        sys.exit(0)
    else:
        sys.exit(str(message))
