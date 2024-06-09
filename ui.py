import json
import os
import os.path
import signal
import tkinter as tk
import tkinter.ttk as ttk
from copy import deepcopy
from pprint import pprint
from tkinter import filedialog, messagebox

import viewbase
from baseedit import EditCanvas, draw_base
from baseinfo import BASE_NAMES, BASE_NAMES_REV
from canvasbutton import CanvasButton
from items import ITEMS
from pokemon import MOVES, POKEMON
from viewbase import layout_hash, team_hash

try:
    import PIL.ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


MAX_RECENT_FILES = 5


TRAINER_CLASSES = [
    "Youngster",
    "Bug Catcher",
    "Rich Boy",
    "Camper",
    "Cooltrainer (M)",
    "Lass",
    "School Kid (F)",
    "Lady",
    "Picnicker",
    "Cooltrainer (F)",
]


class TrainerEdit(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.old_index = None
        self.active_idx = None
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)

    def add_widgets(self):
        trainerLbl = tk.Label(self, text="Trainer Name")
        trainerLbl.grid(row=0, column=0, sticky='e')
        self.trainerVar = tk.StringVar()
        self.trainerEntry = ttk.Entry(self, textvariable=self.trainerVar)
        self.trainerEntry.grid(row=0, column=1, sticky='ew')

        idLbl = tk.Label(self, text="ID")
        idLbl.grid(row=1, column=0, sticky='e')
        self.idVar = tk.StringVar()
        self.idEntry = ttk.Entry(self, textvariable=self.idVar)
        self.idEntry.grid(row=1, column=1, sticky='ew')
        self.idVar.trace_add('write', lambda *args: self.update_class())

        sidLbl = tk.Label(self, text="SID")
        sidLbl.grid(row=2, column=0, sticky='e')
        self.sidVar = tk.StringVar()
        self.sidEntry = ttk.Entry(self, textvariable=self.sidVar)
        self.sidEntry.grid(row=2, column=1, sticky='ew')

        genderLbl = tk.Label(self, text="Gender")
        genderLbl.grid(row=3, column=0, sticky='e')
        self.genderVar = tk.StringVar()
        self.genderDropdown = ttk.Combobox(self, textvariable=self.genderVar)
        self.genderDropdown['values'] = ['Male', 'Female']
        # self.genderDropdown.current(0)
        self.genderDropdown.grid(row=3, column=1, sticky='ew')
        self.genderVar.trace_add('write', lambda *args: self.update_class())

        classLbl = tk.Label(self, text="Trainer Class")
        classLbl.grid(row=4, column=0, sticky='e')
        self.classVar = tk.StringVar()
        self.classEntry = ttk.Entry(self, state='readonly', textvariable=self.classVar)
        self.classEntry.grid(row=4, column=1, sticky='ew')

        partyLbl = tk.Label(self, text="Party")
        partyLbl.grid(row=5, column=0, sticky='nse')
        self.partyButtons = PartyButtons(self)
        self.partyButtons.add_widgets()
        self.partyButtons.grid(row=5, column=1, sticky='ew')

        speciesLbl = tk.Label(self, text="Species")
        speciesLbl.grid(row=6, column=0, sticky='e')
        self.speciesVar = tk.StringVar()
        self.speciesDropdown = ttk.Combobox(self, textvariable=self.speciesVar)
        self.speciesDropdown['values'] = [x for x in POKEMON if not x.startswith('Unown ')]
        self.speciesDropdown.current(0)
        self.speciesDropdown.grid(row=6, column=1, sticky='ew')
        self.speciesVar.trace_add('write', lambda *args: self.update_party_button_image(self.old_index))

        pidLbl = tk.Label(self, text="PID")
        pidLbl.grid(row=7, column=0, sticky='e')
        self.pidVar = tk.StringVar()
        self.pidVar.set("0")
        self.pidEntry = ttk.Entry(self, textvariable=self.pidVar)
        self.pidEntry.grid(row=7, column=1, sticky='ew')

        movesLbl = tk.Label(self, text="Moves")
        movesLbl.grid(row=8, column=0, sticky='e')

        self.moveVars = [tk.StringVar() for i in range(4)]
        self.moveDropdowns = []
        for i in range(4):
            moveDropdown = ttk.Combobox(self, textvariable=self.moveVars[i])
            moveDropdown.grid(row=8+i, column=1, sticky='ew')
            moveDropdown['values'] = MOVES
            moveDropdown.current(i)

            self.moveDropdowns.append(moveDropdown)

        evsLbl = tk.Label(self, text="EVs")
        evsLbl.grid(row=12, column=0, sticky='e')
        self.evsVar = tk.StringVar()
        self.evsVar.set("85")
        self.evsEntry = ttk.Entry(self, textvariable=self.evsVar)
        self.evsEntry.grid(row=12, column=1, sticky='ew')

        levelLbl = tk.Label(self, text="Level")
        levelLbl.grid(row=13, column=0, sticky='e')
        self.levelVar = tk.StringVar()
        self.levelVar.set("100")
        self.levelEntry = ttk.Entry(self, textvariable=self.levelVar)
        self.levelEntry.grid(row=13, column=1, sticky='ew')

        itemLbl = tk.Label(self, text="Item")
        itemLbl.grid(row=14, column=0, sticky='e')
        self.itemVar = tk.StringVar()
        self.itemDropdown = ttk.Combobox(self, textvariable=self.itemVar)
        self.itemDropdown['values'] = [x for x in ITEMS if x != '????????']
        self.itemDropdown.grid(row=14, column=1, sticky='ew')

        baseLbl = tk.Label(self, text="Base")
        baseLbl.grid(row=15, column=0, sticky='e')
        self.baseVar = tk.StringVar()
        self.baseDropdown = ttk.Combobox(self, textvariable=self.baseVar)
        self.baseDropdown['values'] = list(BASE_NAMES.values())
        self.baseDropdown.grid(row=15, column=1, sticky='ew')

        self.baseVar.trace_add('write', lambda *args: self.on_baseVar_change())

        self.routeScreenshot = tk.Canvas(self, width=240, height=160)
        self.routeScreenshot.grid(row=16, column=0, columnspan=2, sticky='ne')

        self.editCanvas = EditCanvas(self, scale=2)
        self.editCanvas.grid(row=0, column=2, rowspan=16, sticky='nsew')

    def update_class(self):
        classIndex = (int(self.idVar.get()) & 0xFF) % 5
        classIndex += (0 if self.genderVar.get() == "Male" else 1) * 5

        self.classVar.set(TRAINER_CLASSES[classIndex])

    def load_bases(self, bases):
        self.bases = bases

    def on_baseVar_change(self):
        self.editCanvas.load_and_draw(self.get_base_from_inputs())
        self.set_base_screenshot(BASE_NAMES_REV[self.baseVar.get()])

    def set_base_screenshot(self, base_id):
        # get the base screenshot
        fn = os.path.join(os.path.dirname(__file__), f"base_screenshots/{base_id}.png")
        if os.path.exists(fn):
            self.routeScreenshot.img = tk.PhotoImage(file=fn)
            self.routeScreenshot.create_image(0, 0, image=self.routeScreenshot.img, anchor='nw')

    def load_base(self, base_idx):
        if self.active_idx is not None:
            # save the current base
            self.bases[self.active_idx]['trainer_name'] = self.trainerVar.get()
            self.bases[self.active_idx]['id'] = int(self.idVar.get())
            self.bases[self.active_idx]['sid'] = int(self.sidVar.get())
            self.bases[self.active_idx]['gender'] = 0 if self.genderVar.get() == "Male" else 1
            self.bases[self.active_idx]['party'] = self.party
            self.bases[self.active_idx]['secret_base_id'] = self.baseVar.get()
            self.bases[self.active_idx]['decorations'] = self.editCanvas.base['decorations']
            self.bases[self.active_idx]['decoration_positions'] = self.editCanvas.base['decoration_positions']

        self.active_idx = base_idx
        self.editCanvas.base = baseDict = self.bases[base_idx]

        self.trainerVar.set(baseDict['trainer_name'])
        self.idVar.set(baseDict['id'])
        self.sidVar.set(baseDict['sid'])

        # class is lowest byte of ID mod 5, +5 if female
        classIndex = baseDict['id'] & 0xFF % 5
        classIndex += baseDict['gender'] * 5
        self.classVar.set(TRAINER_CLASSES[classIndex])

        self.genderVar.set('Male' if baseDict['gender'] == 0 else 'Female')

        self.party = baseDict['party']
        self.old_index = None
        self.set_party_display(0)

        self.baseVar.set(baseDict['secret_base_id'])
        self.set_base_screenshot(BASE_NAMES_REV[baseDict['secret_base_id']])

        self.set_party_buttons()

        self.editCanvas.load_and_draw(baseDict)

        self.master.update_list()

    def set_party_buttons(self):
        for i in range(6):
            self.partyButtons.btns[i].set_image(f"sprites/{self.party[i]['species'].lower()}.png")
        # select first one
        self.partyButtons.set_active(0)

    def update_party_button_image(self, index):
        # index = self.old_index
        if index is None:
            return
        if self.state == 'switching':
            return
        species = self.speciesVar.get()

        if os.path.exists(f"sprites/{species.lower()}.png"):
            self.partyButtons.btns[index].set_image(f"sprites/{species.lower()}.png")
        else:
            self.partyButtons.btns[index].set_image("sprites/none.png")
        self.partyButtons.btns[index].draw()

    def set_party_display(self, index):
        # first save all the old ones to the party
        if self.old_index is not None:
            self.party[self.old_index]['species'] = self.speciesVar.get()
            self.party[self.old_index]['personality'] = int(self.pidVar.get())
            self.party[self.old_index]['level'] = int(self.levelVar.get())
            self.party[self.old_index]['held_item'] = self.itemVar.get()
            self.party[self.old_index]['evs'] = int(self.evsVar.get())

            self.party[self.old_index]['moves'] = [m.get() for m in self.moveVars]

        self.state = 'switching'

        self.speciesVar.set(self.party[index]['species'])
        self.pidVar.set(self.party[index]['personality'])
        self.levelVar.set(self.party[index]['level'])
        self.itemVar.set(self.party[index]['held_item'])
        self.evsVar.set(self.party[index]['evs'])

        self.state = 'normal'

        for i in range(6):
            if i != index:
                self.partyButtons.btns[i].state = 'normal'
                self.partyButtons.btns[i].draw()

        for i in range(4):
            self.moveVars[i].set(self.party[index]['moves'][i])

        self.old_index = index

        self.update_party_button_image(index)
        self.partyButtons.btns[index].state = 'disabled'


    def get_base_from_inputs(self):
        newBase = deepcopy(self.editCanvas.base)

        if newBase is None:
            return {}

        newBase['trainer_name'] = self.trainerVar.get()
        newBase['id'] = int(self.idVar.get())
        newBase['sid'] = int(self.sidVar.get())

        newBase['language'] = 2
        newBase['to_register'] = 2

        newBase['secret_base_id'] = self.baseVar.get()

        newBase['gender'] = 0 if self.genderVar.get() == "Male" else 1

        return newBase

    def save(self, fn):
        self.set_party_display(self.partyButtons.active)

        self.load_base(self.active_idx)

        newhsave = self.parent.save

        for i in range(20):
            newhsave = viewbase.insert_base_to_save(newhsave, self.bases[i], i)

        fullsave = viewbase.insert_halfsave_to_save(self.parent.fullsave, newhsave)

        try:
            with open(fn, 'wb+') as f:
                f.write(bytes(fullsave))
            print(f"Saved to {fn}")
        except OSError:
            # this could be a permission error, or a file in use error
            # use a dialog to show the error
            messagebox.showerror("Error", "Could not save file. Is it open in another program?")

    def save_base(self, idx, folder_path):
        self.set_party_display(self.partyButtons.active)

        self.load_base(idx)

        lh = layout_hash(self.bases[idx])
        th = team_hash(self.bases[idx])
        fn = f"{folder_path}/{self.bases[idx]['trainer_name']} ({self.bases[idx]['id']}) - {lh} - {th}.json"

        with open(fn, 'w+') as f:
            f.write(json.dumps(self.bases[idx], indent=4))

        print(f"Saved to {fn}")

    def save_all_bases(self, folder_path):
        # get folder, save all to that folder under fn "ID - Trainer Name - hash.json"
        for i in range(20):
            lh = layout_hash(self.bases[i])
            th = team_hash(self.bases[i])
            fn = f"{folder_path}/{self.bases[i]['trainer_name']} ({self.bases[i]['id']}) - {lh} - {th}.json"
            self.save_base(i, fn)

    def import_base(self, fn):
        with open(fn, 'r') as f:
            imported_base = json.load(f)

        idx = self.active_idx
        self.bases[self.active_idx] = imported_base
        self.active_idx = None
        self.load_base(idx)

    def save_base_as_image(self, idx, file_name):
        base = self.bases[idx]
        draw_base(base, file_name)

    def save_all_bases_as_images(self, folder_path):
        for i in range(20):
            if self.bases[i]['trainer_name']:
                lh = layout_hash(self.bases[i])
                th = team_hash(self.bases[i])
                fn = f"{folder_path}/{self.bases[i]['trainer_name']} ({self.bases[i]['id']}) - {lh} - {th}.png"
                self.save_base_as_image(i, fn)

        


class BaseEdit(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

    def add_widgets(self):
        canvas = tk.Canvas(self)
        canvas.grid(row=0, column=0, sticky='nsew', columnspan=2)

        decorationLbl = tk.Label(self, text="Decoration")
        decorationLbl.grid(row=1, column=0, sticky='w')
        self.decorationDropdown = ttk.Combobox(self)
        self.decorationDropdown.grid(row=1, column=1, sticky='w')

        indexLbl = tk.Label(self, text="Index")
        indexLbl.grid(row=2, column=0, sticky='w')
        self.indexEntry = ttk.Entry(self, state='readonly')
        self.indexEntry.grid(row=2, column=1, sticky='w')

        xLbl = tk.Label(self, text="X")
        xLbl.grid(row=3, column=0, sticky='w')
        self.xEntry = ttk.Entry(self)
        self.xEntry.grid(row=3, column=1, sticky='w')

        yLbl = tk.Label(self, text="Y")
        yLbl.grid(row=4, column=0, sticky='w')
        self.yEntry = ttk.Entry(self)
        self.yEntry.grid(row=4, column=1, sticky='w')


class PartyButtons(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.active = 0

    def add_widgets(self):
        self.btns = []
        # add 6 square buttons, with A-F on them
        for i in range(6):
            btn = CanvasButton(self, 32, 32, "image", "sprites/egg.png")
            btn.command = lambda i=i: self.set_active(i)
            btn.grid(row=0, column=i, sticky='nsew')
            self.grid_columnconfigure(i, weight=1)

            self.btns.append(btn)

    def set_active(self, i):
        self.active = i
        # make only the active one clicked
        for i in range(6):
            self.btns[i].state = 'normal'
        self.btns[self.active].state = 'disabled'

        for i in range(6):
            self.btns[i].draw()

        self.parent.set_party_display(self.active)


class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Secret Base Editor")

        self.load_settings()
        self.create_menu()

        self.treeview = ttk.Treeview(self, show="tree", selectmode='browse')
        self.treeview.grid(row=0, column=0, sticky='nsew')
        self.treeview.bind("<ButtonRelease-1>", self.on_treeview_click)

        for i in range(20):
            self.treeview.insert('', 'end', text=f'Base {i+1}')

        self.edit = TrainerEdit(self)
        self.edit.add_widgets()
        self.edit.grid(row=0, column=1, sticky='nsew')

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def create_menu(self):
        self.menu = tk.Menu(self)
        self.config(menu=self.menu)
        self.file_menu = tk.Menu(self.menu, tearoff=0)
        self.file_menu.add_command(label="Open...", command=self.open_file_dialog, underline=0)
        self.file_menu.add_command(label="Save File...", command=self.save_file_dialog, underline=0)
        self.file_menu.add_command(label="Export Base...", command=self.save_base_dialog, underline=0)
        self.file_menu.add_command(label="Export All Bases...", command=self.save_all_bases_dialog, underline=7)
        self.file_menu.add_command(label="Import Base...", command=self.import_base_dialog, underline=0)

        if PIL_AVAILABLE:
            self.file_menu.add_command(label="Export Base As Image...", command=self.export_base_as_image, underline=1)
            self.file_menu.add_command(label="Export All Bases As Images...", command=self.export_all_bases_as_images, underline=7)
        else:
            self.file_menu.add_command(label="Export Base As Image... (requires PIL)", state='disabled', underline=1)
            self.file_menu.add_command(label="Export All Bases As Images... (requires PIL)", state='disabled', underline=7)

        self.file_menu.add_separator()

        # recent files
        self.file_menu.add_cascade(label="Recent Files", menu=tk.Menu(self.file_menu, tearoff=0))
        recent_files_menu = self.file_menu.winfo_children()[-1]
        for i, fn in enumerate(self.settings['recent_files']):
            recent_files_menu.add_command(label=fn, command=lambda fn=fn: self.open_file(fn), underline=0)

        self.menu.add_cascade(label="File", menu=self.file_menu)

    def update_menu(self):
        # first, get rid of the entire menu
        self.menu.delete(0)

        self.create_menu()

    def update_list(self):
        bases = self.edit.bases

        # clear treeview first
        for i in self.treeview.get_children():
            self.treeview.delete(i)

        for i, base in enumerate(bases):
            if not base['trainer_name']:
                self.treeview.insert('', 'end', text=f"{i+1}: Base {i+1}")
            else:
                self.treeview.insert('', 'end', text=f"{i+1}: {base['trainer_name']} ({base['id']})")

        # add a selection
        if self.edit.active_idx is not None:
            self.treeview.selection_set(self.treeview.get_children()[self.edit.active_idx])

    def on_treeview_click(self, event):
        item = self.treeview.selection()[0]
        self.edit.load_base(self.treeview.index(item))

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(title="Open File", filetypes=[("SAV", "*.sav")])
        self.open_file(file_path)

    def open_file(self, file_path):
        fullsave = viewbase.load_full_save(file_path)
        save = viewbase.load_save(file_path)
        self.save = save
        self.fullsave = fullsave
        bases = viewbase.get_all_bases_from_save(save)

        self.edit.active_idx = None
        self.edit.load_bases(bases)
        self.edit.load_base(0)

        # add to recent files
        if file_path in self.settings['recent_files']:
            self.settings['recent_files'].remove(file_path)
        self.settings['recent_files'].insert(0, file_path)

        if len(self.settings['recent_files']) > MAX_RECENT_FILES:
            self.settings['recent_files'].pop()

        self.save_settings()

        self.update_menu()

    def save_file_dialog(self):
        file_path = filedialog.asksaveasfilename(title="Save File", filetypes=[("SAV", "*.sav")])
        self.edit.save(file_path)

    def save_base_dialog(self):
        folder_path = filedialog.askdirectory()
        self.edit.save_base(self.edit.active_idx, folder_path)

    def save_all_bases_dialog(self):
        folder_path = filedialog.askdirectory()
        self.edit.save_all_bases(folder_path)

    def import_base_dialog(self):
        file_path = filedialog.askopenfilename(title="Import Base", filetypes=[("JSON", "*.json")])
        self.edit.import_base(file_path)

    def export_base_as_image(self):
        file_path = filedialog.asksaveasfilename(title="Export Base As Image", filetypes=[("PNG", "*.png")])
        self.edit.save_base_as_image(self.edit.active_idx, file_path)

    def export_all_bases_as_images(self):
        folder_path = filedialog.askdirectory()
        self.edit.save_all_bases_as_images(folder_path)

    def save_settings(self):
        with open('settings.json', 'w+') as f:
            f.write(json.dumps(self.settings, indent=4))

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                'recent_files': []
            }
            self.save_settings()


def add_ctrl_c_handler(app):
    def handler(event):
        app.destroy()
        print('caught ^C')

    def check():
        app.after(500, check)  #  time in ms.

    signal.signal(signal.SIGINT, lambda x,y : print('terminal ^C') or handler(None))
    app.after(500, check)



if __name__ == "__main__":
    app = App()
    ico = tk.PhotoImage(file='decorations/MUDKIP_DOLL.png')
    app.wm_iconphoto(False, ico)
    add_ctrl_c_handler(app)

    app.mainloop()