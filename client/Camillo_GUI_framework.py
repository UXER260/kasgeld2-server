# client/Camillo_GUI_framework
# Zelf gemaakt framework voor user interface
import backend
from imports import *

with open('config.json', 'r') as f:
    config = json.load(f)

pysg.theme(config["theme"])


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

        self.set_window(old_gui=App.current_gui() if App.current_gui() else None)

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


class App:
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
