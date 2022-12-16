import json

from textual.app import App
from textual.widgets import Static, Header, Footer
from textual.binding import Binding
from textual.geometry import Size
from textual.reactive import Reactive
from textual.events import Click

from rich.text import Text
from rich.color import Color
from rich.style import Style

# Infinite Minesweeper
# k01e @ github.com/k01e-01 @ k01e.alm07@gmail.com
# 2022-12-16
# MIT License


class State(dict):
    """Stores information about the current state of the game."""

    FLAG   = 10
    EMPTY  = 11
    EOL    = 12

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self["score"] = 0
        self["offset"] = [0, 0]
    
    def __getattr__(self, name: str):
        try: return self[name]
        except KeyError: raise AttributeError(name)

    @staticmethod
    def at(x, y):
        return f"cell-{x}-{y}"
    
    def render(self, x1, y1, x2, y2):
        for y in range(y1, y2+1):
            for x in range(x1, x2+1):
                try:
                    yield self[self.at(x, y)]
                except KeyError:
                    yield self.EMPTY
            yield self.EOL


class View(Static):
    """Enables the user to interact with the state of the game."""

    CELL_LOOKUP: dict[int, tuple[str, Color]] = {
        -1:     ("  ", Color.parse("black")),

        0:      (" 0", Color.parse("white")),
        1:      (" 1", Color.parse("blue")),
        2:      (" 2", Color.parse("green")),
        3:      (" 3", Color.parse("red")),
        4:      (" 4", Color.parse("purple")),
        5:      (" 5", Color.parse("yellow")),
        6:      (" 6", Color.parse("cyan")),
        7:      (" 7", Color.parse("magenta")),
        8:      (" 8", Color.parse("black")),

        State.FLAG:     (" F", Color.parse("red")),
        State.EMPTY:    ("  ", Color.parse("black")),
        State.EOL:      ("\n", Color.parse("black"))
    }

    def on_click(self, event: Click):
        pass

    def redraw(self):
        xlim: int = self.app.size.width
        ylim: int = self.app.size.height - 2
        xoffset: int = self.app.state.offset[0]
        yoffset: int = self.app.state.offset[1]
        state: State = self.app.state
        togglenums: bool = self.app.togglenums

        text = Text()
        for item in state.render(
            xlim // 2 - xoffset, 
            ylim // 2 - yoffset, 
            -(xlim // 2) - xoffset, 
            -(ylim // 2) - yoffset
        ):
            text.append(
                text=self.CELL_LOOKUP[item if togglenums else -1][0],
                style=Style(color="white", bgcolor=self.CELL_LOOKUP[item][1])
            )
            
        self.update(text)


class Minesweeper(App):
    """An infinitely generative minesweeper game."""

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit")
    ]

    state = State()
    togglenums = Reactive(True)

    def compose(self):
        yield Header()
        v = View()
        v.styles.overflow = "hidden"
        yield v
        yield Footer()



if __name__ == "__main__":
    Minesweeper().run()