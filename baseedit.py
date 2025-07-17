import tkinter as tk
from tkinter import ttk
import os

try:
    import PIL.ImageGrab
    import PIL.Image
    import PIL.ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from baseinfo import BASE_LAYOUTS, BASE_NAMES, BASE_NAMES_REV
from decors import SIZES, DECORATIONS, NAMES, NAMES_REV


def get_decoration_offset(decor_id):
    # returns x, y offset
    w, h = SIZES[decor_id]

    if h == w == 1:
        return -7, -7
    elif h == 2 and w == 1:
        return -7, -8
    elif h == 1 and w == 2:
        return -7, -7
    elif h == w == 2:
        return -7, -8
    elif h == 2 and w == 3:
        return -7, -8
    elif h == 3 and w == 2:
        return -7, -9
    elif h == w == 3:
        return -7, -9
    elif h == 4 and w == 2:
        return -7, -10
    elif h == 2 and w == 4:
        return -7, -8
    return -7, -7


def sort_decorations(decors, positions, reverse=False):
    sorted_decors = []
    sorted_positions = []

    # mats get drawn first
    for i in range(len(decors)):
        if decors[i].endswith("MAT"):
            sorted_decors.append(decors[i])
            sorted_positions.append(positions[i])

    # then desks
    for i in range(len(decors)):
        if decors[i].endswith("DESK") or decors[i] == "DECOR_TIRE":
            sorted_decors.append(decors[i])
            sorted_positions.append(positions[i])

    # then bricks
    for i in range(len(decors)):
        if decors[i].endswith("BRICK"):
            sorted_decors.append(decors[i])
            sorted_positions.append(positions[i])

    # then everything else, but lower y values get drawn first!!!!
    sorted_decs = sorted(zip(decors, positions), key=lambda x: x[1][1], reverse=reverse)
    for decor, pos in sorted_decs:
        if (
            not decor.endswith("MAT")
            and not decor.endswith("DESK")
            and not decor.endswith("BRICK")
            and decor != "DECOR_TIRE"
        ):
            sorted_decors.append(decor)
            sorted_positions.append(pos)

    if reverse:
        sorted_decors = sorted_decors[::-1]
        sorted_positions = sorted_positions[::-1]

    return sorted_decors, sorted_positions



class EditCanvas(tk.Frame):
    def __init__(self, master, scale=1):
        super().__init__(master)
        self.master = master
        self.base = None
        self.scale = scale
        self.mode = "normal"
        self.selected_decor_idx = None
        self.drag_offset = (0, 0)  # Offset between click and top-left corner of decoration

        self.add_controls()

        self.canvas = tk.Canvas(self, width=272 * self.scale, height=272 * self.scale)
        self.canvas.grid(row=1, column=0, sticky='nsew')

        self.canvas.bind("<Button-1>", self.detect_click)
        self.canvas.bind("<Button-3>", self.detect_right_click)
        self.canvas.bind("<B1-Motion>", self.handle_drag)

    def add_controls(self):
        self.controls = tk.Frame(self)

        self.decorLbl = tk.Label(self.controls, text="Decoration:")
        self.decorLbl.grid(row=0, column=0, sticky='e')
        self.decorVar = tk.StringVar()
        self.decorEntry = ttk.Combobox(self.controls, textvariable=self.decorVar)
        self.decorEntry['values'] = [x for x in NAMES_REV]
        self.decorEntry.grid(row=0, column=1, sticky='ew')

        self.decorEntry.bind("<<ComboboxSelected>>", lambda e: self.set_decor(NAMES_REV[self.decorVar.get()]))

        self.idxLbl = tk.Label(self.controls, text="Index:")
        self.idxLbl.grid(row=0, column=2, sticky='e')
        self.idxVar = tk.StringVar()
        self.idxEntry = ttk.Spinbox(self.controls, textvariable=self.idxVar, from_=0, to=15)
        self.idxEntry.grid(row=0, column=3, sticky='ew')

        self.idxVar.trace("w", lambda *args: self.select(int(self.idxVar.get())))

        self.xLbl = tk.Label(self.controls, text="X:")
        self.xLbl.grid(row=1, column=0, sticky='e')
        self.xVar = tk.StringVar()
        self.xEntry = ttk.Entry(self.controls, textvariable=self.xVar)
        self.xEntry.grid(row=1, column=1, sticky='ew')

        self.xEntry.bind("<Return>", lambda e: self.set_x(int(self.xVar.get())))

        self.yLbl = tk.Label(self.controls, text="Y:")
        self.yLbl.grid(row=1, column=2, sticky='e')
        self.yVar = tk.StringVar()
        self.yEntry = ttk.Entry(self.controls, textvariable=self.yVar)
        self.yEntry.grid(row=1, column=3, sticky='ew')

        self.yEntry.bind("<Return>", lambda e: self.set_y(int(self.yVar.get())))

        self.controls.grid(row=0, column=0)

    def set_decor(self, decor):
        if self.base is None or self.selected_decor_idx is None:
            return
        if self.selected_decor_idx < 0 or self.selected_decor_idx >= len(self.base['decorations']):
            return
        self.base['decorations'][self.selected_decor_idx] = decor
        self.draw()

    def set_x(self, x):
        if self.base is None:
            return
        self.base['decoration_positions'][self.selected_decor_idx] = (x, self.base['decoration_positions'][self.selected_decor_idx][1])
        self.xVar.set(x)
        self.draw()

    def set_y(self, y):
        if self.base is None:
            return
        self.base['decoration_positions'][self.selected_decor_idx] = (self.base['decoration_positions'][self.selected_decor_idx][0], y)
        self.yVar.set(y)
        self.draw()

    def sort(self):
        if self.base is None:
            return

        self.base['decorations'], self.base['decoration_positions'] = sort_decorations(
            self.base['decorations'],
            self.base['decoration_positions']
        )

    def select(self, idx):
        if self.base is None:
            return
        if idx is None or idx < 0 or idx >= len(self.base['decorations']):
            self.selected_decor_idx = None
            return

        self.selected_decor_idx = idx
        self.decorVar.set(NAMES[self.base['decorations'][idx]])
        self.idxVar.set(idx)
        self.xVar.set(self.base['decoration_positions'][idx][0])
        self.yVar.set(self.base['decoration_positions'][idx][1])

        self.draw()

    def load_and_draw(self, base):
        self.base = base
        self.sort()
        self.select(0)
        self.draw()

    def draw(self):
        self.imgs = []
        self.canvas.delete("all")
        self.draw_background()
        self.draw_decorations()
        self.draw_controls()

    def detect_click(self, event):
        if self.base is None:
            return
        x, y = event.x, event.y
        tile_size = 16 * self.scale
        for i in range(len(self.base['decorations'])-1, -1, -1):
            decor = self.base['decorations'][i]
            if decor == "DECOR_NONE":
                continue
            x_offset, y_offset = get_decoration_offset(decor)
            i_x_pos, i_y_pos = self.base['decoration_positions'][i]
            x_pos = (i_x_pos + x_offset)
            y_pos = (i_y_pos + y_offset)

            width, height = SIZES[decor]
            if SIZES[decor] == (2, 2) and decor.endswith("DOLL"):
                extra_x = -16
            else:
                extra_x = 0
            deco_x0 = (x_pos) * tile_size + extra_x
            deco_y0 = (y_pos) * tile_size
            deco_x1 = deco_x0 + (16 * width) * self.scale
            deco_y1 = deco_y0 + (16 * height) * self.scale
            if deco_x0 <= x < deco_x1 and deco_y0 <= y < deco_y1:
                self.selected_decor_idx = i
                # Store the grid cell where drag started
                self._drag_start_grid = (x // tile_size, y // tile_size)
                self._drag_start_decor_pos = (i_x_pos, i_y_pos)
                print(f"Selected {decor} at {i_x_pos}, {i_y_pos}, drag started at grid {self._drag_start_grid}")
                self.select(i)
                self.draw()
                return

    def detect_right_click(self, event):
        if self.base is None:
            return
        x, y = event.x, event.y
        t_x, t_y = x // (16 * self.scale), y // (16 * self.scale)
        idx = None
        for i in range(len(self.base['decorations'])-1, -1, -1):
            decor = self.base['decorations'][i]
            if decor == "DECOR_NONE":
                continue
            x_offset, y_offset = get_decoration_offset(decor)
            i_x_pos, i_y_pos = self.base['decoration_positions'][i]
            x_pos = (i_x_pos + x_offset)
            y_pos = (i_y_pos + y_offset)
            if x_pos == t_x and y_pos == t_y:
                idx = i

        if idx is not None:
            print(f"Right clicked {decor} at {i_x_pos}, {i_y_pos}")
            self.select(idx)
            self.set_decor("DECOR_NONE")
            self.draw()
            return

    def handle_drag(self, event):
        if self.base is None or self.selected_decor_idx is None:
            return
        if self.selected_decor_idx < 0 or self.selected_decor_idx >= len(self.base['decorations']):
            return

        x, y = event.x, event.y
        tile_size = 16 * self.scale
        # Get the grid cell under the mouse pointer
        grid_x = x // tile_size
        grid_y = y // tile_size

        # Get the grid cell where drag started and the original decor position
        start_grid = getattr(self, '_drag_start_grid', None)
        start_decor_pos = getattr(self, '_drag_start_decor_pos', None)
        if start_grid is None or start_decor_pos is None:
            return

        # Only move if the grid cell under the mouse is different from the drag start cell
        dx = grid_x - start_grid[0]
        dy = grid_y - start_grid[1]
        new_x = start_decor_pos[0] + dx
        new_y = start_decor_pos[1] + dy

        old_pos = self.base['decoration_positions'][self.selected_decor_idx]
        new_pos = (int(new_x), int(new_y))
        if old_pos == new_pos:
            return
        self.base['decoration_positions'][self.selected_decor_idx] = new_pos
        self.select(self.selected_decor_idx)
        self.draw()

    def draw_background(self):
        if self.base is None:
            return
        layout = BASE_LAYOUTS[BASE_NAMES_REV[self.base['secret_base_id']]]
        if layout == "None":
            return
        fn = os.path.join(os.getcwd(), 'interior', f'{layout}.png')
        self.bg = tk.PhotoImage(file=fn)
        if self.scale != 1:
            self.bg = self.bg.zoom(self.scale)
        self.imgs.append(self.bg)
        self.canvas.create_image(0, 0, image=self.bg, anchor='nw')

    def draw_decorations(self):
        if self.base is None:
            return
        decors, positions = sort_decorations(
            self.base['decorations'],
            self.base['decoration_positions']
        )
        for i in range(len(decors)):
            decor = decors[i]
            if decor == "DECOR_NONE":
                continue
            if "NOTE_MAT" in decor:
                fn = os.path.join(os.getcwd(), 'decorations', 'NOTE_MAT.png')
            else:
                fn = os.path.join(os.getcwd(), 'decorations', f'{decor.replace("DECOR_", "")}.png')
            img = tk.PhotoImage(file=fn)
            if self.scale != 1:
                img = img.zoom(self.scale)
            self.imgs.append(img)
            x_offset, y_offset = get_decoration_offset(decor)

            if SIZES[decor] == (2, 2) and decor.endswith("DOLL"):
                extra_x = -16
            else:
                extra_x = 0

            x = (positions[i][0] + x_offset) * 16 * self.scale + extra_x
            y = (positions[i][1] + y_offset) * 16 * self.scale

            self.canvas.create_image(x, y, image=img, anchor='nw')

    def draw_controls(self):
        if self.base is None:
            return
        # draw selected square
        if self.selected_decor_idx is not None:
            decor = self.base['decorations'][self.selected_decor_idx]
            x_offset, y_offset = get_decoration_offset(decor)
            width, height = SIZES[decor]
            x_pos, y_pos = self.base['decoration_positions'][self.selected_decor_idx]

            if SIZES[decor] == (2, 2) and decor.endswith("DOLL"):
                extra_x = -16
            else:
                extra_x = 0

            x_pos = (x_pos + x_offset) * 16 * self.scale + extra_x
            y_pos = (y_pos + y_offset) * 16 * self.scale
            self.canvas.create_rectangle(
                x_pos, y_pos,
                x_pos + (16 * width) * self.scale, y_pos + (16 * height) * self.scale,
                outline="red",
                width=2
            )


def draw_base(base, output_filename):
    if not PIL_AVAILABLE:
        return

    # create a new PIL image with the size of the template
    layout = BASE_LAYOUTS[BASE_NAMES_REV[base['secret_base_id']]]
    if layout == "None":
        return
    
    fn = os.path.join(os.getcwd(), 'interior', f'{layout}.png')
    bg = PIL.Image.open(fn)

    decors, positions = sort_decorations(
        base['decorations'],
        base['decoration_positions']
    )

    for i in range(len(decors)):
        decor = decors[i]
        if decor == "DECOR_NONE":
            continue
        if "NOTE_MAT" in decor:
            fn = os.path.join(os.getcwd(), 'decorations', 'NOTE_MAT.png')
        else:
            fn = os.path.join(os.getcwd(), 'decorations', f'{decor.replace("DECOR_", "")}.png')
        img = PIL.Image.open(fn).convert("RGBA")
        x_offset, y_offset = get_decoration_offset(decor)
        x = (positions[i][0] + x_offset) * 16
        y = (positions[i][1] + y_offset) * 16
        bg.paste(img, (x, y), img)

    bg.save(output_filename)

    print(f"Saved image to {output_filename}")


if __name__ == '__main__':
    root = tk.Tk()

    # Minimal sample base object for testing
    sample_base = {
        'secret_base_id': list(BASE_NAMES_REV.keys())[0],
        'decorations': ["DECOR_TV", "DECOR_SMALL_CHAIR", "DECOR_SMALL_DESK"],
        'decoration_positions': [(5, 5), (10, 10), (15, 15)]
    }

    canvas = EditCanvas(root)
    canvas.grid(row=0, column=0, sticky='nsew')
    canvas.load_and_draw(sample_base)
    root.mainloop()
