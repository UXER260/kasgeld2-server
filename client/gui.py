import datetime
import PySimpleGUI as pysg
import backend

import json

with open('config.json', 'r') as f:
    config = json.load(f)

pysg.theme(config['theme'])


class Gui:
    default_window_init_args = {"finalize": True, "enable_close_attempted_event": True}

    def __init__(self, window_title="No Title", font=None,
                 window_dimensions=None, keep_on_top=False,
                 window_is_popup=False,
                 window_init_args_overwrite: dict = None):

        self.window_is_popup = window_is_popup
        self.keep_on_top = keep_on_top or self.window_is_popup
        if window_init_args_overwrite is None:
            window_init_args_overwrite = {}
        self.overwritten_window_args = backend.overwrite_dict_with_dict(
            original_dict=self.default_window_init_args.copy(),
            overwriter_dict=window_init_args_overwrite
        )

        if window_dimensions is None:
            window_dimensions = config["window_size"]
        if font is None:
            font = backend.default_font()

        self.window: None | pysg.Window = None
        self.menu = None

        self.window_title = window_title
        self.window_dimensions = window_dimensions
        self.font = font

        self.event = None
        self.values = None

        self.set_window(old_gui=Menu.current_gui() if Menu.current_gui() else None)

    def update_window_title(self, new_title: str):
        self.window.set_title(title=new_title)
        self.window_title = new_title

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.InputText(self.window_title, font=self.font, enable_events=True)]
        ]

    def set_window(self, old_gui, close_old_window: bool = False):
        layout = self.layout()

        if old_gui is not None:
            if self.window_dimensions == (None, None):
                new_window = pysg.Window(keep_on_top=self.keep_on_top, title=self.window_title,
                                         size=self.window_dimensions,
                                         layout=self.layout(),
                                         **self.overwritten_window_args)
                new_window.hide()
                self.window_dimensions = new_window.size

                new_pos_x = int(old_gui.window.current_location(more_accurate=True)[0] +
                                old_gui.window.size[0] / 2 - self.window_dimensions[0] / 2)
                new_pos_y = int(old_gui.window.current_location(more_accurate=True)[1] +
                                old_gui.window.size[1] / 2 - self.window_dimensions[1] / 2)

                new_window.move(new_pos_x, new_pos_y)
                new_window.un_hide()

            else:
                new_pos_x = int(old_gui.window.current_location(more_accurate=True)[0] +
                                old_gui.window.size[0] / 2 - self.window_dimensions[0] / 2)
                new_pos_y = int(old_gui.window.current_location(more_accurate=True)[1] +
                                old_gui.window.size[1] / 2 - self.window_dimensions[1] / 2)

                new_window = pysg.Window(title=self.window_title, size=self.window_dimensions,
                                         location=(new_pos_x, new_pos_y), layout=self.layout(),
                                         **self.overwritten_window_args)

            if not self.window_is_popup:
                if close_old_window:
                    old_gui.window.close()
                else:
                    old_gui.window.hide()

        else:
            new_window = pysg.Window(title=self.window_title, size=self.window_dimensions, layout=layout,
                                     **self.overwritten_window_args)

        self.window = new_window

    def update(self):
        self.event, self.values = self.window.read()
        if self.event == pysg.WIN_CLOSE_ATTEMPTED_EVENT:
            self.menu.back_button()

        return self.event, self.values


class Menu:
    active = False
    guis: list[Gui] = []

    @classmethod
    def delete_gui(cls, index: int):
        cls.guis[index].window.close()
        del cls.guis[index]

    @classmethod
    def clear_all_guis(cls):
        for _ in range(len(cls.guis)):
            cls.delete_gui(index=0)

    @classmethod
    def current_gui(cls):
        if len(cls.guis) > 0:
            return cls.guis[-1]
        return None

    @classmethod
    def previous_gui(cls):
        return cls.guis[-2]

    @classmethod
    def set_gui(cls, gui: Gui):
        """
        :param gui: A class that inherited from the `Gui` class
        """

        cls.guis.append(gui)
        cls.current_gui().menu = cls

    @classmethod
    def back_button(cls):
        # gaat een gui terug in de `guis` lijst en verwijdert de vorige gui uit de list
        # werkt alleen als oude window niet was gesloten
        if len(cls.guis) <= 1:
            exit_program = pysg.popup_yes_no("Afsluiten?", title="", keep_on_top=True, font=backend.default_font())
            if exit_program == "Yes":
                cls.active = False
                backend.sys.exit(0)
            return

        if not cls.current_gui().window_is_popup:
            new_pos_x = int(
                cls.current_gui().window.current_location(more_accurate=True)[0] + cls.current_gui().window.size[
                    0] / 2 -
                cls.previous_gui().window.size[0] / 2)
            new_pos_y = int(
                cls.current_gui().window.current_location(more_accurate=True)[1] + cls.current_gui().window.size[
                    1] / 2 -
                cls.previous_gui().window.size[1] / 2)

            cls.previous_gui().window.move(new_pos_x, new_pos_y)

        cls.previous_gui().window.un_hide()  # un-hide voor het geval dat de window was ge-hide
        cls.current_gui().window.close()
        del cls.guis[-1]  # wat eerst `cls.previous_gui()` was, is nu dezelfde als `cls.current_gui()`

    @classmethod
    def update(cls):
        if not cls.guis:
            cls.active = False
        cls.current_gui().update()

    @classmethod
    def run(cls):
        assert cls.current_gui is not None, "Makesure `current_gui` is properly set before running."
        cls.active = True
        while cls.active:
            cls.update()


class UserSelectionWindow(Gui):
    def __init__(self, name_list: list[str] = None,
                 window_title="Kies een persoon", *args, **kwargs):
        if name_list is None:
            name_list = backend.User.get_username_list()
        self.name_list = name_list
        super().__init__(window_title=window_title, *args, **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.InputText("", font=self.font, expand_x=True, key='-SEARCH_BAR_FIELD-',
                            enable_events=True)],
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
            userdata = backend.User.get_userdata_by_username(username=username)

            transaction_list = backend.User.get_transaction_list(user_id=userdata.user_id)

            self.menu.set_gui(
                gui=UserOverviewWindow(userdata=userdata, transaction_list=transaction_list)
            )
            return

        elif self.event == "add":
            self.menu.set_gui(gui=AddUserMenu(window_is_popup=True))

    def update_username_list(self, search_name: str | None = None):
        self.name_list = backend.User.get_username_list()
        if self.values["-SEARCH_BAR_FIELD-"]:
            search_name = self.values["-SEARCH_BAR_FIELD-"]

        if search_name is not None:
            self.window['-NAME_LIST-'].update(backend.filter_list(search_name, self.name_list))
            if not self.values["-SEARCH_BAR_FIELD-"]:
                self.window['-SEARCH_BAR_FIELD-'].update(search_name)
        else:
            self.window["-NAME_LIST-"].update(self.name_list)


class UserOverviewWindow(Gui):
    def __init__(self, userdata: backend.RawUserData, transaction_list: list[backend.RawTransactionData],
                 window_title=None, *args,
                 **kwargs):
        if window_title is None:
            window_title = f"Gebruikersoverzicht - {userdata.name}"
        self.userdata = userdata
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
            [pysg.Button(" < ", font=backend.default_font(), key="-BACK_BUTTON-"),
             pysg.Text(f"€{self.userdata.saldo}", font=backend.default_font(), justification="c", expand_x=True,
                       key="-SALDO-"),
             pysg.Button(" ⚙ ", font=backend.default_font(), key="-OPTIONS_BUTTON-")],
            [pysg.Listbox(self.transaction_preview_list, enable_events=True, expand_y=True, expand_x=True,
                          font=backend.default_font(scale=0.7), key="-TRANSACTION_PREVIEW_LIST-")],
            [pysg.Button("Verander Saldo", font=backend.default_font(), expand_x=True, key="-SET_SALDO_BUTTON-")]]

    def update(self):
        super().update()

        if self.event == "-BACK_BUTTON-":
            self.menu.back_button()
            assert isinstance(self.menu.current_gui(), UserSelectionWindow)
            self.menu.current_gui().update_username_list()
        elif self.event == pysg.WIN_CLOSE_ATTEMPTED_EVENT:
            # `self.menu.back_button()`  is niet nodig omdat al is ge-called bij `Menu.update`
            assert isinstance(self.menu.current_gui(), UserSelectionWindow)
            self.menu.current_gui().update_username_list()

        elif self.event == '-TRANSACTION_PREVIEW_LIST-' and len(
                self.window['-TRANSACTION_PREVIEW_LIST-'].get_indexes()) >= 0:
            # get selected transaction
            transaction = self.transaction_list[-1 - self.window['-TRANSACTION_PREVIEW_LIST-'].get_indexes()[0]]
            self.menu.set_gui(
                gui=TransActionDetailsWindow(transaction=transaction, userdata=self.userdata)
            )

        elif self.event == "-SET_SALDO_BUTTON-":
            self.menu.set_gui(
                gui=SetSaldoMenu(userdata=self.userdata)
            )

        elif self.event == "-OPTIONS_BUTTON-":
            self.menu.set_gui(OptionsMenu(userdata=self.userdata))

    def update_window_with_new_userdata(self, new_userdata=None, update_transaction_list=True):
        """
        Update het window met nieuwe gebruikers data
        :param new_userdata: Vervangt `self.userdata` met waarde als waarde niet None is.
        Anders haalt programma de nieuwe data van de server met de huidige user_id
        :param update_transaction_list: Update `self.transaction_list` en `self.transaction_preview_list`
        met data van de server. Vervolgens: `self.window["-TRANSACTION_PREVIEW_LIST-"].update(data van server)`
        """

        if new_userdata is None:
            new_userdata = backend.User.get_userdata(user_id=self.userdata.user_id)

            if self.userdata.name != new_userdata.name:
                self.update_window_title(new_title=f"Gebruikersoverzicht - {new_userdata.name}")

        self.userdata = new_userdata

        if update_transaction_list:
            self.transaction_list = backend.User.get_transaction_list(user_id=self.userdata.user_id)
            self.transaction_preview_list = self.generate_transaction_previews()
            self.window["-TRANSACTION_PREVIEW_LIST-"].update(self.transaction_preview_list)


class TransActionDetailsWindow(Gui):
    def __init__(self, transaction: backend.RawTransactionData, userdata: backend.RawUserData, window_title=None, *args,
                 **kwargs):
        self.transaction = transaction
        self.userdata = userdata
        super().__init__(window_title=window_title, *args, **kwargs)

    def update(self):
        super().update()

        if self.event == "-BACK_BUTTON-":
            self.menu.back_button()

    def layout(self) -> list[list[pysg.Element]]:
        now = datetime.datetime.now()
        datetime_string = now.strftime('%d/%m/%Y %H:%M')
        return [
            [pysg.Button(" < ", font=backend.default_font(), key="-BACK_BUTTON-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=backend.default_font())],
            [pysg.Text('Datum & Tijd', font=backend.default_font(scale=0.7)), pysg.Push(),
             pysg.Text(f"{datetime_string}", font=backend.default_font(scale=0.7),
                       key="-TRANSACTION_DATE-TIME-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=backend.default_font())],
            [pysg.Text('Bedrag', font=backend.default_font(scale=0.7)), pysg.Push(),
             pysg.Text(self.transaction.amount, font=backend.default_font(scale=0.7), key="-AMOUNT-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=backend.default_font())],
            [pysg.Text('Saldo Na Transactie', font=backend.default_font(scale=0.7)), pysg.Push(),
             pysg.Text(self.transaction.saldo_after_transaction, font=backend.default_font(scale=0.7),
                       key="-SALDO_AFTER_TRANSACTION-")],
            [pysg.Text(config['item_separation'][0] * config['item_separation'][1], justification="c",
                       expand_x=True,
                       font=backend.default_font())],
            [pysg.Text('Beschrijving', font=backend.default_font(scale=0.7), justification="c", expand_x=True, )],
            [pysg.Multiline(self.transaction.description, font=backend.default_font(scale=0.7), disabled=True,
                            expand_x=True,
                            size=(0, 7),
                            key="-TRANSACTION_DESCRIPTION-")],
        ]


class SetSaldoMenu(Gui):
    def __init__(self, userdata: backend.RawUserData, window_title=None, *args, **kwargs):
        if window_title is None:
            window_title = f"Pas saldo aan - {userdata.name}"
        self.userdata = userdata
        super().__init__(window_title=window_title, *args, **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Text("Bedrag", font=backend.default_font()), pysg.Push(),
             pysg.DropDown(["-", "+", "op"], "-", readonly=True, font=backend.default_font(), key="-PLUS_MINUS-"),
             pysg.InputText("", font=backend.default_font(), expand_x=True, key='-AMOUNT-')],
            [pysg.Text("Titel:", font=backend.default_font()), pysg.Push(),
             pysg.InputText("", font=backend.default_font(), expand_x=True, key='-TRANSACTION_TITLE-')],
            [pysg.Text("Beschrijving", font=backend.default_font(), expand_x=True)],
            [pysg.Multiline(font=backend.default_font(), expand_x=True, expand_y=True, size=(0, 7),
                            key="-TRANSACTION_DESCRIPTION-")],
            [pysg.Button("OK", expand_x=True, font=backend.default_font(), key="OK")]
        ]

    def update(self):
        super().update()

        if self.event == "OK" and all(self.values.values()):
            amount = backend.check_string_valid_float(self.values["-AMOUNT-"])
            if not backend.check_valid_saldo(saldo=amount):
                return

            plus_minus = self.values["-PLUS_MINUS-"]
            if plus_minus == "-":
                saldo_after_transaction = self.userdata.saldo - amount
            elif plus_minus == "+":
                saldo_after_transaction = self.userdata.saldo + amount
            else:
                saldo_after_transaction = amount

            transaction_title = self.values["-TRANSACTION_TITLE-"]
            transaction_description = self.values["-TRANSACTION_DESCRIPTION-"]

            transaction_details = backend.TransactionField(
                saldo_after_transaction=saldo_after_transaction,
                title=transaction_title,
                description=transaction_description,
            )

            backend.User.set_saldo(user_id=self.userdata.user_id, transaction_details=transaction_details)
            self.menu.back_button()
            # `type(self.menu.current_gui())` MOET `UserOverviewWindow` zijn
            assert isinstance(self.menu.current_gui(), UserOverviewWindow)
            self.menu.current_gui().update_window_with_new_userdata()  # `current_gui` is veranderd door `back_button`


class AddUserMenu(Gui):
    def __init__(self, window_is_popup=True, window_dimensions=(None, None), window_title: str = "Voeg Gebruiker Toe",
                 *args, **kwargs):
        super().__init__(window_is_popup=window_is_popup, window_dimensions=window_dimensions,
                         window_title=window_title,
                         *args, **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Text(f"Naam:", font=backend.default_font(), expand_x=True, expand_y=True), pysg.Push(),
             pysg.InputText("", font=backend.default_font(), size=(15, 0), key='-ACCOUNT_NAME-')],
            [pysg.Text(f"Saldo:", font=backend.default_font(), expand_x=True, expand_y=True), pysg.Push(),
             pysg.InputText("", font=backend.default_font(), size=(15, 0), key='-SALDO-')],
            [pysg.Button("OK", expand_x=True, font=backend.default_font(), key="OK")]
        ]

    def update(self):
        super().update()
        if self.event == "OK" and all(self.values.values()):
            username = self.values["-ACCOUNT_NAME-"]
            saldo = self.values["-SALDO-"]
            if not backend.check_string_valid_float(saldo):
                return
            if not backend.check_valid_saldo(saldo=saldo):
                return

            if backend.User.get_user_exists_by_username(username):
                pysg.Popup(f"Gebruiker met naam '{username}' bestaat al.\n"
                           f"Kies een andere naam", title="Gebruiker bestaat al", font=backend.default_font(),
                           keep_on_top=True)
                return

            userdata = backend.AddUser(
                name=username,
                saldo=saldo
            )
            backend.User.add_user(userdata=userdata)

            self.menu.back_button()
            assert isinstance(self.menu.current_gui(), UserSelectionWindow)
            self.menu.current_gui().update_username_list(search_name=userdata.name)


class OptionsMenu(Gui):
    def __init__(self, userdata: backend.RawUserData, window_is_popup=True, window_dimensions=(None, None),
                 window_title=None,
                 *args, **kwargs):
        if window_title is None:
            window_title = f"Opties - {userdata.name}"
        self.userdata = userdata
        super().__init__(window_is_popup=window_is_popup, window_dimensions=window_dimensions,
                         window_title=window_title, *args,
                         **kwargs)

    def layout(self) -> list[list[pysg.Element]]:
        return [
            [pysg.Button("Hernoem", font=backend.default_font(), size=(9, 0), key='-RENAME_BUTTON-')],
            [pysg.Button("Verwijder", font=backend.default_font(), size=(9, 0), key='-DELETE_BUTTON-')],
        ]

    def update(self):
        super().update()

        if self.event == "-RENAME_BUTTON-":
            self.window.hide()
            new_username = pysg.popup_get_text("Voor nieuwe gebruikersnaam is:", font=backend.default_font(),
                                               keep_on_top=True)
            if not new_username:
                self.window.un_hide()
                return

            if not backend.User.get_user_exists_by_username(username=new_username) is True:
                backend.User.rename_user(user_id=self.userdata.user_id, new_username=new_username)
                # het is niet meer nodig om nu het window weer tevoorschijn te halen omdat het toch wordt gesloten
                self.menu.back_button()
                assert isinstance(self.menu.current_gui(), UserOverviewWindow)
                self.menu.current_gui().update_window_with_new_userdata()

            else:
                pysg.Popup(f"Gebruiker met naam '{new_username}' bestaat al.\n"
                           f"Kies een andere naam", title="Gebruiker bestaat al", font=backend.default_font())
                self.window.un_hide()

        elif self.event == "-DELETE_BUTTON-":
            self.window.hide()
            delete_user = pysg.popup_yes_no(
                f"Weet je zeker dat je het account `{self.userdata.name}` wilt verwijderen?\n"
                f"Dit kan niet ongedaan worden gemaakt.", title="Verwijder Account",
                font=backend.default_font(), keep_on_top=True)
            if delete_user != "Yes":
                return

            if backend.User.get_user_exists_by_id(user_id=self.userdata.user_id) is True:
                backend.User.delete_user(user_id=self.userdata.user_id)
                # het is niet meer nodig om nu het window weer tevoorschijn te halen omdat het toch wordt gesloten
                self.menu.clear_all_guis()
                self.menu.set_gui(UserSelectionWindow())
                return
            else:
                pysg.Popup(f"Gebruiker met naam '{delete_user}' bestaat niet.\n"
                           f"Kies een andere naam", title="Gebruiker bestaat al", font=backend.default_font())
                self.window.un_hide()
