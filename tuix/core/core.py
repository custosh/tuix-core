import os
import re
import sys
import time
import shutil
from typing import Union
import copy
import wcwidth

if sys.platform == "win32":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

def text_color(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


def background_color(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"


def is_rgb(value):
    if not (isinstance(value, tuple) and len(value) == 3):
        return False
    for x in value:
        if isinstance(x, float):
            if not 0.0 <= x <= 255.0:
                return False
        elif isinstance(x, int):
            if not 0 <= x <= 255:
                return False
        else:
            return False
    return True


def blend_shadow(bg, fg, intensity=0.3):
    return tuple(
        int(bg[i] * (1 - intensity) + fg[i] * intensity)
        for i in range(3)
    )


def visual_width(s):
    return sum(wcwidth.wcwidth(ch) for ch in s)


class TuixEngine():
    def __init__(self):
        self.styles = Styles(self)
        self.components = ComponentAPI(self)
        self.layout = LayoutEngine(self)
        self.render = RenderEngine(self)
        self.input = InputHandler(self)


class Styles():
    def __init__(self, main):
        self.main = main
        self.types = ["adaptive", "strict"]
        self.styles = ["classic"]
        self.styles_config = {
            "classic": {
                "shadow": False,
                "background": 0,
                "prompt_background": (0, 0, 0),
                "border": (255, 255, 255),
                "text_color": (255, 255, 255),
                "text_background": False,
                "unselected_background": False,
                "unselected_text": (255, 255, 255),
                "selected_background": (255, 255, 255),
                "selected_text": (0, 0, 0),
                "text": {
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "dim": False
                }
            }
        }   
        self.type = "strict"
        self.style = "classic"
        self.custom_styles = {
            "shadow": None,
            "background": None,
            "prompt_background": None,
            "border": None,
            "text_color": None,
            "text_background": None,
            "unselected_background": None,
            "unselected_text": None,
            "selected_background": None,
            "selected_text": None,
            "text": {
                "bold": None,
                "italic": None,
                "underline": None,
                "dim": None
            }
        }
        self.cached_styles = self._precompute_styles()

    def set_type(self, type: str):
        if type in self.types:
            self.type = type
        else:
            raise ValueError(f"Unknown prompt type \"{type}\"")

    def set_style(self, style: str):
        if style in self.styles:
            self.style = style
        else:
            raise ValueError(f"Unknown prompt style \"{style}\"")

    def set_custom_style(self, *, key: str, option: str = None, value: Union[tuple, bool]):
        if key in ["background", "prompt_background", "border", "unselected_text", "selected_background",
                       "selected_text", "text_color"]:
            self._set_custom_style_onlyrgb_handler(key=key, value=value)
        elif key in ["shadow", "text_background", "unselected_background"]:
            self._set_custom_style_bool_rgb_handler(key=key, value=value)
        elif key in ["text"]:
            self._set_custom_style_options_handler(option=option, value=value, key=key)
        else:
            raise ValueError(f"Unknown key \"{key}\"")

    def _set_custom_style_onlyrgb_handler(self, *, key: str, value: tuple):
        if is_rgb(value):
            self.custom_styles[key] = value
        else:
            raise ValueError("Value must be rgb tuple")
        self._cache_styles()

    def _set_custom_style_bool_rgb_handler(self, *, key: str, value: bool):
        if isinstance(value, bool):
            if value:
                if key == "shadow":
                    self.custom_styles[key] = blend_shadow(
                        self.custom_styles["background"] if self.custom_styles["background"] != None else
                        self.styles_config[self.style]["background"],
                        self.custom_styles["prompt_background"] if self.custom_styles["prompt_background"] != None else
                        self.styles_config[self.style]["prompt_background"])
                elif key in ["text_background", "unselected_background"]:
                    raise ValueError("Value can't be True")
            else:
                self.custom_styles[key] = False
        elif is_rgb(value):
            self.custom_styles[key] = value
        else:
            raise ValueError(f"Value must be boolean or rgb tuple")
        self._cache_styles()

    def _set_custom_style_options_handler(self, *, option: str, value: bool, key: str):
        if option in self.custom_styles[key]:
            if isinstance(value, bool):
                self.custom_styles[key][option] = value
            else:
                raise ValueError("Value must be boolean")
        else:
            raise ValueError(f"Unknown option \"{option}\" for key \"{key}\"")
        self._cache_styles()

    def remove_custom_style(self, key: Union[str, list], option: Union[str, list] = None):
        if isinstance(key, list):
            for word in key:
                if isinstance(word, str):
                    if word in self.custom_styles:
                        if word not in ["text"]:
                            self.custom_styles[word] = None
                        else:
                            raise ValueError("This style doesn't support removing using list")
        else:
            if key in self.custom_styles:
                if key not in ["text"]:
                    self.custom_styles[key] = None
                else:
                    if isinstance(option, str):
                        if option in self.custom_styles[key]:
                            self.custom_styles[key][option] = None
                    elif isinstance(option, list):
                        for opt in option:
                            if opt in self.custom_styles[key]:
                                self.custom_styles[key][opt] = None
                    else:
                        raise ValueError("Option must be string or list")

        self._cache_styles()

    def define_style(self, *, name: str, config: dict):
        keys = []
        new_keys = []
        for name_, data in self.styles_config["classic"].items():
            keys.append(name_)
        for name_, data in config.items():
            new_keys.append(name_)

        if set(keys) != set(new_keys):
            raise ValueError("Style config keys do not match the required keys")

        if name not in self.styles_config:
            self.styles_config[name] = config
            self.styles.append(name)

    def _precompute_styles(self):
        """
        Internal API.
        Computes and returns the fully resolved style dictionary
        (after applying preset + custom cascade) for RenderAPI consumption.
        """
        precomputed_styles = copy.deepcopy(self.styles_config[self.style])
        styles_config = []
        for name, data in self.styles_config[self.style].items():
            styles_config.append(name)

        for name, data in self.custom_styles.items():
            if name not in styles_config:
                raise ValueError(f"Unknown style key \"{name}\"")

            if data != None:
                precomputed_styles[name] = data

        return precomputed_styles

    def _cache_styles(self):
        """
        Internal API.
        Caches the precomputed styles for faster access.
        """
        self.cached_styles = self._precompute_styles()


class ComponentAPI:
    """ Component management API
    self.objects structure:
    { "id": {"type": "choice", "label": "Select an option:", "choices": [[{name: "Option 1", action: "action_1"}], [{name: "Option 2", action: "action_2"}]...]}}  # every sub-list is a 1 row with buttons in menu
    { "id": {"type": "progress_bar", "label": "Loading...", "progress": 50 } }
    { "id": {"type": "text_input", "label": "Enter your name:", "default_text": "" } }

    ToDo — Validation System Upgrade
    - [ ] Split `set_property()` into type-specific validators:
        - _validate_choice()
        - _validate_progress_bar()
        - _validate_text_input()
    - [ ] Add property schema metadata per component
    - [ ] Introduce validators registry for dynamic dispatch
    - [ ] Prepare testing harness for validator integrity
    """

    def __init__(self, main):
        self.main = main
        self.objects = {}
        self.types = ["choice", "progress_bar", "text_input"]
        self.properties = {
            "label": self.types,
            "choices": ["choice"],
            "progress": ["progress_bar"],
            "default_text": ["text_input"]
        }

    def create(self, type: str, id: str, classes: list = []):
        if id in self.objects:
            raise ValueError(f"Object with id \"{id}\" already exists")
        if type not in self.types:
            raise ValueError(f"Unknown object type \"{type}\"")
        self.objects[id] = {"type": type,
                                       "layout": {"margin_top_mode": "custom", "margin_left_mode": "custom",
                                                  "width_modifier": 0.5, "height_modifier": 0.5, "margin_top_modifier": 0.0,
                                                  "margin_left_modifier": 0.0}}
        if type in self.properties["label"]:
            self.objects[id]["label"] = ""
        if type in self.properties["choices"]:
            self.objects[id]["choices"] = []
        if type in self.properties["progress"]:
            self.objects[id]["progress"] = 0
        if type in self.properties["default_text"]:
            self.objects[id]["default_text"] = ""

    def set_property(self, *, id: str, param: str, value):
        if id not in self.objects:
            raise ValueError(f"Object with id \"{id}\" does not exist")
        if param not in self.properties:
            raise ValueError(f"Unknown property name \"{param}\"")
        if self.objects[id]["type"] not in self.properties[param]:
            raise ValueError(
                f"Property \"{param}\" is not applicable for object type \"{self.objects[id]['type']}\"")
        self.objects[id][param] = value

    def get(self, id: str):
        if id not in self.objects:
            raise ValueError(f"Object with id \"{id}\" does not exist")
        return self.objects[id]

    def delete(self, id: str):
        if id not in self.objects:
            raise ValueError(f"Object with id \"{id}\" does not exist")
        del self.objects[id]


class LayoutEngine():
    """
    Layout management API
    self.objects structure:
    obj["layout"] = {
        "x": width_modifier * terminal_width,
        "y": height_modifier * terminal_height,
        "margin_top": margin_top * terminal_height,
        "margin_left": margin_left * terminal_width,
        "margin_top_mode": "custom"
        "margin_left_mode": "custom"
        "corners": {
            "top_left": (margin_left, margin_top),
            "bottom_right": (margin_left + width_modifier * terminal_width, margin_top + height_modifier * terminal_height),
        }
    }

    if user want centred object use this:
    obj["layout"] = {
        "x": width_modifier * terminal_width,
        "y": height_modifier * terminal_height,
        "margin_top": (terminal_rows - int(height_modifier * terminal_rows)) // 2,
        "margin_left": (terminal_cols - int(width_modifier * terminal_cols)) // 2,
        "margin_top_mode": "centered"
        "margin_left_mode": "centered"
        "corners": {
            "top_left": (margin_left, margin_top),
            "bottom_right": (margin_left + width_modifier * terminal_width, margin_top + height_modifier * terminal_height),
        }
    }
    """

    def __init__(self, main):
        self.main = main
        self.objects = self.main.components.objects

    def set_dimensions(self, *, id: str, width_modifier: float = None, height_modifier: float = None,
                       margin_top: float = None, margin_left: float = None):
        if id not in self.objects:
            raise ValueError(f"Object with id \"{id}\" does not exist")
        if width_modifier is None and height_modifier is None and margin_top is None and margin_left is None:
            raise ValueError("At least one dimension parameter must be provided")

        for param, value in {"width_modifier": width_modifier, "height_modifier": height_modifier,
                             "margin_top": margin_top, "margin_left": margin_left}.items():
            if value is not None:
                if (param == "margin_top" and self.objects[id]["layout"]["margin_top_mode"] == "centered") or (
                        param == "margin_left" and self.objects[id]["layout"]["margin_left_mode"] == "centered"):
                    raise ValueError(f"Cannot set margin when \"{param}\" mode is set to \"centered\"")
                if not (0.0 <= value <= 1.0):
                    raise ValueError(f"\"{param}\" parameter must be between 0.0 and 1.0")

                self.objects[id]["layout"][param] = value

    def margin_mode(self, *, id: str, param: Union[str, list], mode: str):
        if id not in self.objects:
            raise ValueError(f"Object with id \"{id}\" does not exist")
        if not isinstance(param, list):
            param = [param]
        for value in param:
            if value not in ["margin_top", "margin_left"]:
                raise ValueError(f"Unknown parameter type \"{value}\"")
        if mode not in ["centered", "custom"]:
            raise ValueError(f"Unknown margin mode \"{mode}\" for parameter \"{param}\"")

        for value in param:
            self.objects[id]["layout"][f"{value}_mode"] = mode


    def _compute_all(self):
        terminal_cols, terminal_rows = shutil.get_terminal_size()
        for id, obj in self.objects.items():
            width_modifier = self.objects[id]["layout"]["width_modifier"]
            height_modifier = self.objects[id]["layout"]["height_modifier"]
            margin_top = self.objects[id]["layout"]["margin_top_modifier"]
            margin_left = self.objects[id]["layout"]["margin_left_modifier"]
            self.objects[id]["layout"] = {
                "width_modifier": width_modifier,
                "height_modifier": height_modifier,
                "margin_top_modifier": margin_top,
                "margin_left_modifier": margin_left,
                "margin_top_mode": obj["layout"]["margin_top_mode"],
                "margin_left_mode": obj["layout"]["margin_left_mode"],
                "x": int(width_modifier * terminal_cols),
                "y": int(height_modifier * terminal_rows),
                "margin_top": int(margin_top * terminal_rows) if obj["layout"]["margin_top_mode"] == "custom" else (terminal_rows - int(height_modifier * terminal_rows)) // 2,
                "margin_left": int(margin_left * terminal_cols) if obj["layout"]["margin_left_mode"] == "custom" else (terminal_cols - int(width_modifier * terminal_cols)) // 2,
                "corners": {
                    "top_left": (int(margin_left * terminal_cols), int(margin_top * terminal_rows)),
                    "bottom_right": (int((margin_left + width_modifier) * terminal_cols),
                                     int((margin_top + height_modifier) * terminal_rows))
                }
            }

class RenderEngine:
    def __init__(self, main):
        self.main = main
        self.objects = self.main.components.objects
        self.selected_row = 0
        self.selected_index = 0

    def draw(self):
        os.system("cls" if sys.platform == "win32" else "clear")
        self.main.layout._compute_all()
        if len(self.objects) == 1:
            for key, obj in self.objects.items():
                if obj["type"] == "choice":
                    print("\n" * obj["layout"]["margin_top"], end="")
                    print(" " * obj["layout"]["margin_left"] + "┏" + "━" * (obj["layout"]["x"] - 2) + "┓")
                    self._draw_choice(obj, obj["label"])
                else:
                    raise NotImplementedError("Only choice prompt is available now")
        elif len(self.objects) == 0:
            raise ValueError("Must be initialized at least 1 object")
        else:
            raise NotImplementedError("Multi-modal layout system is still in development")

    def _wrap_and_center(self, text: str, max_width: int) -> list[str]:
        """Wraps text to max_width, but centers block horizontally."""
        tokens = []
        for part in text.split("\n"):
            if part:
                tokens.extend(re.findall(r'\S+|\s+', part))
            tokens.append("\n")

        lines, current, line_len = [], "", 0
        for token in tokens:
            if token == "\n":
                lines.append(current.rstrip())
                current = ""
                line_len = 0
                continue
            token_len = len(token)
            if line_len + token_len > max_width:
                lines.append(current.rstrip())
                current = token
                line_len = token_len
            else:
                current += token
                line_len += token_len
        if current.strip():
            lines.append(current.rstrip())

        left_pad = 0
        if lines:
            gap = max_width - len(lines[0])
            left_pad = gap // 2

        return [(" " * left_pad + line + " " * (max_width - len(line) - left_pad)) for line in lines]

    def _draw_buttons(self, *, obj, choices: list, max_width: int, max_height: int) -> None:
        if not choices:
            raise ValueError("Choices list can't be empty")

        layout = obj["layout"]
        rendered_rows = []

        for row in choices:
            row_parts = []
            for choice in row:
                text = choice["name"]
                if visual_width(text) > max_width - 4:
                    chunk, pieces = "", []
                    for ch in text:
                        if visual_width(chunk + ch) >= max_width - 4:
                            pieces.append(chunk)
                            chunk = ch
                        else:
                            chunk += ch
                    if chunk:
                        pieces.append(chunk)
                    text = " ".join(pieces)
                row_parts.append(text)
            rendered_rows.append("    ".join(row_parts))

        total_rows = min(len(rendered_rows), max_height)
        visible_rows = rendered_rows[-total_rows:]
        start_y = max_height - total_rows
        lines_to_render = []

        for idx, text_line in enumerate(visible_rows):
            row_width = visual_width(text_line)
            left_offset = max((max_width - row_width) // 2, 0)
            lines_to_render.append({
                "text": text_line,
                "left_offset": left_offset,
                "y_offset": start_y + idx,
            })

        print(
            (" " * layout["margin_left"] + "┃" + " " * (layout["x"] - 2) + "┃\n")
            * (max_height - len(lines_to_render) * 2),
            end="",
        )

        for row_idx, line in enumerate(lines_to_render):
            inner_space_left = " " * line["left_offset"]
            inner_space_right = " " * (
                layout["x"] - 2 - line["left_offset"] - visual_width(line["text"])
            )

            if row_idx == self.selected_row:
                highlighted = ""
                segments = line["text"].split("    ")
                for idx, segment in enumerate(segments):
                    if idx == self.selected_index:
                        background_col = self.main.styles.custom_styles['selected_background'] if is_rgb(self.main.styles.custom_styles['selected_background']) else self.main.styles.styles_config[self.main.styles.style]['selected_background']
                        text_col = self.main.styles.custom_styles['selected_text'] if is_rgb(self.main.styles.custom_styles['selected_text']) else self.main.styles.styles_config[self.main.styles.style]['selected_text']

                        highlighted += (("    " if idx != 0 else "") + f"{background_color(*background_col)}{text_color(*text_col)}{segment.strip()}\x1b[0m" + ("    " if idx == 0 else ""))
                    else:
                        highlighted += f"{segment.strip()}"
                line_text = highlighted.rstrip()
            else:
                line_text = line["text"]

            print(
                " " * layout["margin_left"]
                + "┃"
                + inner_space_left
                + line_text
                + inner_space_right
                + "┃"
            )
            print(
                " " * layout["margin_left"] + "┃" + " " * (layout["x"] - 2) + "┃"
            )

    def _draw_choice(self, obj, text: str):
        text = self._wrap_and_center(text=text, max_width=(obj["layout"]["x"] - 4))
        layout = obj["layout"]

        print(" " * layout["margin_left"] + "┃" + " " * (layout["x"] - 2) + "┃")
        for line in text:
            print(" " * layout["margin_left"] + "┃ " + line + " ┃")
        print(" " * layout["margin_left"] + "┃" + " " * (layout["x"] - 2) + "┃")

        self._draw_buttons(
            obj=obj,
            choices=obj["choices"],
            max_height=(layout["y"] - len(text) - 5),
            max_width=(layout["x"] - 4),
        )

        print(" " * layout["margin_left"] + "┃" + " " * (layout["x"] - 2) + "┃")
        print(" " * layout["margin_left"] + "┗" + "━" * (layout["x"] - 2) + "┛")

        self.main.input.listen(choices=obj["choices"])

    def _handle_selection_change(self, key: str, choices: list):
        if not choices:
            return

        if key == "up":
            self.selected_row = max(0, self.selected_row - 1)
            self.selected_index = min(
                self.selected_index, len(choices[self.selected_row]) - 1
            )
        elif key == "down":
            self.selected_row = min(len(choices) - 1, self.selected_row + 1)
            self.selected_index = min(
                self.selected_index, len(choices[self.selected_row]) - 1
            )
        elif key == "left":
            self.selected_index = max(0, self.selected_index - 1)
        elif key == "right":
            self.selected_index = min(
                len(choices[self.selected_row]) - 1, self.selected_index + 1
            )

        self._refresh(selected_row=self.selected_row, selected_index=self.selected_index)

    def _refresh(self, *, selected_row=None, selected_index=None):
        if selected_row is not None:
            self.selected_row = selected_row
        if selected_index is not None:
            self.selected_index = selected_index

        os.system("cls" if sys.platform == "win32" else "clear")
        self.draw()

class InputHandler:
    def __init__(self, main):
        self.main = main
        self.selected_row = 0
        self.selected_index = 0
        self.running = True

    def get_key(self):
        if sys.platform == "win32":
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b"\xe0", b"\x00"):
                    key = msvcrt.getch()
                    code = key.decode(errors="ignore")
                    mapping = {
                        "H": "up",
                        "P": "down",
                        "K": "left",
                        "M": "right"
                    }
                    return mapping.get(code)
                elif key in (b"\r", b"\n"):
                    return "enter"
            return None

        else:
            import termios, tty, select, sys as _sys
            fd = _sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                rlist, _, _ = select.select([_sys.stdin], [], [], 0.1)
                if rlist:
                    ch = _sys.stdin.read(1)
                    if ch == "\x1b":
                        seq = _sys.stdin.read(2)
                        mapping = {
                            "[A": "up",
                            "[B": "down",
                            "[C": "right",
                            "[D": "left"
                        }
                        return mapping.get(seq)
                    elif ch in ["\r", "\n"]:
                        return "enter"
                return None
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


    def listen(self, choices:list):
        while self.running:
            key = self.get_key()
            if not key:
                time.sleep(0.05)
                continue

            if key == "up":
                self.selected_row = max(0, self.selected_row - 1)
                self.selected_index = 0
            elif key == "down":
                self.selected_row = min(len(choices) - 1, self.selected_row + 1)
                self.selected_index = 0
            elif key == "left":
                self.selected_index = max(0, self.selected_index - 1)
            elif key == "right":
                self.selected_index = min(len(choices[self.selected_row]) - 1, self.selected_index + 1)
            elif key == "enter":
                os.system("cls" if sys.platform == "win32" else "clear")
                print(f"Selected index: {self.selected_index}")
                self.running = False

            self.main.render._refresh(selected_row=self.selected_row, selected_index=self.selected_index)
