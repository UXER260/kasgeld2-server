# client/main.py

import datetime

import backend
import Camillo_GUI_framework
import updater
from imports import *

with open('config.json', 'r') as f:
    config = json.load(f)

print("TEST")


class App(Camillo_GUI_framework.App):
    @classmethod
    def run(cls):
        updated = updater.conditional_deploy_latest_update()
        if updated:
            print("UPDATED!")
            pysg.popup_no_buttons("Nieuwe updates gedownload.\nHerstarten...", non_blocking=True, auto_close=True,
                                  auto_close_duration=.75)

        valid_session = backend.Admin.check_session_valid()
        if not valid_session:
            cls.current_gui().window.hide()
            if pysg.popup_yes_no("Log in voor toegang", title="De inlog is verlopen",
                                 font=backend.default_font()) != "Yes":
                cls.active = False
                return False
            else:
                cls.set_gui(gui=AdminLoginMenu())

        super().run()


class UserSelectionWindow(Camillo_GUI_framework.Gui):
    def __init__(self, name_list: list[str] = None,
                 window_title="Kies een persoon", *args, **kwargs):
        if name_list is None:
            name_list = backend.User.get_username_list()
        self.name_list = name_list
        super().__init__(window_title=window_title, *args, **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.InputText("", font=self.font, expand_x=True, key='-SEARCH_BAR_FIELD-',
                            enable_events=True), pysg.Button("👤", font=self.font)],
            [pysg.Listbox(self.name_list, font=self.font, expand_x=True, expand_y=True,
                          enable_events=True, key='-NAME_LIST-')],
            [pysg.Button("add", font=self.font, expand_x=True)]
        ]

    def update(self):
        super().update()

        if self.event == '-SEARCH_BAR_FIELD-':  # if a letter is typed
            self.window['-NAME_LIST-'].update(
                backend.filter_list(self.values['-SEARCH_BAR_FIELD-'], self.name_list))  # search feature

        elif self.event == '-NAME_LIST-' and self.values['-NAME_LIST-']:  # when clicked and list is not emtpy
            username = self.values['-NAME_LIST-'][0]
            if not backend.User.get_user_exists_by_username(username=username):
                pysg.Popup(f"Gebruiker met naam '{username}' bestaat niet meer.", title="ERROR",
                           font=self.font)
                self.refresh()
                return

            user = backend.User.get_user_by_username(username=username)

            transaction_list = backend.User.get_transaction_list(user_id=user.data.user_id)

            self.menu.set_gui(
                gui=UserOverviewWindow(user=user, transaction_list=transaction_list)
            )
            return

        elif self.event == "add":
            self.menu.set_gui(gui=AddUserMenu())

    def refresh(self, search_name: str | None = None):  # refresh username_list
        self.name_list = backend.User.get_username_list()
        if self.values and self.values["-SEARCH_BAR_FIELD-"]:
            search_name = self.values["-SEARCH_BAR_FIELD-"]

        if search_name is not None:
            self.window['-NAME_LIST-'].update(backend.filter_list(search_name, self.name_list))
            if not self.values["-SEARCH_BAR_FIELD-"]:
                self.window['-SEARCH_BAR_FIELD-'].update(search_name)
        else:
            self.window["-NAME_LIST-"].update(self.name_list)


class UserOverviewWindow(Camillo_GUI_framework.Gui):
    def __init__(self, user: backend.User, transaction_list: list[backend.RawTransactionData],
                 window_title=None, *args,
                 **kwargs):
        if window_title is None:
            window_title = f"Gebruikersoverzicht - {user.data.name}"
        self.user = user
        self.transaction_list = transaction_list
        self.transaction_preview_list = self.generate_transaction_previews()
        super().__init__(window_title=window_title, *args, **kwargs)

    def generate_transaction_previews(self):
        transaction_preview_list = []
        for transaction in self.transaction_list:
            date = datetime.date.fromtimestamp(transaction.transaction_timestamp)

            # titel + datum = transaction preview
            transaction_preview_list.append(
                f"€{transaction.amount} | {transaction.title} | {date.day}/{date.month}/{date.year}"
            )
        return backend.reverse(transaction_preview_list)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Button(" < ", font=self.font, key="-BACK_BUTTON-"),
             pysg.Text(f"€{self.user.data.saldo}", font=self.font, justification="c", expand_x=True,
                       key="-SALDO-"),
             pysg.Button(" ⚙ ", font=self.font, key="-OPTIONS_BUTTON-")],
            [pysg.Listbox(self.transaction_preview_list, enable_events=True, expand_y=True, expand_x=True,
                          font=backend.default_font(scale=0.7), key="-TRANSACTION_PREVIEW_LIST-")],
            [pysg.Button("Verander Saldo", font=self.font, expand_x=True, key="-SET_SALDO_BUTTON-")]]

    def update(self):
        super().update()

        if self.event == "-BACK_BUTTON-":
            self.menu.back_button()
            assert isinstance(self.menu.current_gui(), UserSelectionWindow)
            self.menu.current_gui().refresh()
        elif self.event == pysg.WIN_CLOSE_ATTEMPTED_EVENT:
            # `self.menu.back_button()`  is niet nodig omdat al is ge-called bij `App.update`
            assert isinstance(self.menu.current_gui(), UserSelectionWindow)
            self.menu.current_gui().refresh()

        elif self.event == '-TRANSACTION_PREVIEW_LIST-' and len(
                self.window['-TRANSACTION_PREVIEW_LIST-'].get_indexes()) >= 0:
            # get selected transaction
            transaction = self.transaction_list[-1 - self.window['-TRANSACTION_PREVIEW_LIST-'].get_indexes()[0]]
            self.menu.set_gui(
                gui=TransActionDetailsWindow(transaction=transaction, user=self.user)
            )

        elif self.event == "-SET_SALDO_BUTTON-":
            self.menu.set_gui(
                gui=SetSaldoMenu(user=self.user)
            )

        elif self.event == "-OPTIONS_BUTTON-":
            self.menu.set_gui(OptionsMenu(user=self.user))

    def refresh(self, update_transaction_list=True):
        """
        Update het window met nieuwe gebruikers data
        :param update_transaction_list: Update `self.transaction_list` en `self.transaction_preview_list`
        met data van de server. Vervolgens: `self.window["-TRANSACTION_PREVIEW_LIST-"].update(data van server)`
        """

        self.update_window_title(new_title=f"Gebruikersoverzicht - {self.user.data.name}")

        self.window["-SALDO-"].update(self.user.data.saldo)

        if update_transaction_list:
            self.transaction_list = backend.User.get_transaction_list(user_id=self.user.data.user_id)
            self.transaction_preview_list = self.generate_transaction_previews()
            self.window["-TRANSACTION_PREVIEW_LIST-"].update(self.transaction_preview_list)


class TransActionDetailsWindow(Camillo_GUI_framework.Gui):
    def __init__(self, transaction: backend.RawTransactionData, user: backend.User, window_title=None, *args,
                 **kwargs):
        self.transaction = transaction
        self.user = user
        super().__init__(window_title=window_title, *args, **kwargs)

    def update(self):
        super().update()

        if self.event == "-BACK_BUTTON-":
            self.menu.back_button()

    def layout(self) -> list[list[pysg.Element]]:
        now = datetime.datetime.now()
        datetime_string = now.strftime('%d/%m/%Y %H:%M')
        return [
            [pysg.Button(" < ", font=self.font, key="-BACK_BUTTON-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=self.font)],
            [pysg.Text('Datum & Tijd', font=backend.default_font(scale=0.7)), pysg.Push(),
             pysg.Text(f"{datetime_string}", font=backend.default_font(scale=0.7),
                       key="-TRANSACTION_DATE-TIME-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=self.font)],
            [pysg.Text('Bedrag', font=backend.default_font(scale=0.7)), pysg.Push(),
             pysg.Text(self.transaction.amount, font=backend.default_font(scale=0.7), key="-AMOUNT-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=self.font)],
            [pysg.Text('Saldo Na Transactie', font=backend.default_font(scale=0.7)), pysg.Push(),
             pysg.Text(self.transaction.saldo_after_transaction, font=backend.default_font(scale=0.7),
                       key="-SALDO_AFTER_TRANSACTION-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=self.font)],
            [pysg.Text('Beschrijving', font=backend.default_font(scale=0.7), justification="c", expand_x=True, )],
            [pysg.Multiline(self.transaction.description, font=backend.default_font(scale=0.7), disabled=True,
                            expand_x=True,
                            size=(0, 7),
                            key="-TRANSACTION_DESCRIPTION-")],
        ]


class SetSaldoMenu(Camillo_GUI_framework.Gui):
    def __init__(self, user: backend.User, window_title=None, *args, **kwargs):
        if window_title is None:
            window_title = f"Pas saldo aan - {user.data.name}"
        self.user = user
        super().__init__(window_title=window_title, *args, **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Text("Bedrag", font=self.font), pysg.Push(),
             pysg.DropDown(["-", "+", "op"], "-", readonly=True, font=self.font, key="-PLUS_MINUS-"),
             pysg.InputText("", font=self.font, expand_x=True, key='-AMOUNT-')],
            [pysg.Text("Titel:", font=self.font), pysg.Push(),
             pysg.InputText("", font=self.font, expand_x=True, key='-TRANSACTION_TITLE-')],
            [pysg.Text("Beschrijving", font=self.font, expand_x=True)],
            [pysg.Multiline(font=self.font, expand_x=True, expand_y=True, size=(0, 7),
                            key="-TRANSACTION_DESCRIPTION-")],
            [pysg.Button("OK", expand_x=True, font=self.font, key="OK")]
        ]

    def update(self):
        super().update()

        if self.event == "OK":
            if not all(self.values.values()):
                pysg.Popup("Vul alle velden in")

            amount = backend.check_string_valid_float(self.values["-AMOUNT-"])
            if not backend.check_valid_saldo(saldo=amount):
                return

            operation = self.values["-PLUS_MINUS-"]  # of je saldo +bedrag, -bedrag of op bedrag wilt zetten
            if operation == "-":
                saldo_after_transaction = self.user.data.saldo - amount
            elif operation == "+":
                saldo_after_transaction = self.user.data.saldo + amount
            else:
                saldo_after_transaction = amount

            transaction_title = self.values["-TRANSACTION_TITLE-"]
            transaction_description = self.values["-TRANSACTION_DESCRIPTION-"]

            transaction_details = backend.TransactionField(
                saldo_after_transaction=saldo_after_transaction,
                title=transaction_title,
                description=transaction_description,
            )

            self.user.set_saldo(transaction_details=transaction_details)
            self.menu.back_button()
            # `type(self.menu.current_gui())` MOET `UserOverviewWindow` zijn
            assert isinstance(self.menu.current_gui(), UserOverviewWindow)
            self.menu.current_gui().refresh()  # `current_gui` is veranderd door `back_button`


class AddUserMenu(Camillo_GUI_framework.Gui):
    def __init__(self, window_is_popup=True, window_dimensions=(None, None), window_title: str = "Voeg Gebruiker Toe",
                 *args, **kwargs):
        super().__init__(window_is_popup=window_is_popup, window_dimensions=window_dimensions,
                         window_title=window_title,
                         *args, **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Text(f"Naam:", font=self.font, expand_x=True, expand_y=True), pysg.Push(),
             pysg.InputText("", font=self.font, size=(15, 0), key='-ACCOUNT_NAME-')],
            [pysg.Text(f"Saldo:", font=self.font, expand_x=True, expand_y=True), pysg.Push(),
             pysg.InputText("", font=self.font, size=(15, 0), key='-SALDO-')],
            [pysg.Button("OK", expand_x=True, font=self.font, key="OK")]
        ]

    def update(self):
        super().update()
        if self.event == "OK" and all(self.values.values()):
            username: str = self.values["-ACCOUNT_NAME-"]
            username = username.capitalize()
            saldo = self.values["-SALDO-"]
            if not backend.check_string_valid_float(saldo):
                return
            if not backend.check_valid_saldo(saldo=saldo):
                return

            if backend.User.get_user_exists_by_username(username):
                pysg.Popup(f"Gebruiker met naam '{username}' bestaat al.\n"
                           f"Kies een andere naam.", title="Gebruiker bestaat al", font=self.font,
                           keep_on_top=True)
                return

            user = backend.AddUser(
                name=username,
                saldo=saldo
            )
            backend.User.add_user(userdata=user)

            self.menu.back_button()
            assert isinstance(self.menu.current_gui(), UserSelectionWindow)
            self.menu.current_gui().refresh(search_name=user.name)


class OptionsMenu(Camillo_GUI_framework.Gui):
    def __init__(self, user: backend.User, window_is_popup=True, window_dimensions=(None, None),
                 window_title=None,
                 *args, **kwargs):
        if window_title is None:
            window_title = f"Opties - {user.data.name}"
        self.user = user
        super().__init__(window_is_popup=window_is_popup, window_dimensions=window_dimensions,
                         window_title=window_title, *args,
                         **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Button("Hernoem", font=self.font, size=(9, 0), key='-RENAME_BUTTON-')],
            [pysg.Button("Verwijder", font=self.font, size=(9, 0), key='-DELETE_BUTTON-')],
        ]

    def update(self):
        super().update()

        if self.event == "-RENAME_BUTTON-":
            self.window.hide()
            new_username = pysg.popup_get_text("Voor nieuwe gebruikersnaam is:", font=self.font,
                                               keep_on_top=True)
            if not new_username:
                self.window.un_hide()
                return

            if backend.User.get_user_exists_by_username(username=new_username) is True:
                pysg.Popup(f"Gebruiker met naam '{new_username}' bestaat al.\n"
                           f"Kies een andere naam.", title="Gebruiker bestaat al", font=self.font)
                self.window.un_hide()
                return False

            else:
                self.user.rename(new_username=new_username)
                # het is niet meer nodig om nu het window weer tevoorschijn te halen omdat het toch wordt gesloten
                self.menu.back_button()
                assert isinstance(self.menu.current_gui(), UserOverviewWindow)
                self.menu.current_gui().refresh()
                return True

        elif self.event == "-DELETE_BUTTON-":
            self.window.hide()
            delete_user = pysg.popup_yes_no(
                f"Weet je zeker dat je het account `{self.user.data.name}` wilt verwijderen?\n"
                f"Dit kan niet ongedaan worden gemaakt.", title="Verwijder Account",
                font=self.font, keep_on_top=True)
            if delete_user != "Yes":
                return None

            if backend.User.get_user_exists_by_id(user_id=self.user.data.user_id) is True:
                backend.User.delete_user(user_id=self.user.data.user_id)
                # het is niet meer nodig om nu het window weer tevoorschijn te halen omdat het toch wordt gesloten
                self.menu.clear_all_guis()
                self.menu.set_gui(UserSelectionWindow())
                return True
            else:
                pysg.Popup(f"Gebruiker met naam '{delete_user}' bestaat niet.\n"
                           f"Kies een andere naam.", title="Gebruiker bestaat al", font=self.font)
                self.window.un_hide()
                return False


class AdminLoginMenu(Camillo_GUI_framework.Gui):
    def __init__(self, window_dimensions=(None, None), window_title="Voer gegevens in",
                 *args, **kwargs):
        super().__init__(window_dimensions=window_dimensions,
                         window_title=window_title, *args,
                         **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Text("email:", font=self.font), pysg.Push()],
            [pysg.InputText("", font=self.font, size=(18, 0), key='-EMAIL-')],
            [pysg.Text("password:", font=self.font), pysg.Push()],
            [pysg.InputText("", font=self.font, size=(18, 0), password_char="•", key='-PASSWORD-')],
            [pysg.VPush()],
            [pysg.Button("OK", expand_x=True, font=self.font)]
        ]

    def set_window(self, *args, **kwargs):
        super().set_window(*args, **kwargs)
        self.window["-PASSWORD-"].bind('<Enter>', "<HoverPassword>")
        self.window["-PASSWORD-"].bind('<Leave>', "<UnHoverPassword>")

    def update(self):
        super().update()

        print(self.event)
        if self.event == "-PASSWORD-<HoverPassword>":  # Geeft wachtwoord weer bij hover over input
            self.window["-PASSWORD-"].update(password_char="")

        elif self.event == "-PASSWORD-<UnHoverPassword>":
            self.window["-PASSWORD-"].update(password_char="•")

        if self.event == "OK" and all(self.values):
            login_field = backend.AdminLoginField(email=self.values["-EMAIL-"], password=self.values["-PASSWORD-"])
            succes = backend.Admin.login(login_field=login_field)
            if succes:
                self.menu.back_button()
                assert isinstance(self.menu.current_gui(), UserSelectionWindow)
                self.menu.current_gui().refresh()
                pysg.popup_no_buttons("succes!", non_blocking=True, auto_close=True, auto_close_duration=.75,
                                      no_titlebar=True, font=self.font)
                return True
            else:
                pysg.Popup("Gegevens komen niet overeen", title="Fout", font=self.font)


App.set_gui(gui=UserSelectionWindow())
App.run()
