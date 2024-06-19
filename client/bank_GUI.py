# todo list ###########################
import traceback

from bank_client import *


# done ######################### done
# - review/improve logic in this file
# - monthly salary (kasgeld)
# SORT ACCOUNT NAMES ALPHABETICALLY
# todo list ###########################


# - savings
# - theme picker
# - (maybe) finally fix/and implement the console version of this program


def check_string_valid_float(string: str):
    try:
        return float(string)
    except ValueError:
        return False


def select(window=None):
    print("AAAA")
    Account.update_account_names()
    print("BBBBB")

    new_window_info = Window.account_selection_window(name_list=Account.account_name_list)
    if window is None:
        window = Window.change_window(new_window_info=new_window_info)  # create window if necessary
        # (most likely at startup when there is no initial window to swap with)
    else:
        window = Window.change_window(new_window_info=new_window_info,
                                      current_window=window)
    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED:
            on_exit()

        elif event == "-SEARCH_BAR_FIELD-":  # if a letter is typed
            print(f"typed `{values['-SEARCH_BAR_FIELD-']}` in search bar")
            window["-NAME_LIST-"].update(
                filter_list(values["-SEARCH_BAR_FIELD-"], Account.account_name_list))  # search feature
            # update name list

        elif event == "-NAME_LIST-":
            if not values["-NAME_LIST-"]:
                continue  # when clicked and list was emtpy
            print(f"clicked `{values['-NAME_LIST-'][0]}` in namelist")
            account = Account.get_account_data(account_name=values["-NAME_LIST-"][0])
            print("ACCOUNT  ", account)
            status = \
                mode_account_overview(account, window)
            window_info = Window.account_selection_window(name_list=Account.account_name_list)
            window = Window.change_window(new_window_info=window_info, current_window=status)

            continue

        elif event == "-ADD_USER-":
            print(f"pressed `{event}` button")
            status = \
                add_account()
            if status:
                added_account = status
                window["-SEARCH_BAR_FIELD-"].update(added_account.name)
                window["-NAME_LIST-"].update([added_account.name])


def mode_account_overview(account, window=None):
    window_info = Window.account_overview_window(saldo=account.money, account_name=account.name,
                                                 transaction_title_list=Account.get_transaction_header_list(
                                                     account=account))
    return_status = None

    window_info["init_args"]["title"] = account.name
    if window is None:
        window = Window.change_window(new_window_info=window_info)
    else:
        window = Window.change_window(new_window_info=window_info, current_window=window)

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED:
            on_exit()
        elif event == "-BACK_BUTTON-":
            return_status = window
            break
        elif event == "-TRANSACTION_TITLE_LIST-":
            if len(window["-TRANSACTION_TITLE_LIST-"].get_indexes()) <= 0:
                continue
            # get selected transaction
            transaction = account.transactions[-1 - window["-TRANSACTION_TITLE_LIST-"].get_indexes()[0]]

            view_transaction(transaction)
        elif event == "-SET_SALDO_BUTTON-":
            status = \
                set_saldo(account)

            if new_account_info := status:
                account = Account.load_account(new_account_info)

                window["-TRANSACTION_TITLE_LIST-"].update(Account.get_transaction_header_list(account=account))
                window["-SALDO-"].update(f"€{account.money}")

        elif event == "-OPTIONS_BUTTON-":
            status = \
                options(account)
            if status:
                Account.update_account_names()
                if status == "AccountRenamed":

                    # adjust window to update new name
                    window.set_title(account.name)

                elif status == "AccountDeleted":
                    return_status = window
                    break
    return return_status


def check_valid_saldo(saldo: float):
    if -7320 > float(saldo) or float(saldo) > 7320:
        Sg.popup("Houd u dat bedrag eventjes realistisch?", font=config["font"], keep_on_top=True,
                 title="Fout")
        return False


def set_saldo(account: AccountField):
    new_window_info = Window.set_saldo_menu(account_name=account.name)
    window = Window.change_window(new_window_info=new_window_info)

    return_status = None

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED:
            break

        if event == "OK":
            if all(values.values()):
                amount = check_string_valid_float(values["-AMOUNT-"])
                if check_valid_saldo(saldo=amount) is False:
                    continue

                plus_minus = values["-PLUS_MINUS-"]
                if plus_minus == "-":
                    amount_to_set = account.money - amount
                elif plus_minus == "+":
                    amount_to_set = account.money + amount
                else:
                    amount_to_set = amount
                transaction_title = values["-TRANSACTION_TITLE-"]
                transaction_description = values["-TRANSACTION_DESCRIPTION-"]

                transaction_details = TransactionField(
                    amount_to_set=amount_to_set,
                    title=transaction_title,
                    description=transaction_description,
                    date="",
                    time=""
                )

                if check_valid_saldo(saldo=amount_to_set) is False:
                    continue

                status = \
                    Account.set_saldo(
                        account=account,
                        transaction_details=transaction_details
                    )
                return_status = status
                break
    window.close()
    return return_status


def view_transaction(transaction):
    window_info = Window.transaction_details_widget(
        transaction_date=transaction["date"],
        transaction_time=transaction["time"], amount=transaction["amount"],
        saldo_after_transaction=transaction["saldo_after_transaction"],
        transaction_description=transaction["description"],
        transaction_title=transaction["title"])

    window = Window.change_window(new_window_info=window_info)

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED:
            break
    window.close()
    return True


def get_birth_date():
    Sg.popup_get_date()


def add_account() -> AccountField | None:
    window = Window.change_window(new_window_info=Window.add_account_menu())
    return_status = None

    while True:
        event, values = window.read()

        if event == Sg.WINDOW_CLOSED:  # stop
            return_status = None
            break

        if event == "OK":
            if all(values.values()):
                saldo = values["-AMOUNT-"]
                if check_valid_saldo(saldo=saldo) is False:
                    continue
                account_name = values["-ACCOUNT_NAME-"]
                account_name = account_name.title()

                check = Account.check_account_exists(account_name=account_name)
                print("CHECK", check)
                if check:
                    Sg.PopupOK(f"Account `{account_name}` bestaat al", keep_on_top=True, font=config["font"])
                    window["-ACCOUNT_NAME-"].update(account_name)
                    continue

                first_transaction = Account.generate_transaction(
                    current_money=0,
                    transaction_details=TransactionField(
                        amount_to_set=saldo,
                        title="start bedrag",
                        description=f"Start bedrag van {account_name}",
                        date="",
                        time=""
                    )
                )

                account = Account.load_account(
                    {"name": account_name, "money": saldo, "transactions": [first_transaction], "savings": []})

                status = Account.add_account_to_file(account_info=account)

                if status:
                    return_status = status
                    break

    window.close()
    return return_status


def rename(account):
    window_info = Window.rename_account_menu(account_name=account.name)
    window = Window.change_window(new_window_info=window_info)
    return_status = None
    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED:
            break
        elif event == "OK":
            new_name = values["-NEW_ACCOUNT_NAME-"]
            status = \
                Account.rename_account(account=account, new_name=new_name)

            if status is not True:
                if status == "ExistsError":
                    Sg.PopupOK(f"Het account `{new_name}` bestaat al.", font=config["font"], keep_on_top=True)
            else:
                return_status = new_name
                break

    window.close()
    return return_status


def options(account):
    window_info = Window.options_menu(account_name=account.name)
    window = Window.change_window(new_window_info=window_info)
    return_status = None

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED:
            break
        elif event == "-DELETE_BUTTON-":
            ok = \
                Sg.PopupOKCancel(f"Weet je zeker dat je het account\n`{account.name}` wilt verwijderen?",
                                 keep_on_top=True, font=config["font"])
            if ok == "OK":
                status = \
                    Account.delete_account(account.name)
                if status:
                    Sg.PopupOK(f"Account `{account.name}`\nwas succesvol verwijderd", font=config["font"],
                               keep_on_top=True)
                    return_status = "AccountDeleted"
                else:
                    Sg.PopupOK(f"Fout bij verwijderen van account\n`{account.name}`", font=config["font"],
                               keep_on_top=True)
                    return_status = False
            break
        elif event == "-RENAME_BUTTON-":
            status = \
                rename(account)
            print("renamed", status)
            if status:
                return_status = "AccountRenamed"
                break

    window.close()
    return return_status


def main():
    sys.excepthook = exception
    running = True
    while running:
        select()


def exception(exc_type, exc_value, exc_traceback):
    traceback.print_tb(exc_traceback)
    print(f"{exc_type.__name__}: {exc_value}")

    if exc_type is requests.exceptions.ConnectionError:
        Sg.Popup("De verbinding is niet (meer) beschikbaar.\n"
                 "Zorg ervoor dat je verbonden bent met het WiFi netwerk 'De Vrije Ruimte'\n",
                 "Check je connectie en probeer het opnieuw.",
                 title="Connectie Fout", keep_on_top=True, font=config["font"])
    else:
        Sg.Popup(
            f'⚠Er is een onverwachtse fout opgetreden, neem AUB contact op met Camillo, als het propleem vaker voorkomt.'
            f'\n\nType: "{exc_type.__name__}"\nOmschrijving: "{exc_value}"',
            title="ONBEKENDE FOUT", text_color='red', keep_on_top=True, font=config["font"]
        )
    sys.exit(1)


if __name__ == "__main__":
    main()

################### oud

# # todo list ###########################
# import traceback
#
# from bank_client import *
#
#
# # done ######################### done
# # - review/improve logic in this file
# # - monthly salary (kasgeld)
# # todo list ###########################
#
#
# # fixme SORT ACCOUNT NAMES ALPHABETICALLY
# # - savings
# # - theme picker
# # - (maybe) finally fix/and implement the UI version of this program
#
#
# def check_string_valid_float(string: str):
#     try:
#         return float(string)
#     except ValueError:
#         return False
#
#
# def select(window=None):
#     new_window_info = Window.account_selection_window(name_list=Account.account_name_list)
#     if window is None:
#         window = Window.change_window(new_window_info=new_window_info)  # create window if necessary
#         # (most likely at startup when there is no initial window to swap with)
#     else:
#         window = Window.change_window(new_window_info=new_window_info,
#                                       current_window=window)
#     while True:
#         event, values = window.read()
#         if event == Sg.WINDOW_CLOSED:
#             on_exit()
#
#         elif event == "-SEARCH_BAR_FIELD-":  # if a letter is typed
#             print(f"typed `{values['-SEARCH_BAR_FIELD-']}` in search bar")
#             window["-NAME_LIST-"].update(
#                 filter_list(values["-SEARCH_BAR_FIELD-"], Account.account_name_list))  # search feature
#             # update name list
#
#         elif event == "-NAME_LIST-":
#             if not values["-NAME_LIST-"]:
#                 continue  # when clicked and list was emtpy
#             print(f"clicked `{values['-NAME_LIST-'][0]}` in namelist")
#             account = Account.loaded_accounts[values["-NAME_LIST-"][0]]
#             status = \
#                 mode_account_overview(account, window)
#             window_info = Window.account_selection_window(name_list=Account.account_name_list)
#             window = Window.change_window(new_window_info=window_info, current_window=status)
#
#             continue
#
#         elif event == "-ADD_USER-":
#             print(f"pressed `{event}` button")
#             status = \
#                 add_account()
#             if status:
#                 Account.refresh()
#                 added_account = status
#                 window["-SEARCH_BAR_FIELD-"].update(added_account.name)
#                 window["-NAME_LIST-"].update([added_account.name])
#
#
# def mode_account_overview(account, window=None):
#     window_info = Window.account_overview_window(saldo=account.money, account_name=account.name,
#                                                  transaction_title_list=Account.get_transaction_header_list(
#                                                      account=account))
#     return_status = None
#
#     window_info["init_args"]["title"] = account.name
#     if window is None:
#         window = Window.change_window(new_window_info=window_info)
#     else:
#         window = Window.change_window(new_window_info=window_info, current_window=window)
#
#     while True:
#         event, values = window.read()
#         if event == Sg.WINDOW_CLOSED:
#             on_exit()
#         elif event == "-BACK_BUTTON-":
#             return_status = window
#             break
#         elif event == "-TRANSACTION_TITLE_LIST-":
#             if len(window["-TRANSACTION_TITLE_LIST-"].get_indexes()) <= 0:
#                 continue
#             # get selected transaction
#             transaction = account.transactions[-1 - window["-TRANSACTION_TITLE_LIST-"].get_indexes()[0]]
#
#             view_transaction(transaction)
#         elif event == "-SET_SALDO_BUTTON-":
#             status = \
#                 set_saldo(account)
#
#             if new_account_info := status:
#                 account = Account.load_account(account=new_account_info)
#
#                 window["-TRANSACTION_TITLE_LIST-"].update(Account.get_transaction_header_list(account=account))
#                 window["-SALDO-"].update(f"€{account.money}")
#
#         elif event == "-OPTIONS_BUTTON-":
#             status = \
#                 options(account)
#             if status:
#                 Account.update_account_names()
#                 if status == "AccountRenamed":
#
#                     # adjust window to update new name
#                     window.set_title(account.name)
#
#                 elif status == "AccountDeleted":
#                     return_status = window
#                     break
#     return return_status
#
#
# def check_valid_saldo(saldo: float):
#     if -7320 > float(saldo) or float(saldo) > 7320:
#         Sg.popup("Houd u dat bedrag eventjes realistisch?", font=config["font"], keep_on_top=True,
#                  title="Fout")
#         return False
#
#
# def set_saldo(account: AccountField):
#     new_window_info = Window.set_saldo_menu(account_name=account.name)
#     window = Window.change_window(new_window_info=new_window_info)
#
#     return_status = None
#
#     while True:
#         event, values = window.read()
#         if event == Sg.WINDOW_CLOSED:
#             break
#
#         if event == "OK":
#             if all(values.values()):
#                 amount = check_string_valid_float(values["-AMOUNT-"])
#                 if amount is False:
#                     continue
#                 plus_minus = values["-PLUS_MINUS-"]
#                 if plus_minus == "-":
#                     amount_to_set = account.money - amount
#                 elif plus_minus == "+":
#                     amount_to_set = account.money + amount
#                 else:
#                     amount_to_set = amount
#                 transaction_title = values["-TRANSACTION_TITLE-"]
#                 transaction_description = values["-TRANSACTION_DESCRIPTION-"]
#
#                 transaction_details = TransactionField(
#                     amount_to_set=amount_to_set,
#                     title=transaction_title,
#                     description=transaction_description,
#                     date="",
#                     time=""
#                 )
#
#                 if check_valid_saldo(saldo=amount_to_set) is False:
#                     continue
#
#                 status = \
#                     Account.set_saldo(
#                         account=account,
#                         transaction_details=transaction_details
#                     )
#                 return_status = status
#                 break
#     window.close()
#     return return_status
#
#
# def view_transaction(transaction):
#     window_info = Window.transaction_details_widget(
#         transaction_date=transaction["date"],
#         transaction_time=transaction["time"], amount=transaction["amount"],
#         saldo_after_transaction=transaction["saldo_after_transaction"],
#         transaction_description=transaction["description"],
#         transaction_title=transaction["title"])
#
#     window = Window.change_window(new_window_info=window_info)
#
#     while True:
#         event, values = window.read()
#         if event == Sg.WINDOW_CLOSED:
#             break
#     window.close()
#     return True
#
#
# def get_birth_date():
#     Sg.popup_get_date()
#
#
# def add_account() -> AccountField:
#     window = Window.change_window(new_window_info=Window.add_account_menu())
#     return_status = None
#
#     while True:
#         event, values = window.read()
#
#         if event == Sg.WINDOW_CLOSED:  # stop
#             return_status = None
#             break
#
#         if event == "OK":
#             if all(values.values()):
#                 saldo = values["-AMOUNT-"]
#                 account_name = values["-ACCOUNT_NAME-"]
#
#                 first_transaction = Account.generate_transaction(
#                     current_money=0,
#                     transaction_details=TransactionField(
#                         amount_to_set=saldo,
#                         title="start bedrag",
#                         description=f"Start bedrag van {account_name}",
#                         date="",
#                         time=""
#                     ))
#
#                 account = Account.load_account(
#                     AccountField(name=account_name, money=saldo, transactions=[first_transaction], savings=[]))
#
#                 if check_valid_saldo(saldo=saldo) is False:
#                     continue
#
#                 status = Account.add_account_to_file(account_info=account)
#
#                 if not status:
#                     if status == "ExistsError":
#                         Sg.PopupOK(f"Account `{account_name}` bestaat al", keep_on_top=True, font=config["font"])
#
#                 else:
#                     return_status = status
#                     break
#
#     window.close()
#     return return_status
#
#
# def rename(account):
#     window_info = Window.rename_account_menu(account_name=account.name)
#     window = Window.change_window(new_window_info=window_info)
#     return_status = None
#     while True:
#         event, values = window.read()
#         if event == Sg.WINDOW_CLOSED:
#             break
#         elif event == "OK":
#             new_name = values["-NEW_ACCOUNT_NAME-"]
#             status = \
#                 Account.rename_account(account=account, new_name=new_name)
#
#             if status is not True:
#                 if status == "ExistsError":
#                     Sg.PopupOK(f"Het account `{new_name}` bestaat al.", font=config["font"], keep_on_top=True)
#             else:
#                 return_status = new_name
#                 break
#
#     window.close()
#     return return_status
#
#
# def options(account):
#     window_info = Window.options_menu(account_name=account.name)
#     window = Window.change_window(new_window_info=window_info)
#     return_status = None
#
#     while True:
#         event, values = window.read()
#         if event == Sg.WINDOW_CLOSED:
#             break
#         elif event == "-DELETE_BUTTON-":
#             ok = \
#                 Sg.PopupOKCancel(f"Weet je zeker dat je het account\n`{account.name}` wilt verwijderen?",
#                                  keep_on_top=True, font=config["font"])
#             if ok == "OK":
#                 status = \
#                     Account.delete_account(account)
#                 if status:
#                     Sg.PopupOK(f"Account `{account.name}`\nwas succesvol verwijderd", font=config["font"],
#                                keep_on_top=True)
#                     return_status = "AccountDeleted"
#                 else:
#                     Sg.PopupOK(f"Fout bij verwijderen van account\n`{account.name}`", font=config["font"],
#                                keep_on_top=True)
#                     return_status = False
#             break
#         elif event == "-RENAME_BUTTON-":
#             status = \
#                 rename(account)
#             print("renamed", status)
#             if status:
#                 return_status = "AccountRenamed"
#                 break
#
#     window.close()
#     return return_status
#
#
# def main():
#     sys.excepthook = exception
#     running = True
#     while running:
#         Account.refresh()
#         select()
#
#
# def exception(exc_type, exc_value, exc_traceback):
#     traceback.print_tb(exc_traceback)
#     print(f"{exc_type.__name__}: {exc_value}")
#
#     Sg.Popup(
#         f'⚠Er is een onverwachtse fout opgetreden, neem AUB contact op met Camillo, als het propleem vaker voorkomt.'
#         f'\n\nType: "{exc_type.__name__}"\nOmschrijving: "{exc_value}"',
#         title="FATALE ERROR", text_color='red', keep_on_top=True, font=config["font"]
#     )
#     sys.exit(1)
#
#
# if __name__ == "__main__":
#     main()
