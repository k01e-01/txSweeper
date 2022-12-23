import json
import random
import asyncio
from types import SimpleNamespace
from typing import Any
from itertools import product

from textual.app import App
from textual.widgets import Static, Header, Footer
from textual.binding import Binding
from textual.events import Click

from rich.color import Color
from rich.style import Style
from rich.text import Text

# txSweeper
# k01e @ github.com/k01e-01 @ k01e.alm07@gmail.com
# 2022-12-16
# MIT License


# to avoid recursive interception
intercept_blacklist = [
    "score",
    "seed",
    "offset",
    "invsoffset",
    "initclick",
    "_intercept_callback",
]


class State(SimpleNamespace):
    """Stores information about the current state of the game."""

    FLAG   = 10
    EMPTY  = 11
    EOL    = 12
    RESET  = 13


    def __init__(self, intercept_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.score = 0
        self.seed = random.randint(0, (2**32)-1)
        self.offset = [0, 0]
        self.invsoffset = 0
        self.initclick = True
        self._intercept_callback = intercept_callback 
        # used for keeping track of score
    

    # for dict-like access
    def __getitem__(self, key):                
        try:
            return self.__getattribute__(key)
        except AttributeError:
            return None
    def __setitem__(self, key, value):
        return self.__setattr__(key, value)
    def __delitem__(self, key):
        return self.__delattr__(key)

    # for intercepting changes to keep track of score
    def __setattr__(self, __name: str, __value: Any) -> None:      
        if not __name in intercept_blacklist: self._intercept_callback()
        return super().__setattr__(__name, __value)
    def __delattr__(self, __name: str) -> None:
        if not __name in intercept_blacklist: self._intercept_callback()
        return super().__delattr__(__name)


    @staticmethod
    def at(x, y):               # cell identifier
        """Returns the id of the cell at the given position."""
        return f"cell-{x}-{y}"
    
    @staticmethod
    def is_bomb(x, y, seed):   # 4/25 chance of being a bomb
        """Returns whether the cell at the given position is a bomb."""
        return abs(hash((x, y, seed))) % 25 < 4
    

    def render(self, x1, y1, x2, y2):  
        """Yeilds the values of the cells in the given range."""
        r = lambda k, l: range(k, l+1)

        delta_y = y2
        for y, x in product(r(y2, y1), r(x2, x1)):
            if y != delta_y: # delta_y is used to print EOLs at the right times
                yield self.EOL
                delta_y = y
            ret = self[State.at(x, y)]
            yield ret if ret is not None else self.EMPTY # if the cell is not set, return EMPTY
            

class View(Static):
    """Enables the user to interact with the state of the game."""

    LEFTMOUSE = 1
    RIGHTMOUSE = 3

    # this is used down in redraw()
    CELL_LOOKUP: dict[int, tuple[str, Color]] = {
        -1: ("..", "black"  ),  # style for togglenums off, text not important

        0:  (" 0", "white"  ),
        1:  (" 1", "blue"   ),
        2:  (" 2", "green"  ),
        3:  (" 3", "red"    ),
        4:  (" 4", "purple" ),  # self explanatory
        5:  (" 5", "yellow" ),
        6:  (" 6", "cyan"   ),
        7:  (" 7", "magenta"),
        8:  (" 8", "black"  ),

        State.FLAG:     (" F", "red"    ),  # flag
        State.EMPTY:    ("..", "black"  ),  # empty cell
        State.EOL:      ("\n", "white"  ),  # end of line, style not important
    }


    # initial draw
    def on_compose(self):
        self.redraw()


    async def on_click(self, event: Click):
        if self.app.gameovered:
            return
        
        # math, to get the cell the user clicked on
        # this took me far too long
        state = self.app.state
        xoffset: int = state.offset[0]
        yoffset: int = state.offset[1]
        xlim: int = self.app.size.width // 4 - 1
        ylim: int = self.app.size.height // 4
        x = int((event.x + 0.5) // 2) - (xlim + xoffset)
        y = int((event.y / 2 - (ylim + yoffset / 2)) * 2) - 1
        button = event.button

        deltatitle = self.app.title
        self.app.title = "txSweeper - Calculating..."
        await asyncio.sleep(0.01)  # this is needed to update the title
        self.calc(x, y, button)
        if not self.app.gameovered:
            self.app.title = deltatitle
        if button == 1: self.app.bell()


    def calc(self, x: int, y: int, button: bool, depth: int = 0):
        """Calculates the result of a click on a cell."""

        state: State = self.app.state
        seed = state.seed

        getresult = lambda: sum(map(
            lambda t: int(State.is_bomb(t[1], t[0], seed)),  # if it's a bomb, return 1, else 0
            product(range(y-1, y+2), range(x-1, x+2))        # get all the surrounding cells
        ))

        # make sure that the first click is always 0
        if state.initclick:
            state.initclick = False
            while getresult() != 0:
                state.offset[0] -= 1
                state.invsoffset -= 1
                x += 1
            self.log(state.offset)


        # if the cell is already set, don't do anything (unless it's a flag)
        if State.at(x, y) in vars(state).keys() and state[State.at(x, y)] != State.FLAG:
            return

        result = State.EMPTY # this shouldnt ever get through... hopefully

        if button == self.LEFTMOUSE:
            if State.is_bomb(x, y, seed):
                self.app.game_over()
                return
            
            # get the number of bombs in the surrounding cells
            result = getresult()

        if button == self.RIGHTMOUSE:  # toggle flag
            result = State.FLAG if not state[State.at(x, y)] == State.FLAG else State.RESET

        if result == State.RESET:  # if the flag was toggled off, delete cell
            del state[State.at(x, y)]
        else:
            state[State.at(x, y)] = result
        
        # recurse if the cell doesn't have a mine nearby
        if result == 0 and depth < 100: 
            for ny, nx in product(range(y-1, y+2), range(x-1, x+2)):
                self.calc(nx, ny, self.LEFTMOUSE, depth + 1)
        
        if depth == 0:
            self.calcscore()
            self.app.update_title()

        self.redraw()  # hey!


    def calcscore(self):
        """Calculates the score of the game."""

        state = self.app.state
        score = 0
        flags = 0

        for key, val in vars(state).items():
            if key.split("-")[0] != "cell":
                continue
            
            # 0 -> 1, 1 -> 1, 2 -> 2 etc
            if val == 0:
                score += 1
            if val < 10:
                score += val
            if val != State.FLAG:
                continue  # only flags will pass
            
            # if block so players cant just spam flags
            if flags // len(vars(state).values()) < 0.05:   # 5% of the cells are flags
                score += 5
            elif flags // len(vars(state).values()) < 0.1:  # 10% of the cells are flags
                score += 3
            elif flags // len(vars(state).values()) < 0.2:  # 20% of the cells are flags
                score += 1
        
            flags += 1
        
        state.score = score
        self.app.update_title()


    def redraw(self):
        """Redraw the screen."""

        # more arbitrary math
        # more of my time gone testing different numbers
        xlim: int = self.app.size.width // 4 - 1
        ylim: int = self.app.size.height // 2
        xoffset: int = self.app.state.offset[0]
        yoffset: int = self.app.state.offset[1]
        state: State = self.app.state
        togglenums: bool = self.app.togglenums

        renderable = Text()
        renderiter = state.render(
            xlim - xoffset, 
            ylim - yoffset,  # limits of the screen space avaliable
            -xlim - xoffset, 
            -ylim - yoffset
        )

        for item in renderiter:
            # idx     : if togglenums is on, show the numbers
            # bgcolor : get the color of the cell
            # color   : if the cell is empty, make the text the same color as the cell
            idx = item if togglenums or item == State.EOL else -1               
            bgcolor = self.CELL_LOOKUP[item][1]                                 
            color = "white" if item != State.EMPTY and togglenums else bgcolor  

            renderable.append(
                text=self.CELL_LOOKUP[idx][0],  # get the text
                style=Style(color=color, bgcolor=bgcolor)
            )
            
        self.update(renderable)  # hey!


# its spaghetti from here on out
class txSweeper(App):
    """An infinitely generative minesweeper game."""

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit"),
        Binding(key="n", action="toggle_nums", description="Toggle numbers"),
        Binding(key="up", action="move(0, 1)", description="Up"),
        Binding(key="left", action="move(1, 0)", description="Left"),
        Binding(key="down", action="move(0, -1)", description="Down"),
        Binding(key="right", action="move(-1, 0)", description="Right"),
        Binding(key="s", action="save", description="Save"),
        Binding(key="l", action="load", description="Load"),
    ]

    CSS = """
    Screen {
        background: #000000;
    }
    Header {
        background: #202020;
    }
    Footer {
        background: #202020;
    }
    Footer > .footer--highlight {
        background: #303030;
    }
    Footer > .footer--key {
        background: #363636;
    }
    Footer > .footer--highlight-key {
        background: #404040;
    }
    """ # css small enough to not need a file

    state: State
    togglenums = True
    gameovered = False


    def compose(self):
        yield Header()
        v = View(id="view")
        yield v
        yield Footer()

        # setting the callback for the intercept to update score
        self.state = State(v.calcscore)  

    # the rest of this should be self explanatory 

    def on_mount(self):
        self.screen.styles.overflow_y = "hidden"
        self.title = "txSweeper - (0, 0) - Score: 0"
    
    def action_toggle_nums(self):
        self.togglenums = not self.togglenums
        self.query_one("#view").redraw()
    
    def action_move(self, x: int, y: int):
        self.state.offset[0] += x
        self.state.offset[1] += y
        self.query_one("#view").redraw()
        self.update_title()
    
    def update_title(self):
        """Update the title of the window."""
        if self.gameovered:
            return
        self.title = f"txSweeper - ({self.state.offset[0]-self.state.invsoffset}, {self.state.offset[1]}) - Score: {self.state.score}"
    
    def action_save(self):
        if self.gameovered:
            return
        with open("txsweepersave", "w") as f:
            dct = vars(self.state)
            del dct["_intercept_callback"]
            f.write(json.dumps(dct))
            self.title = "txSweeper - Saved!"
            self.bell()
    
    def action_load(self):
        try:
            with open("txsweepersave", "r") as f:
                self.state = State(self.query_one("#view").calcscore)
                for key, val in json.loads(f.read()).items():
                    setattr(self.state, key, val)
                self.query_one("#view").redraw()
                self.title = "txSweeper - Loaded!"
                self.bell()
                self.gameovered = False
        except:
            self.title = "txSweeper - No save found!"
            self.bell()

    def game_over(self):
        """Ends the game."""
        self.title = "txSweeper - Game Over!"
        self.gameovered = True
        
def main():
    """Entry point for the application script"""
    txSweeper().run()

# hello world!
if __name__ == "__main__":
    main()