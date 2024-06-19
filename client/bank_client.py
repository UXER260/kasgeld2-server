import copy
import json
import socket
import sys

import PySimpleGUI as Sg
import requests
from pydantic import BaseModel

with open('config.json', 'r') as f:
    config = json.load(f)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


if not config["host"]:
    config["host"] = get_ip()

ADDRESS = str(config["host"]) + ("" if not config["port"] else f":{config['port']}")
print(ADDRESS)


class TransactionField(BaseModel):
    amount_to_set: float
    title: str
    description: str
    date: str
    time: str


class TransactionJsonField(BaseModel):
    title: str
    amount: float  # NOT saldo after the transaction. but the amount that got added or subtracted
    # (x or -x, 1 or -1 depending on whether the user earned or lost money)
    description: str
    saldo_after_transaction: float
    date: str
    time: str


class AccountField(BaseModel):
    name: str
    money: float
    transactions: list[dict]
    savings: list[dict]
    last_salary_date: list[int] = []
    # data_of_birth: list[int]


class Account:
    account_name_list = []

    @classmethod
    def load_account(cls, data):
        if type(data) is dict:
            return AccountField(**data)
        else:
            return data

    @staticmethod
    def check_account_exists(account_name: str):
        return requests.get(ADDRESS + "/check_account_exists", params={"account_name": account_name}).json()

    @classmethod
    def update_account_names(cls):
        cls.account_name_list = cls.get_account_name_list()

    @staticmethod
    def add_account_to_file(account_info: AccountField):
        new_account_info = requests.post(ADDRESS + "/add_account_to_file",
                                         json=account_info.model_dump()).json()
        # print(new_account_info)
        if type(new_account_info) is str:
            return new_account_info
        return AccountField(**new_account_info)

    @staticmethod
    def get_account_data(account_name: str):
        account_data = requests.get(ADDRESS + "/get_account_data",
                                    params={"account_name": account_name})

        print("DATA", account_data.content)

        if account_data is None:
            return account_data
        else:
            return AccountField(**account_data.json())

    @staticmethod
    def get_account_name_list():
        return sorted(requests.get(ADDRESS + "/get_account_name_list").json())

    @staticmethod
    def get_transaction_header_list(account: AccountField):
        response = requests.get(ADDRESS + "/get_transaction_header_list",
                                params={"account_name": account.name})
        return response.json()

    @staticmethod
    def generate_transaction(current_money, transaction_details: TransactionField):
        params = {"current_money": current_money}
        return requests.post(ADDRESS + "/generate_transaction",
                             params=params, json=transaction_details.model_dump()).json()

    @staticmethod
    def set_saldo(account: AccountField, transaction_details: TransactionField):
        new_account_data = requests.put(ADDRESS + "/set_saldo", params={"account_name": account.name},
                                        json=transaction_details.model_dump())
        print("RESPONSE:", new_account_data.content)
        return AccountField(**new_account_data.json())

    @staticmethod
    def delete_account(account_name):
        response = requests.delete(ADDRESS + "/delete_account", params={"account_name": account_name})
        if response.status_code != 200:
            return False
        return response

    @staticmethod
    def rename_account(account, new_name):
        params = {"account_name": account.name, "new_name": new_name}
        response = requests.put(ADDRESS + "/rename_account", params=params)
        if response.status_code != 200:
            return False
        account.name = new_name
        return True


class Window:
    Sg.theme(config['theme'])

    @staticmethod
    def account_selection_window(**params):
        return {
            "init_args": {
                "title": "Kies een persoon",
                "size": config['window_size'],
            },
            "layout": [
                [Sg.InputText("", font=config['font'], expand_x=True, key='-SEARCH_BAR_FIELD-',
                              enable_events=True)],
                [Sg.Listbox(params["name_list"], font=config['font'], expand_x=True, expand_y=True,
                            enable_events=True, key='-NAME_LIST-')],
                [Sg.Button("Voeg Gebruiker Toe", font=config['font'], expand_x=True, key="-ADD_USER-")]
            ]}

    @staticmethod
    def account_overview_window(**params):
        return {
            "init_args": {"title": params["account_name"],
                          "size": config['window_size']},
            "layout": [
                [Sg.Button(" < ", font=config['font'], key="-BACK_BUTTON-"),
                 Sg.Text(f"€{params['saldo']}", font=config['header_font'], justification="c", expand_x=True,
                         key="-SALDO-"),
                 Sg.Button(" ⚙ ", font=config['font'], key="-OPTIONS_BUTTON-")],
                [Sg.Listbox(params["transaction_title_list"],
                            enable_events=True, expand_y=True, expand_x=True, font="Helvetica 25",
                            key='-TRANSACTION_TITLE_LIST-')],

                [Sg.Button("Verander Saldo", font="Helvetica 30", expand_x=True,
                           key="-SET_SALDO_BUTTON-")]]}

    @staticmethod
    def set_saldo_menu(**params):
        fond_type = config['font'].split(' ')[0]
        return {
            "init_args": {
                "title": f"Pas kasgeld-saldo aan voor `{params['account_name']}`",
                "size": (config['window_size'][1], config['window_size'][1]),
                "keep_on_top": True
            },
            "layout": [
                [Sg.Text("Bedrag", font=config['font']), Sg.Push(),
                 Sg.DropDown(["-", "+", "op"], "-", readonly=True, font=config['font'], key="-PLUS_MINUS-"),
                 Sg.InputText("", font=config['font'], expand_x=True, key='-AMOUNT-')],
                [Sg.Text("Titel:", font=config['font']), Sg.Push(),
                 Sg.InputText("", font=config['font'], expand_x=True, key='-TRANSACTION_TITLE-')],
                [Sg.Text("Beschrijving", font=config['font'], expand_x=True)],
                [Sg.Multiline(font=f"{fond_type} 25", expand_x=True, expand_y=True, size=(0, 7),
                              key="-TRANSACTION_DESCRIPTION-")],
                [Sg.Button("OK", expand_x=True, font=config['font'], key="OK")]
            ]}

    @staticmethod
    def add_account_menu(**params):
        return {
            "init_args": {
                "title": "Voeg Gebruiker Toe",
                "size": (None, None),
                "keep_on_top": True
            },
            "layout": [
                [Sg.Text("Naam:", font=config["font"]), Sg.Push(),
                 Sg.InputText("", font=config['font'], size=(15, 0), key='-ACCOUNT_NAME-')],
                [Sg.Text("Kasgeld:", font=config["font"]), Sg.Push(),
                 Sg.InputText("", font=config['font'], size=(15, 0), key='-AMOUNT-')],
                [Sg.Button('OK', expand_x=True, font=config['font'])]
            ]}

    @staticmethod
    def options_menu(**params):
        return {
            "init_args": {
                "title": f"Opties",
                "size": (None, None),
                "keep_on_top": True
            },
            "layout": [
                [Sg.Button("Hernoem", font=config['font'], size=(10, 0), key='-RENAME_BUTTON-')],
                [Sg.Button("Verwijder", font=config['font'], size=(10, 0), key='-DELETE_BUTTON-')],
            ]}

    @staticmethod
    def rename_account_menu(**params):
        return {
            "init_args": {
                "title": f"Hernoem account `{params['account_name']}`",
                "size": (None, None),
                "keep_on_top": True
            },
            "layout": [
                [Sg.Text(f"Nieuwe naam:", font=config["font"],
                         expand_x=True, expand_y=True), Sg.Push(),
                 Sg.InputText("", font=config['font'], size=(15, 0), key='-NEW_ACCOUNT_NAME-')],
                [Sg.Button('OK', expand_x=True, font=config['font'], key="OK")],
            ]}

    @staticmethod
    def transaction_details_widget(**params):
        return {
            "init_args": {
                "title": f"Details - {params['transaction_title']}",
                "size": (850, 579),
                "keep_on_top": True
            },
            "layout": [
                [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                         expand_x=True,
                         font=config['font'])],
                [Sg.Text('Datum & Tijd', font="Helvetica 25"), Sg.Push(),
                 Sg.Text(f"{params['transaction_date']} | {params['transaction_time']}", font="Helvetica 25",
                         key="-TRANSACTION_DATE-TIME-")],
                [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                         expand_x=True,
                         font=config['font'])],
                [Sg.Text('Bedrag', font="Helvetica 25"), Sg.Push(),
                 Sg.Text(params['amount'], font="Helvetica 25", key="-AMOUNT-")],
                [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                         expand_x=True,
                         font=config['font'])],
                [Sg.Text('Saldo Na Transactie', font="Helvetica 25"), Sg.Push(),
                 Sg.Text(params["saldo_after_transaction"], font="Helvetica 25", key="-SALDO_AFTER_TRANSACTION-")],
                [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                         expand_x=True,
                         font=config['font'])],
                [Sg.Text('Beschrijving', font="Helvetica 25", justification="c", expand_x=True)],
                [Sg.Multiline(params["transaction_description"], font="Helvetica 25", disabled=True, expand_x=True,
                              size=(0, 7),
                              key="-TRANSACTION_DESCRIPTION-")],
            ]}

    @staticmethod
    def change_window(new_window_info: dict,
                      # param: `new_window`: dict object containing window information
                      current_window: Sg.Window = None,
                      keys=None  # param: `keys`: used for filling in missing information in the window layout
                      ) -> Sg.Window:  # "seamlessly" change to a different window
        if current_window is not None:
            loc = current_window.current_location()

            new_window = Sg.Window(**new_window_info["init_args"],
                                   layout=new_window_info["layout"], location=loc,
                                   finalize=True)
        else:
            new_window = Sg.Window(**new_window_info["init_args"],
                                   layout=new_window_info["layout"], finalize=True)

        if keys is not None:
            for key, value in keys.items():
                new_window[key].update(value)
        current_window.close() if current_window is not None else ...
        return new_window


# todo: add to Camillib
def filter_list(search, seq, conv_lower=True) -> list:
    if conv_lower:
        return [item for item in seq if search.lower() in item.lower()]
    else:
        return [item for item in seq if search in item]


def reverse(seq):  # todo: replace with build in function
    t = copy.deepcopy(seq)
    t.reverse()
    return t


def on_exit(message=None) -> None:
    if message is None:
        sys.exit(0)
    else:
        sys.exit(str(message))

##################### oud

# import copy
# import json
# import socket
# import sys
#
# import PySimpleGUI as Sg
# import requests
# from pydantic import BaseModel
#
# with open('config.json', 'r') as f:
#     config = json.load(f)
#
#
# def get_ip():
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     s.connect(("8.8.8.8", 80))
#     ip = s.getsockname()[0]
#     s.close()
#     return ip
#
#
# if not config["host"]:
#     config["host"] = get_ip()
#
# ADDRESS = str(config["host"]) + ("" if not config["port"] else f":{config['port']}")
# print(ADDRESS)
#
#
# class TransactionField(BaseModel):
#     amount_to_set: float
#     title: str
#     description: str
#     date: str
#     time: str
#
#
# class TransactionJsonField(BaseModel):
#     title: str
#     amount: float  # NOT saldo after the transaction. but the amount that got added or subtracted
#     # (x or -x, 1 or -1 depending on whether the user earned or lost money)
#     description: str
#     saldo_after_transaction: float
#     date: str
#     time: str
#
#
# class AccountField(BaseModel):
#     name: str
#     money: float
#     transactions: list[dict]
#     savings: list[dict]
#     last_salary_date: list[int] = []
#     # data_of_birth: list[int]
#
#
# class Account:
#     loaded_accounts = {}
#     account_name_list = [account.name for account in loaded_accounts.values()]
#
#     @classmethod
#     def refresh(cls):
#         cls.update_accounts()
#         cls.load_account_names()
#
#     @classmethod
#     def load_account_names(cls):
#         cls.account_name_list = [account.name for account in cls.loaded_accounts.values()]
#
#     @classmethod
#     def update_account_names(cls):
#         cls.account_name_list = cls.get_account_name_list()
#
#     @staticmethod
#     def load_account(account: AccountField) -> AccountField:  # load one single account
#         Account.loaded_accounts[account.name] = AccountField(
#             name=account.name,
#             money=account.money,
#             transactions=account.transactions,
#             savings=account.savings
#         )
#         return Account.loaded_accounts[account.name]
#
#     @classmethod
#     def update_accounts(cls) -> None:  # load all accounts
#         accounts = Account.get_all_account_data()
#         for name, data in accounts.items():
#             new_data = {"name": name, "money": data["money"], "transactions": data["transactions"],
#                         "savings": data["savings"]}
#             cls.load_account(AccountField(**new_data))
#
#     @staticmethod
#     def add_account_to_file(account_info: AccountField):
#         new_account_info = requests.post(ADDRESS + "/add_account_to_file",
#                                          json=account_info.model_dump()).json()
#         return Account.load_account(AccountField(**new_account_info))
#
#     @staticmethod
#     def get_all_account_data():
#         return requests.get(ADDRESS + "/get_all_account_data").json()
#
#     @staticmethod
#     def get_account_name_list():
#         return requests.get(ADDRESS + "/get_account_name_list").json()
#
#     @staticmethod
#     def get_transaction_header_list(account: AccountField):
#         response = requests.get(ADDRESS + "/get_transaction_header_list",
#                                 params={"account_name": account.name})
#         return response.json()
#
#     @staticmethod
#     def generate_transaction(current_money, transaction_details: TransactionField):
#         params = {"current_money": current_money}
#         return requests.post(ADDRESS + "/generate_transaction",
#                              params=params, json=transaction_details.model_dump()).json()
#
#     @staticmethod
#     def set_saldo(account: AccountField, transaction_details: TransactionField):
#         data = {"account": account.model_dump(), "transaction_details": transaction_details.model_dump()}
#         new_account_data = requests.put(ADDRESS + "/set_saldo", json=data).json()
#         return AccountField(**new_account_data)
#
#     @staticmethod
#     def delete_account(account):
#         response = requests.delete(ADDRESS + "/delete_account", json=account.model_dump())
#         if response.status_code != 200:
#             return False
#         return response
#
#     @staticmethod
#     def rename_account(account, new_name):
#         params = {"account_name": account.name, "new_name": new_name}
#         response = requests.put(ADDRESS + "/rename_account", params=params)
#         if response.status_code != 200:
#             return False
#         Account.loaded_accounts[new_name] = Account.loaded_accounts.pop(account.name)
#         account.name = new_name
#         return True
#
#
# class Window:
#     Sg.theme(config['theme'])
#
#     @staticmethod
#     def account_selection_window(**params):
#         return {
#             "init_args": {
#                 "title": "Kies een persoon",
#                 "size": config['window_size'],
#             },
#             "layout": [
#                 [Sg.InputText("", font=config['font'], expand_x=True, key='-SEARCH_BAR_FIELD-',
#                               enable_events=True)],
#                 [Sg.Listbox(params["name_list"], font=config['font'], expand_x=True, expand_y=True,
#                             enable_events=True, key='-NAME_LIST-')],
#                 [Sg.Button("Voeg Gebruiker Toe", font=config['font'], expand_x=True, key="-ADD_USER-")]
#             ]}
#
#     @staticmethod
#     def account_overview_window(**params):
#         return {
#             "init_args": {"title": params["account_name"],
#                           "size": config['window_size']},
#             "layout": [
#                 [Sg.Button(" < ", font=config['font'], key="-BACK_BUTTON-"),
#                  Sg.Text(f"€{params['saldo']}", font=config['header_font'], justification="c", expand_x=True,
#                          key="-SALDO-"),
#                  Sg.Button(" ⚙ ", font=config['font'], key="-OPTIONS_BUTTON-")],
#                 [Sg.Listbox(params["transaction_title_list"],
#                             enable_events=True, expand_y=True, expand_x=True, font="Helvetica 25",
#                             key='-TRANSACTION_TITLE_LIST-')],
#
#                 [Sg.Button("Verander Saldo", font="Helvetica 30", expand_x=True,
#                            key="-SET_SALDO_BUTTON-")]]}
#
#     @staticmethod
#     def set_saldo_menu(**params):
#         fond_type = config['font'].split(' ')[0]
#         return {
#             "init_args": {
#                 "title": f"Pas kasgeld-saldo aan voor `{params['account_name']}`",
#                 "size": (config['window_size'][1], config['window_size'][1]),
#                 "keep_on_top": True
#             },
#             "layout": [
#                 [Sg.Text("Bedrag", font=config['font']), Sg.Push(),
#                  Sg.DropDown(["-", "+", "op"], "-", readonly=True, font=config['font'], key="-PLUS_MINUS-"),
#                  Sg.InputText("", font=config['font'], expand_x=True, key='-AMOUNT-')],
#                 [Sg.Text("Titel:", font=config['font']), Sg.Push(),
#                  Sg.InputText("", font=config['font'], expand_x=True, key='-TRANSACTION_TITLE-')],
#                 [Sg.Text("Beschrijving", font=config['font'], expand_x=True)],
#                 [Sg.Multiline(font=f"{fond_type} 25", expand_x=True, expand_y=True, size=(0, 7),
#                               key="-TRANSACTION_DESCRIPTION-")],
#                 [Sg.Button("OK", expand_x=True, font=config['font'], key="OK")]
#             ]}
#
#     @staticmethod
#     def add_account_menu(**params):
#         return {
#             "init_args": {
#                 "title": "Voeg Gebruiker Toe",
#                 "size": (None, None),
#                 "keep_on_top": True
#             },
#             "layout": [
#                 [Sg.Text("Naam:", font=config["font"]), Sg.Push(),
#                  Sg.InputText("", font=config['font'], size=(15, 0), key='-ACCOUNT_NAME-')],
#                 [Sg.Text("Kasgeld:", font=config["font"]), Sg.Push(),
#                  Sg.InputText("", font=config['font'], size=(15, 0), key='-AMOUNT-')],
#                 [Sg.Button('OK', expand_x=True, font=config['font'])]
#             ]}
#
#     @staticmethod
#     def options_menu(**params):
#         return {
#             "init_args": {
#                 "title": f"Opties",
#                 "size": (None, None),
#                 "keep_on_top": True
#             },
#             "layout": [
#                 [Sg.Button("Hernoem", font=config['font'], size=(10, 0), key='-RENAME_BUTTON-')],
#                 [Sg.Button("Verwijder", font=config['font'], size=(10, 0), key='-DELETE_BUTTON-')],
#             ]}
#
#     @staticmethod
#     def rename_account_menu(**params):
#         return {
#             "init_args": {
#                 "title": f"Hernoem account `{params['account_name']}`",
#                 "size": (None, None),
#                 "keep_on_top": True
#             },
#             "layout": [
#                 [Sg.Text(f"Nieuwe naam:", font=config["font"],
#                          expand_x=True, expand_y=True), Sg.Push(),
#                  Sg.InputText("", font=config['font'], size=(15, 0), key='-NEW_ACCOUNT_NAME-')],
#                 [Sg.Button('OK', expand_x=True, font=config['font'], key="OK")],
#             ]}
#
#     @staticmethod
#     def transaction_details_widget(**params):
#         return {
#             "init_args": {
#                 "title": f"Details - {params['transaction_title']}",
#                 "size": (850, 579),
#                 "keep_on_top": True
#             },
#             "layout": [
#                 [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
#                          expand_x=True,
#                          font=config['font'])],
#                 [Sg.Text('Datum & Tijd', font="Helvetica 25"), Sg.Push(),
#                  Sg.Text(f"{params['transaction_date']} | {params['transaction_time']}", font="Helvetica 25",
#                          key="-TRANSACTION_DATE-TIME-")],
#                 [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
#                          expand_x=True,
#                          font=config['font'])],
#                 [Sg.Text('Bedrag', font="Helvetica 25"), Sg.Push(),
#                  Sg.Text(params['amount'], font="Helvetica 25", key="-AMOUNT-")],
#                 [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
#                          expand_x=True,
#                          font=config['font'])],
#                 [Sg.Text('Saldo Na Transactie', font="Helvetica 25"), Sg.Push(),
#                  Sg.Text(params["saldo_after_transaction"], font="Helvetica 25", key="-SALDO_AFTER_TRANSACTION-")],
#                 [Sg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
#                          expand_x=True,
#                          font=config['font'])],
#                 [Sg.Text('Beschrijving', font="Helvetica 25", justification="c", expand_x=True)],
#                 [Sg.Multiline(params["transaction_description"], font="Helvetica 25", disabled=True, expand_x=True,
#                               size=(0, 7),
#                               key="-TRANSACTION_DESCRIPTION-")],
#             ]}
#
#     @staticmethod
#     def change_window(new_window_info: dict,
#                       # param: `new_window`: dict object containing window information
#                       current_window: Sg.Window = None,
#                       keys=None  # param: `keys`: used for filling in missing information in the window layout
#                       ) -> Sg.Window:  # "seamlessly" change to a different window
#         if current_window is not None:
#             loc = current_window.current_location()
#
#             new_window = Sg.Window(**new_window_info["init_args"],
#                                    layout=new_window_info["layout"], location=loc,
#                                    finalize=True)
#         else:
#             new_window = Sg.Window(**new_window_info["init_args"],
#                                    layout=new_window_info["layout"], finalize=True)
#
#         if keys is not None:
#             for key, value in keys.items():
#                 new_window[key].update(value)
#         current_window.close() if current_window is not None else ...
#         return new_window
#
#
# # todo: add to Camillib
# def filter_list(search, seq, conv_lower=True) -> list:
#     if conv_lower:
#         return [item for item in seq if search.lower() in item.lower()]
#     else:
#         return [item for item in seq if search in item]
#
#
# def reverse(seq):  # todo: replace with build in function
#     t = copy.deepcopy(seq)
#     t.reverse()
#     return t
#
#
# def on_exit(message=None) -> None:
#     if message is None:
#         sys.exit(0)
#     else:
#         sys.exit(str(message))
