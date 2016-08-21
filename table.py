#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import math
import threading
from PIL import Image, ImageTk
import sys
root = tk.Tk()
root.style = ttk.Style()
if "clam" in root.style.theme_names():
    root.style.theme_use("clam")


MOB_MODE = 1
PLAY_MODE = 2

TOKEN_COLOR_FORMAT = "#%02X%02X%02X"
TOKEN_ENEMY_SCHEME = (255,0,0)
TOKEN_PLAYER_SCHEME = (0, 85, 255)
TOKEN_RANDOMNESS = 120

def random_token_color(color_scheme=TOKEN_PLAYER_SCHEME, max_diff=TOKEN_RANDOMNESS):
    import random
    def diff(x):
        x = x - random.randint(-max_diff/2, max_diff/2)
        if x < 0:
            return 0
        elif x > 255:
            return 255
        else:
            return x
    return TOKEN_COLOR_FORMAT % tuple([diff(x) for x in color_scheme])

TOKEN_SIZE = 80

BACKGROUND_COLOR = "#000"
BUTTON_BG = "#333"
BUTTON_FG = "#FFF"
DEFAULT_VIEW_DIST = 400 #px

ENABLE_SHADOWS = False
SHADOW_FACTOR = 8
SHADOW_STEP_TIMES = 1 # *360 Degree
DARKNESS_OPACITY = 0x4F

INIT_DIR = "/home/mtib/Pictures/DND"

class Playfield(object):
    def __init__(self, master, **kwargs):
        self.view_dist = DEFAULT_VIEW_DIST
        self.master=master
        self.mode = PLAY_MODE
        self.selected = -1
        self.clicked = -1
        self.tokens = []
        self.last_color = "#F0F"
        self.bigger = 0
        self.shadows = ENABLE_SHADOWS
        pad=3

        master.attributes("-fullscreen", True)
        master.title("Virtual Table")
        master.config(bg=BACKGROUND_COLOR, bd=0)
        master.bind('<Escape>',self.kill)

        self.canv = tk.Canvas(self.master, bg=BACKGROUND_COLOR, bd=0)

        self.canv.bind("<Double-Button-1>", self.create_token)
        self.canv.bind("<Button-3>", self.defeat_token)
        self.canv.bind("<Button-1>", self.select_token)
        self.canv.bind("<B1-Motion>", self.move_token)
        self.canv.bind("<ButtonRelease-1>", self.set_token)
        self.canv.bind("<Configure>", self.configured)

        self.canv.pack(fill="both", expand=1)
        self.mob = tk.Button(master, text="Wechsle zu Gegner", command=self.toggle_mode, bg=BUTTON_BG, fg=BUTTON_FG)
        self.mob.pack(side="left")
        self.dead = tk.Button(master, text="Entferne Token", command=self.defeat_selected, bg=BUTTON_BG, fg=BUTTON_FG)
        self.dead.pack(side="left")
        self.create = tk.Button(master, text="Token erstellen", command=self.click_create, bg=BUTTON_BG, fg=BUTTON_FG)
        self.create.pack(side="left")
        self.smaller_token = tk.Button(master, text="Alle-", command=self.do_token_smaller, bg=BUTTON_BG, fg=BUTTON_FG)
        self.smaller_token.pack(side="left")
        self.bigger_token = tk.Button(master, text="Alle+", command=self.do_token_bigger, bg=BUTTON_BG, fg=BUTTON_FG)
        self.bigger_token.pack(side="left")
        self.last_token_sm = tk.Button(master, text="Einer-", command=self.do_last_token_smaller, bg=BUTTON_BG, fg=BUTTON_FG)
        self.last_token_sm.pack(side="left")
        self.last_token_bigger = tk.Button(master, text="Einer+", command=self.do_last_token_bigger, bg=BUTTON_BG, fg=BUTTON_FG)
        self.last_token_bigger.pack(side="left")
        if self.shadows:
            self.more_fog_of_war_btn = tk.Button(master, text="Schatten-", command=self.more_fog_of_war, bg=BUTTON_BG, fg=BUTTON_FG)
            self.more_fog_of_war_btn.pack(side="left")
            self.less_fog_of_war_btn = tk.Button(master, text="Schatten+", command=self.less_fog_of_war, bg=BUTTON_BG, fg=BUTTON_FG)
            self.less_fog_of_war_btn.pack(side="left")
            self.toggle_sicht_btn = tk.Button(master, text="Schatten an/aus", command=self.toggle_sicht, bg=BUTTON_BG, fg=BUTTON_FG)
            self.toggle_sicht_btn.pack(side="left")
        self.destroy_button = tk.Button(master, text="Beenden", command=self.master.destroy, bg=BUTTON_BG, fg=BUTTON_FG)
        self.destroy_button.pack(side="right")
        self.groesse_reset_btn = tk.Button(master, text="Größe Reset", command=self.groesse_reset, bg=BUTTON_BG, fg=BUTTON_FG)
        self.groesse_reset_btn.pack(side="right")
        self.reload_btn = tk.Button(master, text="Neustart", command=self.reload, bg=BUTTON_BG, fg=BUTTON_FG)
        self.reload_btn.pack(side="right")

    def reload(self):
        for t in self.tokens:
            self.canv.delete(t)
        self.tokens = []
        self.selected = -1
        self.intern_click(-1)

    def groesse_reset(self):
        for t in self.tokens:
            try:
                x1, y1, x2, y2 = self.canv.coords(t)
                x = (x1 + x2) / 2
                y = (y1 + y2) / 2
                dif = TOKEN_SIZE / 2
                self.canv.coords(t, x-dif, y-dif, x+dif, y+dif)
            except:
                pass

    def toggle_sicht(self):
        self.shadows = not self.shadows
        if not self.shadows:
            self.more_fog_of_war_btn.config(state=tk.DISABLED)
            self.less_fog_of_war_btn.config(state=tk.DISABLED)
            mask = Image.new("L", self.full_bg.size, 0xFF)
            self.full_bg.putalpha(mask)
            self.bg = ImageTk.PhotoImage(self.full_bg)
            self.canv.itemconfig(self.img, image=self.bg)
        else:
            self.more_fog_of_war_btn.config(state=tk.NORMAL)
            self.less_fog_of_war_btn.config(state=tk.NORMAL)
            self.new_shadow_thread().start()


    def kill(self,event):
        self.master.destroy()

    def show(self):
        self.master.mainloop()

    def more_fog_of_war(self):
        self.view_dist -= 100
        self.new_shadow_thread().start()

    def less_fog_of_war(self):
        self.view_dist += 100
        self.new_shadow_thread().start()

    def new_shadow_thread(self):
        return threading.Thread(target=Playfield.alpha_mask, args=(self,))

    def do_last_token_smaller(self):
        x1, y1, x2, y2 = self.canv.coords(self.clicked)
        x = x1 + x2
        y = y1 + y2
        self.canv.scale(self.clicked, x/2, y/2, 0.9, 0.9)

    def do_last_token_bigger(self):
        x1, y1, x2, y2 = self.canv.coords(self.clicked)
        x = x1 + x2
        y = y1 + y2
        self.canv.scale(self.clicked, x/2, y/2, 1.1, 1.1)


    def do_token_smaller(self):
        for t in self.tokens:
            x1, y1, x2, y2 = self.canv.coords(t)
            x = x1 + x2
            y = y1 + y2
            self.canv.scale(t, x/2, y/2, .9, .9)

    def do_token_bigger(self):
        for t in self.tokens:
            x1, y1, x2, y2 = self.canv.coords(t)
            x = x1 + x2
            y = y1 + y2
            self.canv.scale(t, x/2, y/2, 1.1, 1.1)

    def toggle_mode(self):
        if self.mode == PLAY_MODE:
            self.mode = MOB_MODE
            self.mob.config(text="Wechsle zu Spieler")
        elif self.mode == MOB_MODE:
            self.mode = PLAY_MODE
            self.mob.config(text="Wechsle zu Gegner")

    def click_create(self):
        self.canv.bind("<Button-1>", self.create_token_once)

    def _uncanvas(self, event):
        return self.canv.canvasx(event.x), self.canv.canvasx(event.y)

    def create_token_once(self, event):
        self.create_token(event)
        self.canv.bind("<Button-1>", self.select_token)

    def create_token(self, event):
        x, y = self._uncanvas(event)
        dif = TOKEN_SIZE/2
        color = "#000"
        if self.mode == PLAY_MODE:
            color = random_token_color(TOKEN_PLAYER_SCHEME)
        elif self.mode == MOB_MODE:
            color = random_token_color(TOKEN_ENEMY_SCHEME)
        oval = self.canv.create_oval(x-dif, y-dif, x+dif, y+dif, fill=color)
        self.tokens.append(oval)
        self.intern_click(oval)

    def defeat_token(self, event):
        x, y = self._uncanvas(event)
        try:
            arr = self.canv.find_overlapping(x-2, y-2, x+2, y+2)
            sel = arr[0]
            if sel == self.img and len(arr) == 1 :
                return
            sel = arr[1]
            self.canv.delete(sel)
            self.tokens.delete(sel)
            self.intern_click(-1)
        except:
            pass

    def defeat_selected(self):
        if self.clicked == -1:
            return
        self.canv.delete(self.clicked)
        self.tokens.delete(self.clicked)

    def intern_click(self, num):
        if self.clicked in self.tokens:
            self.canv.itemconfig(self.clicked, width=1, outline="#000")
        if num in self.tokens:
            self.canv.itemconfig(num, width=3, outline="#0F0")
        self.clicked = num

    def select_token(self, event):
        x, y = self._uncanvas(event)
        try:
            arr = self.canv.find_overlapping(x-2, y-2, x+2, y+2)
            sel = arr[0]
            if sel == self.img and len(arr) == 1:
                return
            elif sel == self.img:
                sel = arr[1]
            self.selected = sel
            self.intern_click(sel)
            self.last_color = self.canv.itemcget(sel, "fill")
            self.canv.itemconfig(sel, fill="#FFF")
        except:
            self.selected = -1
            self.intern_click(-1)
            return


    def configured(self, data):
        w, h = data.width, data.height
        pbg = Image.open(sys.argv[-1])
        bw ,bh = pbg.size[0], pbg.size[1]
        if float(bw)/float(w) > float(bh)/float(h):
            d = float(w)/float(bw)
            n = int(d * float(bh))
            pbg = pbg.resize((w, n), Image.ANTIALIAS)
        else:
            d = float(h)/float(bh)
            n = int(d * float(bw))
            pbg = pbg.resize((n, h), Image.ANTIALIAS)
        pbg.save("/tmp/resized_dnd.png")
        self.full_bg = pbg.copy()
        self.small_bg = pbg.resize(
            (
                int(float(w)/SHADOW_FACTOR),
                int(float(h)/SHADOW_FACTOR)
            ),
            Image.ANTIALIAS
        )
        self.bg = ImageTk.PhotoImage(self.full_bg)
        self.img = self.canv.create_image(0,0,anchor="nw",image=self.bg)
        self.canv.itemconfig(self.img, anchor="center")
        self.canv.move(self.img, w/2,h/2)

    def move_token(self, event):
        if self.selected == -1:
            return
        x, y = self._uncanvas(event)
        x1, y1, x2, y2 = self.canv.coords(self.selected)
        dif = (x2-x1)/2
        self.canv.coords(self.selected, x-dif, y-dif, x+dif, y+dif)


    def set_token(self, event):
        if self.shadows:
            self.new_shadow_thread().start()
        if self.last_color != "F0F":
            self.canv.itemconfig(self.selected, fill=self.last_color)
            self.last_color = "F0F"
        self.selected = -1
        # reload alpha mast

    def alpha_mask(self):
        img = self.small_bg.copy()
        pix = img.load() # this might be merged with the line above
        # also static in runtime... actually no need to do this here
        view_dist = int(self.view_dist / SHADOW_FACTOR)
        (tx, ty) = self.small_bg.size
        mask = Image.new("L", (tx,ty), DARKNESS_OPACITY)
        mask.load()
        mids = [
            ((x2+x1)/2/SHADOW_FACTOR, (y2+y1)/2/SHADOW_FACTOR)
            for (x1,y1,x2,y2) in [
                self.canv.coords(token) for token in self.tokens
            ]
        ]
        sin_deg = lambda i: math.sin(math.radians(i))
        cos_deg = lambda i: math.cos(math.radians(i))
        clamp = lambda i, l, h: int(min(max(l,i), min(i,h)))
        lower_bound = int((TOKEN_SIZE/2+2)/SHADOW_FACTOR)
        alpha_lookup = []
        for v in range(view_dist):
            alpha_lookup.append(max(int((1-v/view_dist)*255), DARKNESS_OPACITY))
        norm_lookup = []
        for phi in range(int(360*SHADOW_STEP_TIMES)):
            norm_lookup.append(
                (
                    sin_deg(phi/SHADOW_STEP_TIMES),
                    cos_deg(phi/SHADOW_STEP_TIMES)
                )
            )
        mix = mask.load()
        for mid in mids:
            mx, my = mid
            for (normx, normy) in norm_lookup:
                for vlen in range(view_dist):
                    x = int(vlen * normx + mx)
                    y = int(vlen * normy + my)
                    if y < 0 or y >= ty or x < 0 or x >= tx:
                        break
                    (r, g, b) = pix[x,y]
                    if (r+g+b) < 45: #~15 = 3*15
                        break
                    alpha = alpha_lookup[vlen]
                    calpha = mix[x,y]
                    if calpha == DARKNESS_OPACITY:
                        mix[x,y] = alpha
                    else:
                        mix[x,y] =  int(math.pow(alpha**2+calpha**2,0.5))

        mask = mask.resize(self.full_bg.size, Image.ANTIALIAS)
        self.full_bg.putalpha(mask)
        self.bg = ImageTk.PhotoImage(self.full_bg)
        self.canv.itemconfig(self.img, image=self.bg)



def main():
    pf = Playfield(root)
    pf.show()

def add_enemy():
    pass

def add_player():
    pass

if __name__ == '__main__':
    has_filename = False
    for a in sys.argv[1:]:
        if a[0] != "-":
            has_filename = True
            break
    if len(sys.argv) < 2 or not has_filename:
        import tkinter.filedialog as fd
        c = 0
        while True:
            fname = fd.askopenfilename(
                title       = "Hintergrund",
                initialdir  = INIT_DIR,
                filetypes   = (
                    ("Images",      "*.jpg *.png *.gif *.bmp *.jpeg"),
                    ("all files",   "*.*")
                )
            )
            if fname:
                sys.argv.append(fname)
                break
            c += 1
            if c > 1: # could resist
                sys.exit(1)
    if "-s" in sys.argv:
        ENABLE_SHADOWS = True
    elif "-S" in sys.argv:
        ENABLE_SHADOWS = False
    main()
