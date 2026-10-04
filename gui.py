# =============================================================
#  gui.py — Interface gráfica do Huntix
# =============================================================
#  Telas (menu lateral):
#    Painel      → iniciar / pausar / parar, vida e mana ao vivo, progresso, log
#    Rota        → as 20 flags com miniatura; captura cada uma direto daqui
#    Calibração  → assistente passo a passo (minimapa, batalha, barras...)
#    Ajustes     → hotkeys do jogo, % de cura, teclas do bot (salva em ajustes.json)
#    Ajuda       → mostra o COMO_USAR.txt
#
#  Uso:  pythonw gui.py  (ou o atalho "Huntix.lnk")
#
#  Teclas globais (funcionam com o Tibia em foco, mudam na aba Ajustes):
#    Insert → iniciar | CapsLock → pausar/retomar | End → parar
#    Home → capturar | Page Down → pular   (só durante calibração/captura)
#  Diferente do main.py, aqui a tecla de parar só para o bot — a janela continua aberta.
# =============================================================

import ctypes
import importlib
import json
import os
import platform
import queue
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)


# ── Log: tudo que o bot imprime com print() vai para a janela ──
class _QueueWriter:
    def __init__(self, q, original):
        self.q = q
        self.original = original

    def write(self, text):
        if text:
            self.q.put(text)
        if self.original:
            try:
                self.original.write(text)
            except Exception:
                pass

    def flush(self):
        if self.original:
            try:
                self.original.flush()
            except Exception:
                pass


LOG_QUEUE = queue.Queue()
sys.stdout = _QueueWriter(LOG_QUEUE, sys.stdout)  # pythonw: sys.stdout é None
sys.stderr = _QueueWriter(LOG_QUEUE, sys.stderr)

# Faz o Windows mostrar o ícone do bot na barra de tarefas (e não o do Python)
if platform.system() == "Windows":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("huntix.gui")
    except Exception:
        pass

os.environ["BOT_CALIBRANDO"] = "1"  # a própria interface avisa se falta calibrar

import customtkinter as ctk
import pyautogui as pg
from PIL import Image
from pynput import keyboard

import constants
import mix_vida_mana
import calibrar
import biblioteca
import main  # cria o objeto bot e as funções de jogo (o listener do terminal não roda)

# ─────────────────────────────────────────────────────────────
#  Paleta e fontes
# ─────────────────────────────────────────────────────────────
# Tema neon: azul-marinho quase preto + ciano elétrico
BG = "#060912"
SIDEBAR = "#090e1b"
CARD = "#0c1322"
CARD_HI = "#112036"
BORDER = "#16263f"
BORDER_GLOW = "#0e4a5c"   # borda ciano apagada (cards em destaque)
TEXT = "#e4f3ff"
MUTED = "#7b8bad"
DIM = "#46557a"
ACCENT = "#00e5ff"        # ciano neon — cor principal
ACCENT_HOVER = "#00b8d9"
ACCENT_DIM = "#05242e"
ON_ACCENT = "#00141a"
GREEN = "#00ffa3"         # verde menta neon
AMBER = "#ffb547"
RED = "#ff4d6d"
HP = "#ff3d81"            # rosa neon
MP = "#8b5cff"            # violeta
TRACK = "#14203a"

STATE_STYLE = {
    "parado":  ("Parado",   MUTED),
    "rodando": ("Rodando",  GREEN),
    "pausado": ("Pausado",  AMBER),
    "parando": ("Parando…", RED),
}

ICON_ICO = os.path.join(BASE, "assets", "huntix.ico")
ICON_PNG = os.path.join(BASE, "assets", "huntix_256.png")
GUIDE = os.path.join(BASE, "COMO_USAR.txt")
AJUSTES = os.path.join(BASE, "ajustes.json")
IS_MAC = platform.system() == "Darwin"

# Passo da calibração → chave que ele grava em coords_windows.json (para saber se já foi feito)
STEP_KEY = {"map_tl": "MAP_REGION", "map_br": "MAP_REGION", "battle_tl": "BATTLE_REGION",
            "battle_br": "BATTLE_REGION", "atk": "ATK_X", "atk_pink": "PNK_ATK",
            "life_l": "LIFE", "life_r": "LIFE", "mana_l": "MANA", "mana_r": "MANA",
            "stairs": "stairs_x", "rope": "ROPE_X", "shovel": "SHOVEL_X",
            "bp_tl": "BACKPACK_REGION", "bp_br": "BACKPACK_REGION", "drop": "DROP_X"}
OPTIONAL_STEPS = {"atk_pink", "stairs", "rope", "shovel", "bp_tl", "bp_br", "drop"}
SEM_ACAO = "sem ação"  # opção do menu de ação da flag (aba Rota)

# Teclas oferecidas para controlar o bot (nada de F1–F12: são hotkeys do Tibia)
CONTROL_KEYS = [k for k in ("insert", "home", "end", "page_up", "page_down", "delete", "pause",
                            "scroll_lock", "caps_lock", "num_lock", "print_screen")
                if hasattr(keyboard.Key, k)]


def F(size, weight="normal", family="Bahnschrift"):
    return ctk.CTkFont(family, size, weight)


def key_name(name):
    """Nome amigável da tecla (page_down → PageDown)."""
    return "".join(p.capitalize() for p in name.split("_"))


def img_dir():
    return os.path.join(BASE, constants.IMG_DIR)


def pixel_img(path, size):
    """Abre a imagem ampliada sem borrar (estilo pixel-art)."""
    im = Image.open(path).convert("RGBA")
    big = im.resize((size, size), Image.NEAREST)
    return ctk.CTkImage(big, size=(size, size))


def autowrap(label, pad=40):
    """Quebra o texto conforme a largura do CONTÊINER (wraplength fixo cortava em telas menores).
    Usa o pai, e não o próprio label: mudar o wraplength redimensiona o label, o que dispararia
    um novo <Configure> nele e entraria em loop."""
    parent = label.master
    last = {"w": None}

    def on_resize(e):
        w = max(120, e.width - pad)
        if last["w"] is None or abs(w - last["w"]) > 4:
            last["w"] = w
            label.configure(wraplength=w)

    parent.bind("<Configure>", on_resize, add="+")
    return label


_ICON_CACHE = {}


def ui_icon(nome, size=22):
    """Ícone neon de assets/ui/<nome>.png (gerados por tools/gerar_icones_ui.py)."""
    k = (nome, size)
    if k not in _ICON_CACHE:
        caminho = os.path.join(BASE, "assets", "ui", f"{nome}.png")
        _ICON_CACHE[k] = ctk.CTkImage(Image.open(caminho), size=(size, size)) if os.path.exists(caminho) else None
    return _ICON_CACHE[k]


# ── Teclas do jogo: pynput → nome do pyautogui ───────────────
_MODS = {"shift": ("shift", "shift_l", "shift_r"), "ctrl": ("ctrl", "ctrl_l", "ctrl_r"),
         "alt": ("alt", "alt_l", "alt_r", "alt_gr")}
_MOD_KEYS = {getattr(keyboard.Key, n): m for m, ns in _MODS.items() for n in ns if hasattr(keyboard.Key, n)}
_SPECIAL = {"space": "space", "enter": "enter", "tab": "tab", "backspace": "backspace", "delete": "delete",
            "insert": "insert", "home": "home", "end": "end", "page_up": "pageup", "page_down": "pagedown",
            "up": "up", "down": "down", "left": "left", "right": "right", "esc": "esc",
            "caps_lock": "capslock", "num_lock": "numlock", "scroll_lock": "scrolllock", "pause": "pause",
            "print_screen": "printscreen", **{f"f{i}": f"f{i}" for i in range(1, 25)}}
_SPECIAL_KEYS = {getattr(keyboard.Key, n): v for n, v in _SPECIAL.items() if hasattr(keyboard.Key, n)}


def game_key_name(key, mods):
    """Converte a tecla apertada (+ modificadores segurados) para o formato do pyautogui:
    'f1', 'shift+f1', 'ctrl+3', 'num5'... Retorna None para teclas não suportadas."""
    if key in _SPECIAL_KEYS:
        base = _SPECIAL_KEYS[key]
    elif isinstance(key, keyboard.KeyCode):
        vk = key.vk
        # usa o código da tecla e não o caractere: com Shift, '1' vira '!' e 'a' vira 'A'
        if vk is not None and 96 <= vk <= 105:
            base = f"num{vk - 96}"
        elif vk is not None and (48 <= vk <= 57 or 65 <= vk <= 90):
            base = chr(vk).lower()
        elif key.char and key.char.isprintable():
            base = key.char.lower()
        else:
            return None
    else:
        return None
    if base not in pg.KEYBOARD_KEYS:
        return None
    prefix = [m for m in ("ctrl", "alt", "shift") if m in mods]
    return "+".join(prefix + [base])


def key_label(v):
    """'shift+f1' → 'Shift + F1', 'pageup' → 'PageUp', 'num5' → 'Num 5'."""
    nomes = {"pageup": "PageUp", "pagedown": "PageDown", "capslock": "CapsLock", "numlock": "NumLock",
             "scrolllock": "ScrollLock", "printscreen": "PrintScreen", "esc": "Esc", "backspace": "Backspace"}
    partes = []
    for x in str(v).split("+") if v != "+" else ["+"]:
        if x in nomes:
            partes.append(nomes[x])
        elif x.startswith("num") and x[3:].isdigit():
            partes.append(f"Num {x[3:]}")
        elif len(x) == 1:
            partes.append(x.upper())
        else:
            partes.append(x[:1].upper() + x[1:])
    return " + ".join(partes)


# ── Opções de cura por vocação (dados da biblioteca) ─────────
VOCACOES = {"knight": ("Knight", "Knights"), "paladin": ("Paladin", "Paladins"),
            "druid": ("Druid", "Druids"), "sorcerer": ("Sorcerer", "Sorcerers"),
            "monk": ("Monk", "Monks")}
OUTRO = "Outro (personalizado)"
# Itens que não servem para a cura automática no Tibia atual (descontinuados ou de quest/treino)
_ITENS_FORA = {"Lifefluid", "Manafluid", "Distilled Superior Mana Potion", "Distilled Ultimate Mana Potion"}


def opcoes_magia(voc, todas):
    """Magias de cura da vocação (vocações do Tibia atual, segundo a TibiaWiki)."""
    plural = VOCACOES[voc][1]
    out = [r for r in biblioteca.carregar("magias")
           if r.get("tipo") == "Cura" and not r["nome"].startswith("Cure")
           and (todas or plural in r["vocacoes"])]
    return sorted(out, key=lambda r: (r.get("level") or 0, r["nome"]))


def opcoes_item(kind):
    """kind 'vida' ou 'mana': poções que recuperam aquilo (Spirit recupera os dois)."""
    chaves = {"vida": ("Health Potion", "Spirit Potion"), "mana": ("Mana Potion", "Spirit Potion")}[kind]
    out = [r for r in biblioteca.carregar("suprimentos")
           if r.get("tipo") == "poção" and any(k in r["nome"] for k in chaves) and r["nome"] not in _ITENS_FORA]
    tamanho = ("Small", "", "Strong", "Great", "Ultimate", "Supreme")
    def ordem(r):
        primeira = r["nome"].split()[0]
        return (tamanho.index(primeira) if primeira in tamanho else 1, r["nome"])
    return sorted(out, key=ordem)


def rotulo_cura(r):
    if r.get("palavras") and r.get("mana") is not None:
        return f"{r['nome']}  ·  {r['palavras']}  ·  {r['mana']} mana"
    if r.get("tipo") in ("runa", "fluido", "poção"):
        return f"{r['nome']}  ·  {r['tipo']}"
    return r["nome"]


def accent_button(master, text, command, **kw):
    return ctk.CTkButton(master, text=text, command=command, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                         text_color=ON_ACCENT, font=F(13, "bold"), corner_radius=9, **kw)


def ghost_button(master, text, command, **kw):
    kw.setdefault("font", F(12))
    return ctk.CTkButton(master, text=text, command=command, fg_color=TRACK, hover_color=BORDER,
                         corner_radius=8, **kw)


# ─────────────────────────────────────────────────────────────
#  Componentes
# ─────────────────────────────────────────────────────────────
class Card(ctk.CTkFrame):
    def __init__(self, master, title=None, icon=None, **kw):
        super().__init__(master, fg_color=CARD, corner_radius=14, border_width=1,
                         border_color=BORDER, **kw)
        if title:
            ctk.CTkLabel(self, text=("  " if icon else "") + title.upper(), text_color=MUTED,
                         image=ui_icon(icon, 16) if icon else None, compound="left",
                         font=F(11, "bold")).pack(anchor="w", padx=16, pady=(12, 2))


class StatBar(ctk.CTkFrame):
    """Rótulo + barra + valor (vida, mana, rota)."""

    def __init__(self, master, label, color, icon=None):
        super().__init__(master, fg_color="transparent")
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=("  " if icon else "") + label, text_color=TEXT, font=F(13),
                     image=ui_icon(icon, 18) if icon else None, compound="left").pack(side="left")
        self.value = ctk.CTkLabel(top, text="—", text_color=TEXT, font=F(13, "bold"))
        self.value.pack(side="right")
        self.color = color
        self.bar = ctk.CTkProgressBar(self, height=10, corner_radius=5, fg_color=TRACK,
                                      progress_color=color)
        self.bar.pack(fill="x", pady=(4, 0))
        self.set(0, "—")

    def set(self, fraction, text):
        fraction = max(0.0, min(1.0, fraction))
        # em 0 o CTkProgressBar ainda desenha um pontinho; esconde com a cor do trilho
        self.bar.configure(progress_color=self.color if fraction > 0 else TRACK)
        self.bar.set(fraction)
        self.value.configure(text=text)


class Metric(ctk.CTkFrame):
    def __init__(self, master, label, icon=None):
        super().__init__(master, fg_color=CARD, corner_radius=12, border_width=1,
                         border_color=BORDER)
        ctk.CTkLabel(self, text=("  " if icon else "") + label, text_color=MUTED, font=F(11),
                     image=ui_icon(icon, 16) if icon else None, compound="left").pack(
            anchor="w", padx=14, pady=(10, 0))
        self.value = ctk.CTkLabel(self, text="—", text_color=TEXT, font=F(18, "bold"))
        self.value.pack(anchor="w", padx=14, pady=(0, 10))

    def set(self, text):
        self.value.configure(text=text)


# ─────────────────────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("Huntix")
        self.geometry("1000x680")
        self.minsize(920, 620)
        if os.path.exists(ICON_ICO):
            self.iconbitmap(ICON_ICO)
            # o customtkinter troca o ícone ~200ms depois de abrir; reaplica por cima
            self.after(300, lambda: self.iconbitmap(ICON_ICO))

        self.keys = queue.Queue()     # teclas globais (vêm da thread do pynput)
        self.hp = self.mp = None
        self.run_started = None
        self.log_newline = True       # True = próxima escrita começa linha nova (põe horário)
        self.wiz = None               # assistente de calibração em andamento
        self.flag_capture = None      # captura de flags em andamento
        self.flag_sig = None
        self.junk_capture = False     # captura de item de lixo em andamento
        self.cur_wp_shown = None
        self.current = None

        self._build()
        self.show("painel")
        self.mods = set()             # Shift/Ctrl/Alt segurados agora
        self.listener = keyboard.Listener(on_press=self._on_key, on_release=self._on_release)
        self.listener.start()
        threading.Thread(target=self._bars_worker, daemon=True).start()
        self.after(50, self._poll_keys)
        self.after(100, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════════
    #  Estrutura: menu lateral + páginas
    # ══════════════════════════════════════════════════════════
    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0, width=210)
        side.grid(row=0, column=0, sticky="ns")
        side.grid_propagate(False)
        side.pack_propagate(False)

        logo = ctk.CTkFrame(side, fg_color="transparent")
        logo.pack(fill="x", padx=18, pady=(22, 26))
        if os.path.exists(ICON_PNG):
            self.logo_img = ctk.CTkImage(Image.open(ICON_PNG), size=(46, 46))
            ctk.CTkLabel(logo, image=self.logo_img, text="").pack(side="left")
        t = ctk.CTkFrame(logo, fg_color="transparent")
        t.pack(side="left", padx=10)
        ctk.CTkLabel(t, text="HUNTIX", text_color=ACCENT, font=F(24, "bold")).pack(anchor="w")
        ctk.CTkLabel(t, text="HUNT  ·  AUTOMATION", text_color=DIM, font=F(9)).pack(anchor="w")

        self.nav = {}
        for key, label, icone in (("painel", "Painel", "painel"), ("rota", "Rota", "rota"),
                                  ("lixo", "Lixo", "lootear"), ("calib", "Calibração", "capturar"),
                                  ("ajustes", "Ajustes", "ajustes"),
                                  ("ajuda", "Ajuda", "ajuda")):
            item = ctk.CTkFrame(side, fg_color="transparent")
            item.pack(fill="x", padx=(0, 12), pady=2)
            bar = ctk.CTkFrame(item, width=3, height=26, corner_radius=2, fg_color=SIDEBAR)
            bar.pack(side="left", padx=(0, 9))
            b = ctk.CTkButton(item, text="  " + label, image=ui_icon(icone, 20), compound="left",
                              anchor="w", height=40, corner_radius=10,
                              font=F(14), fg_color="transparent", hover_color=CARD_HI,
                              text_color=MUTED, command=lambda k=key: self.show(k))
            b.pack(side="left", fill="x", expand=True)
            self.nav[key] = (b, bar)

        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=16)
        self.pill = ctk.CTkLabel(bottom, text="", corner_radius=10, fg_color=CARD, height=34,
                                 font=F(13, "bold"))
        self.pill.pack(fill="x")
        self.side_keys = ctk.CTkLabel(bottom, text="", text_color=DIM, font=F(11), justify="left")
        self.side_keys.pack(anchor="w", pady=(10, 0))
        self.topmost = ctk.CTkSwitch(bottom, text="Sempre no topo", text_color=MUTED, font=F(12),
                                     progress_color=ACCENT, command=self._toggle_top)
        self.topmost.pack(anchor="w", pady=(10, 0))

        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.pages = {
            "painel": self._page_painel(),
            "rota": self._page_rota(),
            "lixo": self._page_lixo(),
            "calib": self._page_calib(),
            "ajustes": self._page_ajustes(),
            "ajuda": self._page_ajuda(),
        }
        self._refresh_side_keys()

    def show(self, name):
        for page in self.pages.values():
            page.grid_forget()
        self.pages[name].grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
        for k, (b, bar) in self.nav.items():
            on = k == name
            b.configure(fg_color=CARD_HI if on else "transparent", text_color=ACCENT if on else MUTED)
            bar.configure(fg_color=ACCENT if on else SIDEBAR)
        self.current = name
        if name == "rota":
            self._refresh_flags(force=True)
        if name == "calib":
            self._refresh_steps()
        if name == "lixo":
            self._refresh_junk()

    def _header(self, master, title, subtitle, icon=None):
        h = ctk.CTkFrame(master, fg_color="transparent")
        h.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(h, text=("  " if icon else "") + title, text_color=TEXT, font=F(24, "bold"),
                     image=ui_icon(icon, 28) if icon else None, compound="left").pack(anchor="w")
        sub = ctk.CTkLabel(h, text=subtitle, text_color=MUTED, font=F(13), justify="left",
                           wraplength=700, anchor="w")
        sub.pack(anchor="w", fill="x")
        autowrap(sub)
        return sub

    # ══════════════════════════════════════════════════════════
    #  Painel
    # ══════════════════════════════════════════════════════════
    def _page_painel(self):
        p = ctk.CTkFrame(self.content, fg_color="transparent")

        # aviso de calibração pendente (aparece/some no _tick)
        self.banner = ctk.CTkFrame(p, fg_color=ACCENT_DIM, corner_radius=12)
        self.banner_text = ctk.CTkLabel(self.banner, text="", text_color=ACCENT, font=F(13),
                                        image=ui_icon("dica", 20), compound="left")
        self.banner_text.pack(side="left", padx=16, pady=10)
        accent_button(self.banner, "Resolver →", self._go_fix, width=110, height=30).pack(side="right", padx=10)

        # controles
        self.hero = Card(p)
        self.hero.configure(border_color=BORDER_GLOW)
        self.hero.pack(fill="x", pady=(0, 12))
        self.hero.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(self.hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=20, pady=16)
        ctk.CTkLabel(left, text="ESTADO", text_color=MUTED, font=F(11, "bold")).pack(anchor="w")
        self.state_big = ctk.CTkLabel(left, text="Parado", text_color=MUTED, font=F(26, "bold"))
        self.state_big.pack(anchor="w")
        btns = ctk.CTkFrame(self.hero, fg_color="transparent")
        btns.grid(row=0, column=2, padx=20, pady=16)
        bt = {"height": 44, "width": 130, "corner_radius": 10, "font": F(14, "bold")}
        self.b_start = ctk.CTkButton(btns, text=" Iniciar", image=ui_icon("iniciar_dark", 18), fg_color=GREEN,
                                     hover_color="#00d68a", text_color="#00140c", command=main.bot.start, **bt)
        self.b_pause = ctk.CTkButton(btns, text=" Pausar", image=ui_icon("pausar", 18), fg_color=TRACK,
                                     hover_color=BORDER, command=main.bot.toggle_pause, **bt)
        self.b_stop = ctk.CTkButton(btns, text=" Parar", image=ui_icon("parar", 18), fg_color=TRACK,
                                    hover_color="#3a1426", text_color=RED, command=main.bot.stop, **bt)
        for i, b in enumerate((self.b_start, self.b_pause, self.b_stop)):
            b.grid(row=0, column=i, padx=4)

        # personagem + rota
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=(0, 12))
        row.grid_columnconfigure((0, 1), weight=1, uniform="r")
        char = Card(row, "Personagem", icon="personagem")
        char.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.s_hp = StatBar(char, "Vida", HP, icon="emergencia")
        self.s_hp.pack(fill="x", padx=16, pady=(4, 8))
        self.s_mp = StatBar(char, "Mana", MP, icon="mana")
        self.s_mp.pack(fill="x", padx=16, pady=(0, 16))

        route = Card(row, "Rota", icon="rota")
        route.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.s_route = StatBar(route, "Waypoint", ACCENT, icon="rota")
        self.s_route.pack(fill="x", padx=16, pady=(4, 8))
        nxt = ctk.CTkFrame(route, fg_color="transparent")
        nxt.pack(fill="x", padx=16, pady=(0, 14))
        self.cur_flag_img = ctk.CTkLabel(nxt, text="", width=36, height=36, fg_color=BG, corner_radius=6)
        self.cur_flag_img.pack(side="left")
        self.cur_action = ctk.CTkLabel(nxt, text="Parado", text_color=TEXT, font=F(13))
        self.cur_action.pack(side="left", padx=10)

        # métricas
        mets = ctk.CTkFrame(p, fg_color="transparent")
        mets.pack(fill="x", pady=(0, 12))
        mets.grid_columnconfigure((0, 1, 2), weight=1, uniform="m")
        self.m_kills = Metric(mets, "Abates", icon="caveira")
        self.m_rate = Metric(mets, "Abates / hora", icon="grafico")
        self.m_time = Metric(mets, "Tempo rodando", icon="relogio")
        for i, m in enumerate((self.m_kills, self.m_rate, self.m_time)):
            m.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))

        # log
        logc = Card(p)
        logc.pack(fill="both", expand=True)
        lh = ctk.CTkFrame(logc, fg_color="transparent")
        lh.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(lh, text="  LOG", image=ui_icon("log", 16), compound="left", text_color=MUTED,
                     font=F(11, "bold")).pack(side="left")
        ghost_button(lh, "Limpar", self._clear_log, width=64, height=24, font=F(11)).pack(side="right")
        self.log = ctk.CTkTextbox(logc, fg_color=BG, text_color="#b8c7e0", corner_radius=8,
                                  font=F(12, family="Consolas"), wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for tag, color in (("time", DIM), ("ok", GREEN), ("heal", MP), ("warn", AMBER), ("err", RED)):
            self.log.tag_config(tag, foreground=color)
        self.log.configure(state="disabled")
        return p

    def _go_fix(self):
        self.show("calib" if not self._calibrated() else "rota")

    # ══════════════════════════════════════════════════════════
    #  Rota
    # ══════════════════════════════════════════════════════════
    def _page_rota(self):
        p = ctk.CTkFrame(self.content, fg_color="transparent")
        self.rota_sub = self._header(p, "Rota", "", icon="rota")
        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        self.rota_status = ctk.CTkLabel(bar, text="", text_color=MUTED, font=F(13))
        self.rota_status.pack(side="left")
        self.b_seq = accent_button(bar, " Capturar em sequência", self._flags_sequence, height=34,
                                   image=ui_icon("capturar_dark", 18))
        self.b_seq.pack(side="right")

        grid = ctk.CTkScrollableFrame(p, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        cols = 5
        for c in range(cols):
            grid.grid_columnconfigure(c, weight=1, uniform="f")
        self.tiles = {}
        for i, item in enumerate(main.dados):
            n = item["file"]
            tile = ctk.CTkFrame(grid, fg_color=CARD, corner_radius=12, border_width=2, border_color=BORDER)
            tile.grid(row=i // cols, column=i % cols, sticky="nsew", padx=5, pady=5)
            img = ctk.CTkLabel(tile, text="?", width=56, height=56, fg_color=BG, corner_radius=8,
                               text_color=DIM, font=F(20, "bold"))
            img.pack(pady=(12, 6))
            ctk.CTkLabel(tile, text=f"Flag {n}", text_color=TEXT, font=F(13, "bold")).pack()
            ctk.CTkLabel(tile, text=f"espera {item.get('wait', 0)}s", text_color=MUTED, font=F(11)).pack()
            # Ação ao chegar na flag (escada/buraco): clique esquerdo, direito, corda ou pá
            acao = main.action_of(item)
            menu = ctk.CTkOptionMenu(tile, values=[SEM_ACAO] + list(main.ACTION_NAMES.values()), height=26,
                                     fg_color=BG, button_color=TRACK, button_hover_color=BORDER,
                                     dropdown_fg_color=CARD, font=F(11),
                                     command=lambda v, it=item: self._set_action(it, v))
            menu.set(main.ACTION_NAMES[acao] if acao else SEM_ACAO)
            menu.pack(fill="x", padx=12, pady=(6, 0))
            btn = ghost_button(tile, "Capturar", lambda k=n: self._flag_start([k]), height=26,
                               image=ui_icon("capturar", 14))
            btn.pack(fill="x", padx=12, pady=(8, 12))
            self.tiles[n] = {"frame": tile, "img": img, "btn": btn, "path": item["path"]}
        self._rota_default_sub()
        return p

    def _set_action(self, item, nome):
        for k in main.ACTIONS:      # some com o formato antigo ("stairs": true)
            item.pop(k, None)
        acao = next((k for k, v in main.ACTION_NAMES.items() if v == nome), None)
        if acao:
            item["acao"] = acao
        else:
            item.pop("acao", None)
        main.save_route()
        print(f"Flag {item['file']}: ação = {nome}.")

    def _flag_file(self, n):
        return os.path.join(img_dir(), os.path.basename(self.tiles[n]["path"]))

    def _refresh_flags(self, force=False):
        sig = tuple(os.path.getmtime(self._flag_file(n)) if os.path.exists(self._flag_file(n)) else 0
                    for n in self.tiles)
        if not force and sig == self.flag_sig:
            return
        self.flag_sig = sig
        have = 0
        atual = self.flag_capture["fila"][0] if self.flag_capture and self.flag_capture["fila"] else None
        for n, t in self.tiles.items():
            f = self._flag_file(n)
            if os.path.exists(f):
                have += 1
                t["img"].configure(image=pixel_img(f, 48), text="")
            else:
                t["img"].configure(image=None, text="?")
            if n == atual:
                t["btn"].configure(text=f"Aperte {key_name(constants.CAPTURE_KEY)}…", text_color=ACCENT)
            else:
                t["btn"].configure(text="Recapturar" if os.path.exists(f) else "Capturar", text_color=TEXT)
        total = len(self.tiles)
        self.rota_status.configure(text=f"{have} de {total} flags capturadas",
                                   text_color=GREEN if have == total else AMBER)

    def _flags_sequence(self):
        if self.flag_capture:
            self._flag_end("Captura de flags cancelada.")
            return
        faltando = [n for n in self.tiles if not os.path.exists(self._flag_file(n))]
        self._flag_start(faltando or list(self.tiles))

    def _flag_start(self, fila):
        if self.wiz:
            self._wiz_end("Assistente de calibração interrompido.")
        if self.junk_capture:
            self._junk_end("Captura de lixo interrompida.")
        self.flag_capture = {"fila": list(fila)}
        self.b_seq.configure(text=" Cancelar captura", fg_color=TRACK, text_color=RED, hover_color=BORDER,
                             image=ui_icon("parar", 18))
        self._flag_highlight()

    def _flag_highlight(self):
        atual = self.flag_capture["fila"][0]
        for n, t in self.tiles.items():
            t["frame"].configure(border_color=ACCENT if n == atual else BORDER)
        self._refresh_flags(force=True)
        self.rota_sub.configure(
            text=f"Flag {atual}: no Tibia, ponha o mouse no CENTRO da flag no minimapa e aperte "
                 f"{key_name(constants.CAPTURE_KEY)}.   {key_name(constants.SKIP_KEY)} pula  ·  "
                 f"{key_name(constants.STOP_KEY)} cancela.",
            text_color=ACCENT)

    def _flag_key(self, kind, pos):
        fila = self.flag_capture["fila"]
        n = fila[0]
        if kind == "capture":
            if not calibrar.salvar_flag(os.path.basename(self.tiles[n]["path"]), pos):
                return  # recorte inválido → continua na mesma flag para tentar de novo
            print(f"Flag {n} capturada em {pos}.")
        fila.pop(0)
        if fila:
            self._flag_highlight()
        else:
            self._flag_end("Captura de flags concluída.")

    def _flag_end(self, msg):
        self.flag_capture = None
        print(msg)
        self.b_seq.configure(text=" Capturar em sequência", fg_color=ACCENT, text_color=ON_ACCENT,
                             hover_color=ACCENT_HOVER, image=ui_icon("capturar_dark", 18))
        for t in self.tiles.values():
            t["frame"].configure(border_color=BORDER)
        self._rota_default_sub()
        self._refresh_flags(force=True)

    def _rota_default_sub(self):
        self.rota_sub.configure(
            text=f"Os waypoints na ordem do info.json. Para capturar: clique em Capturar, ponha o mouse "
                 f"sobre a flag no minimapa do Tibia e aperte {key_name(constants.CAPTURE_KEY)}.",
            text_color=MUTED)

    # ══════════════════════════════════════════════════════════
    #  Lixo — itens que o bot joga no chão
    # ══════════════════════════════════════════════════════════
    def _page_lixo(self):
        p = ctk.CTkFrame(self.content, fg_color="transparent")
        self.junk_sub = self._header(p, "Lixo", "", icon="lootear")
        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        self.junk_status = ctk.CTkLabel(bar, text="", text_color=MUTED, font=F(13))
        self.junk_status.pack(side="left")
        self.b_junk = accent_button(bar, " Adicionar item", self._junk_toggle, height=34,
                                    image=ui_icon("capturar_dark", 18))
        self.b_junk.pack(side="right")
        self.junk_grid = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self.junk_grid.pack(fill="both", expand=True)
        for c in range(6):
            self.junk_grid.grid_columnconfigure(c, weight=1, uniform="j")
        self._junk_default_sub()
        return p

    def _junk_default_sub(self):
        self.junk_sub.configure(
            text="Itens que o bot joga no chão depois de lootear. Clique em Adicionar item, ponha o mouse no "
                 f"MEIO do item na mochila do loot e aperte {key_name(constants.CAPTURE_KEY)}. "
                 "Calibre antes o grupo Lixo (mochila e ponto do chão) na aba Calibração.",
            text_color=MUTED)

    def _refresh_junk(self):
        for w in self.junk_grid.winfo_children():
            w.destroy()
        itens = calibrar.itens_lixo()
        for i, caminho in enumerate(itens):
            tile = ctk.CTkFrame(self.junk_grid, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
            tile.grid(row=i // 6, column=i % 6, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(tile, image=pixel_img(caminho, 48), text="", width=56, height=56, fg_color=BG,
                         corner_radius=8).pack(pady=(12, 6))
            ctk.CTkLabel(tile, text=os.path.splitext(os.path.basename(caminho))[0], text_color=TEXT,
                         font=F(12, "bold")).pack()
            ghost_button(tile, "Remover", lambda c=caminho: self._junk_remove(c), height=26,
                         text_color=RED).pack(fill="x", padx=12, pady=(8, 12))
        cfg = calibrar.carregar()
        falta = [n for n, k in (("mochila", "BACKPACK_REGION"), ("ponto do chão", "DROP_X")) if k not in cfg]
        txt = f"{len(itens)} {'item' if len(itens) == 1 else 'itens'} de lixo"
        if falta:
            txt += f"  ·  calibre: {', '.join(falta)} (descarte desligado)"
        self.junk_status.configure(text=txt, text_color=AMBER if falta else (GREEN if itens else MUTED))

    def _junk_remove(self, caminho):
        try:
            os.remove(caminho)
            print(f"Lixo removido: {os.path.basename(caminho)}.")
        except OSError as e:
            print(f"Não consegui remover {caminho}: {e}")
        self._refresh_junk()

    def _junk_toggle(self):
        if self.junk_capture:
            self._junk_end("Captura de lixo encerrada.")
            return
        if self.wiz:
            self._wiz_end("Assistente de calibração interrompido.")
        if self.flag_capture:
            self._flag_end("Captura de flags interrompida.")
        self.junk_capture = True
        self.b_junk.configure(text=" Concluir", fg_color=TRACK, text_color=RED, hover_color=BORDER,
                              image=ui_icon("parar", 18))
        self.junk_sub.configure(
            text=f"No Tibia, ponha o mouse no MEIO do item de lixo na mochila e aperte "
                 f"{key_name(constants.CAPTURE_KEY)}. Pode capturar vários seguidos.   "
                 f"{key_name(constants.STOP_KEY)} ou {key_name(constants.SKIP_KEY)} encerra.",
            text_color=ACCENT)

    def _junk_key(self, pos):
        caminho = calibrar.salvar_lixo(pos)
        if caminho:
            print(f"Lixo capturado em {pos}: {os.path.basename(caminho)}.")
            self._refresh_junk()

    def _junk_end(self, msg):
        self.junk_capture = False
        print(msg)
        self.b_junk.configure(text=" Adicionar item", fg_color=ACCENT, text_color=ON_ACCENT,
                              hover_color=ACCENT_HOVER, image=ui_icon("capturar_dark", 18))
        self._junk_default_sub()
        self._refresh_junk()

    # ══════════════════════════════════════════════════════════
    #  Calibração
    # ══════════════════════════════════════════════════════════
    def _page_calib(self):
        p = ctk.CTkFrame(self.content, fg_color="transparent")
        self._header(p, "Calibração", icon="capturar", subtitle="Ensina ao bot onde ficam o minimapa, a lista de batalha e as barras "
                                      "na SUA tela. Deixe o Tibia aberto do jeito que você joga.")
        body = ctk.CTkFrame(p, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=2, uniform="c")
        body.grid_columnconfigure(1, weight=3, uniform="c")
        body.grid_rowconfigure(0, weight=1)

        steps = Card(body, "Passos", icon="log")
        steps.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.step_rows = []
        grupo = None
        for i, st in enumerate(calibrar.STEPS):
            if st["grupo"] != grupo:
                grupo = st["grupo"]
                icone = {"Minimapa": "mapa", "Lista de batalha": "batalha", "Ataque": "atacar", "Vida": "emergencia",
                         "Mana": "mana", "Ações": "corda", "Lixo": "lootear"}.get(grupo)
                ctk.CTkLabel(steps, text=("  " if icone else "") + grupo, text_color=DIM, font=F(11, "bold"),
                             image=ui_icon(icone, 15) if icone else None, compound="left").pack(
                    anchor="w", padx=18, pady=(6, 0))
            short = st["curto"]
            b = ctk.CTkButton(steps, text="", anchor="w", height=24, corner_radius=6,
                              fg_color="transparent", hover_color=CARD_HI, font=F(12),
                              command=lambda k=i: self._wiz_start(k))
            b.pack(fill="x", padx=10)
            self.step_rows.append((b, short))

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        cur = Card(right)
        cur.pack(fill="x")
        self.wiz_count = ctk.CTkLabel(cur, text="", text_color=ACCENT, font=F(12, "bold"))
        self.wiz_count.pack(anchor="w", padx=20, pady=(16, 0))
        self.wiz_text = ctk.CTkLabel(cur, text="", text_color=TEXT, font=F(17, "bold"),
                                     wraplength=300, justify="left", anchor="w")
        self.wiz_text.pack(anchor="w", fill="x", padx=20, pady=(4, 12))
        autowrap(self.wiz_text)
        chips = ctk.CTkFrame(cur, fg_color="transparent")
        chips.pack(anchor="w", padx=20)
        self.chips = []
        for _ in range(3):
            c = ctk.CTkLabel(chips, text="", fg_color=CARD_HI, corner_radius=8, text_color=TEXT,
                             font=F(12), height=28)
            c.pack(side="left", padx=(0, 6))
            self.chips.append(c)
        bb = ctk.CTkFrame(cur, fg_color="transparent")
        bb.pack(fill="x", padx=20, pady=16)
        self.b_wiz = accent_button(bb, " Iniciar assistente", self._wiz_toggle, height=38,
                                   image=ui_icon("iniciar_dark", 18))
        self.b_wiz.pack(side="left")
        self.b_wiz_back = ghost_button(bb, "← Voltar", self._wiz_back, height=38, width=90, font=F(13))
        self.b_wiz_back.pack(side="left", padx=8)

        live = Card(right, "Mouse agora", icon="mouse")
        live.pack(fill="x", pady=(12, 0))
        lr = ctk.CTkFrame(live, fg_color="transparent")
        lr.pack(fill="x", padx=16, pady=(4, 16))
        self.swatch = ctk.CTkFrame(lr, width=44, height=44, corner_radius=8, fg_color=BG,
                                   border_width=1, border_color=BORDER)
        self.swatch.pack(side="left")
        self.live_text = ctk.CTkLabel(lr, text="", text_color=TEXT, font=F(13, family="Consolas"),
                                      justify="left")
        self.live_text.pack(side="left", padx=12)

        tip = Card(right, "Dica", icon="dica")
        tip.pack(fill="x", pady=(12, 0))
        autowrap(ctk.CTkLabel(tip, text="Clique em qualquer passo da lista para refazer só ele. Cada captura "
                                        "é salva na hora em coords_windows.json — não precisa fazer tudo de "
                                        "uma vez.", text_color=MUTED, font=F(12), justify="left", anchor="w")
                 ).pack(anchor="w", fill="x", padx=16, pady=(0, 14))
        self._wiz_render()
        return p

    def _refresh_steps(self):
        cfg = calibrar.carregar()
        atual = self.wiz["i"] if self.wiz else None
        for i, ((b, short), st) in enumerate(zip(self.step_rows, calibrar.STEPS)):
            done = STEP_KEY[st["id"]] in cfg
            opt = st["id"] in OPTIONAL_STEPS
            if i == atual:
                mark, color = "▶", ACCENT
            elif done:
                mark, color = "✓", GREEN
            elif opt:
                mark, color = "○", DIM
            else:
                mark, color = "•", AMBER
            label = short + ("  (opcional)" if opt and not done and i != atual else "")
            b.configure(text=f"{mark}   {label}", text_color=color if i == atual or not done else TEXT,
                        fg_color=CARD_HI if i == atual else "transparent")

    def _wiz_toggle(self):
        if self.wiz:
            self._wiz_end("Assistente cancelado.")
            return
        cfg = calibrar.carregar()
        pend = [i for i, st in enumerate(calibrar.STEPS)
                if STEP_KEY[st["id"]] not in cfg and st["id"] not in OPTIONAL_STEPS]
        self._wiz_start(pend[0] if pend else 0)

    def _wiz_start(self, i):
        if self.flag_capture:
            self._flag_end("Captura de flags interrompida.")
        if self.junk_capture:
            self._junk_end("Captura de lixo interrompida.")
        # passo que é a 2ª ponta de uma região/barra → começa pela 1ª ponta
        if i > 0 and calibrar.STEPS[i - 1]["aplicar"] is None and calibrar.STEPS[i]["aplicar"]:
            i -= 1
        if not self.wiz:
            self.wiz = {"i": i, "pts": {}, "cfg": calibrar.carregar()}
        self.wiz["i"] = i
        self._wiz_render()

    def _wiz_back(self):
        if self.wiz and self.wiz["i"] > 0:
            self.wiz["i"] -= 1
            self._wiz_render()

    def _wiz_key(self, kind, pos):
        st = calibrar.STEPS[self.wiz["i"]]
        if kind == "capture":
            if calibrar.captura_bloqueada(st, self.wiz["pts"], pos):
                print(f"✗ Calibração: {calibrar.AVISO_PRETO}")
                return  # não grava preto como cor/template; continua no mesmo passo
            if calibrar.aplicar_passo(st, self.wiz["cfg"], self.wiz["pts"], pos):
                importlib.reload(constants)  # barras de vida/mana passam a funcionar na hora
                print(f"Calibração: {st['grupo']} salvo.")
            else:
                print(f"Calibração: ponto {pos} anotado ({st['grupo']}).")
        self.wiz["i"] += 1
        if self.wiz["i"] >= len(calibrar.STEPS):
            self._wiz_end("Calibração concluída! Agora capture as flags na aba Rota.")
        else:
            self._wiz_render()

    def _wiz_end(self, msg):
        self.wiz = None
        importlib.reload(constants)
        print(msg)
        self._wiz_render()

    def _wiz_render(self):
        for chip, (k, label) in zip(self.chips, ((constants.CAPTURE_KEY, "capturar"),
                                                 (constants.SKIP_KEY, "pular"),
                                                 (constants.STOP_KEY, "cancelar"))):
            chip.configure(text=f"  {key_name(k)}  ·  {label}  ")
        if self.wiz:
            i = self.wiz["i"]
            st = calibrar.STEPS[i]
            self.wiz_count.configure(text=f"PASSO {i + 1} DE {len(calibrar.STEPS)}  ·  {st['grupo'].upper()}")
            self.wiz_text.configure(text=st["texto"] + ".")
            self.b_wiz.configure(text=" Cancelar", fg_color=TRACK, text_color=RED, hover_color=BORDER,
                                 image=ui_icon("parar", 18))
            self.b_wiz_back.configure(state="normal" if i > 0 else "disabled")
        else:
            self.wiz_count.configure(text="PRONTO PARA COMEÇAR")
            self.wiz_text.configure(text="Clique em Iniciar assistente. Em cada passo, ponha o mouse no lugar "
                                         "pedido dentro do Tibia e aperte a tecla de capturar.")
            self.b_wiz.configure(text=" Iniciar assistente", fg_color=ACCENT, text_color=ON_ACCENT,
                                 hover_color=ACCENT_HOVER, image=ui_icon("iniciar_dark", 18))
            self.b_wiz_back.configure(state="disabled")
        self._refresh_steps()

    # ══════════════════════════════════════════════════════════
    #  Ajustes
    # ══════════════════════════════════════════════════════════
    def _page_ajustes(self):
        p = ctk.CTkFrame(self.content, fg_color="transparent")
        self._header(p, "Ajustes", icon="ajustes", subtitle="Valem na hora, inclusive com o bot rodando, e ficam salvos em ajustes.json.")
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        self.aj_scroll = sc
        sc.grid_columnconfigure((0, 1), weight=1, uniform="a")
        self.aj_keys = {}        # campo → tecla escolhida (ex.: "KEY_ATK": "t")
        self.key_buttons = {}    # campo → botão que mostra a tecla
        self.key_capture = None  # campo sendo capturado agora
        self.aj_menus = {}

        def label(master, icone, texto, sub=None):
            box = ctk.CTkFrame(master, fg_color="transparent")
            ctk.CTkLabel(box, text="", image=ui_icon(icone, 24), width=28).pack(side="left")
            t = ctk.CTkFrame(box, fg_color="transparent")
            t.pack(side="left", padx=(8, 0))
            ctk.CTkLabel(t, text=texto, text_color=TEXT, font=F(13)).pack(anchor="w")
            if sub:
                ctk.CTkLabel(t, text=sub, text_color=DIM, font=F(11)).pack(anchor="w")
            return box

        def hint(card, texto):
            autowrap(ctk.CTkLabel(card, text=texto, text_color=DIM, font=F(11), wraplength=300,
                                  justify="left", anchor="w"), pad=36).pack(anchor="w", fill="x", padx=16, pady=(4, 14))

        # ── Hotkeys do jogo ──────────────────────────────────
        game = Card(sc, "Hotkeys do jogo", icon="tecla")
        game.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
        for campo, icone, texto in (("KEY_ATK", "atacar", "Atacar"), ("KEY_LOOT", "lootear", "Lootear"),
                                    ("KEY_ROPE", "corda", "Corda (rope)"), ("KEY_SHOVEL", "pa", "Pá (shovel)")):
            r = ctk.CTkFrame(game, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=5)
            label(r, icone, texto).pack(side="left")
            self._key_button(r, campo).pack(side="right")
        hint(game, "Clique no botão e aperte a tecla no teclado. Vale combinação: Shift + F1, Ctrl + 3…")

        # ── Teclas do bot ────────────────────────────────────
        ctl = Card(sc, "Teclas do bot", icon="ajustes")
        ctl.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 12))
        names = [key_name(k) for k in CONTROL_KEYS]
        for campo, icone, texto in (("START_KEY", "iniciar", "Iniciar"), ("PAUSE_KEY", "pausar", "Pausar / retomar"),
                                    ("STOP_KEY", "parar", "Parar / cancelar"),
                                    ("CAPTURE_KEY", "capturar", "Capturar (calibração)"),
                                    ("SKIP_KEY", "pular", "Pular (calibração)")):
            r = ctk.CTkFrame(ctl, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=3)
            label(r, icone, texto).pack(side="left")
            m = ctk.CTkOptionMenu(r, values=names, width=124, height=30, fg_color=BG, button_color=TRACK,
                                  button_hover_color=BORDER, dropdown_fg_color=CARD, font=F(12))
            m.pack(side="right")
            self.aj_menus[campo] = m
        hint(ctl, "F1–F12 ficam de fora porque são hotkeys do Tibia.")

        # ── Cura automática ──────────────────────────────────
        heal = Card(sc, "Cura automática", icon="emergencia")
        heal.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 12))
        top = ctk.CTkFrame(heal, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(top, text="Vocação", text_color=MUTED, font=F(12)).pack(side="left", padx=(0, 10))
        self.voc_buttons = {}
        for voc, (nome, _) in VOCACOES.items():
            b = ctk.CTkButton(top, text=nome, image=ui_icon(voc, 20), compound="left", width=104, height=36,
                              corner_radius=9, font=F(13), fg_color=BG, hover_color=CARD_HI, border_width=1,
                              border_color=BORDER, command=lambda v=voc: self._set_voc(v))
            b.pack(side="left", padx=(0, 6))
            self.voc_buttons[voc] = b
        filtros = ctk.CTkFrame(heal, fg_color="transparent")
        filtros.pack(fill="x", padx=16, pady=(0, 8))
        self.cura_todas = ctk.CTkSwitch(filtros, text="Mostrar magias de todas as vocações", text_color=MUTED,
                                        font=F(12), progress_color=ACCENT, command=self._cura_refresh)
        self.cura_todas.pack(side="left")

        self.slots = {}
        for slot, icone, titulo, sub, campo_key, campo_pct, campo_item, campo_on, cor in (
                ("emerg", "emergencia", "Cura de emergência", "vida crítica — poção ou magia forte",
                 "KEY_LIFE", "LIFE_POTION_PCT", "CURA_EMERG_ITEM", "CURA_EMERG_ON", HP),
                ("magia", "magia", "Magia de cura", "vida baixa",
                 "KEY_EXURA", "EXURA_PCT", "CURA_MAGIA_ITEM", "CURA_MAGIA_ON", HP),
                ("mana", "mana", "Mana", "mana baixa — poção",
                 "KEY_MANA", "MANA_PCT", "CURA_MANA_ITEM", "CURA_MANA_ON", MP)):
            box = ctk.CTkFrame(heal, fg_color=BG, corner_radius=12, border_width=1, border_color=BORDER)
            box.pack(fill="x", padx=16, pady=4)
            box.grid_columnconfigure(0, minsize=250)  # mesma largura nas 3 caixas → colunas alinhadas
            box.grid_columnconfigure(1, weight=1)
            label(box, icone, titulo, sub).grid(row=0, column=0, rowspan=2, sticky="w", padx=14, pady=10)
            item = ctk.CTkOptionMenu(box, values=[OUTRO], height=30, fg_color=CARD, button_color=TRACK,
                                     button_hover_color=BORDER, dropdown_fg_color=CARD, font=F(12),
                                     dynamic_resizing=False)
            item.grid(row=0, column=1, sticky="ew", padx=(6, 8), pady=(10, 2))
            kb = self._key_button(box, campo_key)
            kb.grid(row=0, column=2, padx=(0, 8), pady=(10, 2))
            on = ctk.CTkSwitch(box, text="", width=46, progress_color=cor)
            on.grid(row=0, column=3, padx=(0, 12), pady=(10, 2))
            sl_row = ctk.CTkFrame(box, fg_color="transparent")
            sl_row.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(6, 12), pady=(2, 10))
            ctk.CTkLabel(sl_row, text="usar abaixo de", text_color=DIM, font=F(11)).pack(side="left")
            val = ctk.CTkLabel(sl_row, text="", text_color=cor, font=F(13, "bold"), width=44)
            val.pack(side="right")
            sl = ctk.CTkSlider(sl_row, from_=5, to=95, number_of_steps=18, progress_color=cor, button_color=cor,
                               button_hover_color=cor, fg_color=TRACK,
                               command=lambda v, l=val: l.configure(text=f"{int(v)}%"))
            sl.pack(side="left", fill="x", expand=True, padx=10)
            self.slots[slot] = {"item": item, "on": on, "slider": sl, "val": val, "pct": campo_pct,
                                "campo_item": campo_item, "campo_on": campo_on, "opcoes": {}}
        hint(heal, "A cura de emergência tem prioridade: abaixo dela o bot não usa a magia nem a mana. "
                   "As opções vêm da pasta biblioteca/ (dados da TibiaWiki BR).")

        # ── Rota ─────────────────────────────────────────────
        rt = Card(sc, "Rota", icon="rota")
        rt.grid(row=2, column=0, sticky="nsew", padx=(0, 6))
        r = ctk.CTkFrame(rt, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=4)
        label(r, "tentativas", "Tentativas por waypoint").pack(side="left")
        self.aj_menus["MAX_WAYPOINT_ATTEMPTS"] = ctk.CTkOptionMenu(
            r, values=[str(i) for i in range(1, 9)], width=80, height=30, fg_color=BG, button_color=TRACK,
            button_hover_color=BORDER, dropdown_fg_color=CARD, font=F(12))
        self.aj_menus["MAX_WAYPOINT_ATTEMPTS"].pack(side="right")
        hint(rt, "Quantas vezes o bot tenta chegar numa flag (matando o que bloquear) antes de seguir "
                 "para a próxima.")

        foot = ctk.CTkFrame(p, fg_color="transparent")
        foot.pack(fill="x", pady=(12, 0))
        self.aj_msg = ctk.CTkLabel(foot, text="", font=F(13))
        self.aj_msg.pack(side="left")
        accent_button(foot, "Salvar ajustes", self._aj_save, height=40, width=150).pack(side="right")
        ghost_button(foot, "Desfazer", self._aj_load, height=40, width=100, font=F(13)).pack(side="right", padx=8)
        self._aj_load()
        return p

    # ── Botão que captura uma tecla ──────────────────────────
    def _key_button(self, master, campo):
        b = ctk.CTkButton(master, text="", image=ui_icon("tecla", 18), compound="left", width=118, height=32,
                          corner_radius=8, font=F(13, "bold"), fg_color=CARD_HI, hover_color=BORDER,
                          border_width=1, border_color=BORDER, text_color=TEXT,
                          command=lambda: self._capture_key(campo))
        self.key_buttons[campo] = b
        return b

    def _show_key(self, campo):
        cap = self.key_capture == campo
        self.key_buttons[campo].configure(
            text="Aperte…" if cap else key_label(self.aj_keys.get(campo, "")),
            border_color=ACCENT if cap else BORDER, text_color=ACCENT if cap else TEXT)

    def _capture_key(self, campo):
        anterior = self.key_capture
        self.key_capture = None if anterior == campo else campo  # clicar de novo cancela
        if anterior:
            self._show_key(anterior)
        if self.key_capture:
            self._show_key(campo)
            self.aj_msg.configure(text="Aperte a tecla (Esc cancela).", text_color=ACCENT)
        else:
            self.aj_msg.configure(text="")

    def _key_captured(self, key, mods):
        campo = self.key_capture
        if key == keyboard.Key.esc:
            self.key_capture = None
            self._show_key(campo)
            self.aj_msg.configure(text="")
            return
        if key in _MOD_KEYS:
            return  # só o Shift/Ctrl/Alt: espera a tecla principal
        nome = game_key_name(key, mods)
        if not nome:
            self.aj_msg.configure(text="✗  Essa tecla não é suportada — tente outra.", text_color=RED)
            return
        # teclas de controle do bot, convertidas para o formato do pyautogui (page_up → pageup)
        controle = {_SPECIAL.get(getattr(constants, k), getattr(constants, k))
                    for k in ("START_KEY", "PAUSE_KEY", "STOP_KEY", "CAPTURE_KEY", "SKIP_KEY")}
        if nome in controle:
            self.aj_msg.configure(text=f"✗  {key_label(nome)} já é uma tecla do bot — escolha outra.", text_color=RED)
            return
        self.aj_keys[campo] = nome
        self.key_capture = None
        self._show_key(campo)
        repetida = [k for k, v in self.aj_keys.items() if v == nome and k != campo]
        self.aj_msg.configure(
            text=f"⚠  {key_label(nome)} também está em outro item." if repetida else
            f"{key_label(nome)} definida — clique em Salvar ajustes.",
            text_color=AMBER if repetida else ACCENT)

    # ── Cura por vocação ─────────────────────────────────────
    def _set_voc(self, voc):
        self.cura_voc = voc
        for v, b in self.voc_buttons.items():
            on = v == voc
            b.configure(fg_color="#0b3d4a" if on else BG, border_color=ACCENT if on else BORDER,
                        text_color=ACCENT if on else TEXT)
        self._cura_refresh()

    def _cura_refresh(self, escolhas=None):
        """Recarrega as listas de cada cura conforme vocação e filtros, mantendo a escolha atual."""
        todas = bool(self.cura_todas.get())
        listas = {"emerg": opcoes_item("vida") + opcoes_magia(self.cura_voc, todas),
                  "magia": opcoes_magia(self.cura_voc, todas),
                  "mana": opcoes_item("mana")}
        for slot, regs in listas.items():
            sl = self.slots[slot]
            atual = (escolhas or {}).get(slot) or sl.get("escolha")
            sl["opcoes"] = {rotulo_cura(r): r["nome"] for r in regs}
            valores = list(sl["opcoes"]) + [OUTRO]
            sl["item"].configure(values=valores)
            rot = next((k for k, n in sl["opcoes"].items() if n == atual), None)
            # se a escolha não existe na nova vocação, pega a 1ª da lista (só fica em "Outro" se foi escolhido)
            sl["item"].set(rot or (OUTRO if atual == OUTRO else valores[0]))
            sl["escolha"] = sl["opcoes"].get(sl["item"].get(), atual or OUTRO)

    def _aj_load(self):
        self.key_capture = None
        for campo in self.key_buttons:
            self.aj_keys[campo] = getattr(constants, campo)
            self._show_key(campo)
        for campo, m in self.aj_menus.items():
            v = getattr(constants, campo)
            m.set(str(v) if campo == "MAX_WAYPOINT_ATTEMPTS" else key_name(v))
        for sl in self.slots.values():
            v = getattr(constants, sl["pct"])
            sl["slider"].set(v)
            sl["val"].configure(text=f"{int(v)}%")
            sl["on"].select() if getattr(constants, sl["campo_on"]) else sl["on"].deselect()
            sl["escolha"] = getattr(constants, sl["campo_item"])
        self.cura_voc = constants.CURA_VOCACAO if constants.CURA_VOCACAO in VOCACOES else "knight"
        self._set_voc(self.cura_voc)
        self.aj_msg.configure(text="")

    def _aj_save(self):
        by_name = {key_name(k): k for k in CONTROL_KEYS}
        data = dict(self.aj_keys)
        for campo, m in self.aj_menus.items():
            data[campo] = int(m.get()) if campo == "MAX_WAYPOINT_ATTEMPTS" else by_name[m.get()]
        ctl = [data[k] for k in ("START_KEY", "PAUSE_KEY", "STOP_KEY", "CAPTURE_KEY", "SKIP_KEY")]
        if len(set(ctl)) != len(ctl):
            self.aj_msg.configure(text="✗  As teclas do bot precisam ser diferentes entre si.", text_color=RED)
            return
        for sl in self.slots.values():
            data[sl["pct"]] = int(sl["slider"].get())
            data[sl["campo_on"]] = bool(sl["on"].get())
            data[sl["campo_item"]] = sl["opcoes"].get(sl["item"].get(), sl["item"].get())
        if data["CURA_EMERG_ON"] and data["CURA_MAGIA_ON"] and data["LIFE_POTION_PCT"] >= data["EXURA_PCT"]:
            self.aj_msg.configure(text="✗  A cura de emergência precisa disparar ABAIXO da magia de cura.",
                                  text_color=RED)
            return
        data["CURA_VOCACAO"] = self.cura_voc
        with open(AJUSTES, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        importlib.reload(constants)
        self._refresh_side_keys()
        self._wiz_render()
        if not self.flag_capture:
            self._rota_default_sub()
        self.aj_msg.configure(text="✓  Ajustes salvos.", text_color=GREEN)
        print("Ajustes salvos.")

    # ══════════════════════════════════════════════════════════
    #  Ajuda
    # ══════════════════════════════════════════════════════════
    def _page_ajuda(self):
        p = ctk.CTkFrame(self.content, fg_color="transparent")
        self._header(p, "Ajuda", icon="livro", subtitle="O mesmo conteúdo do arquivo COMO_USAR.txt, na pasta do projeto.")
        box = ctk.CTkTextbox(p, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=14,
                             text_color=TEXT, font=F(13, family="Consolas"), wrap="word")
        box.pack(fill="both", expand=True)
        try:
            with open(GUIDE, "r", encoding="utf-8") as f:
                box.insert("1.0", f.read())
        except OSError:
            box.insert("1.0", "COMO_USAR.txt não encontrado.")
        box.configure(state="disabled")
        return p

    # ══════════════════════════════════════════════════════════
    #  Teclas globais
    # ══════════════════════════════════════════════════════════
    def _on_key(self, key):
        # roda na thread do pynput: só anota a tecla, a posição do mouse e os modificadores
        if key in _MOD_KEYS:
            self.mods.add(_MOD_KEYS[key])
        try:
            self.keys.put((key, pg.position(), frozenset(self.mods)))
        except Exception:
            pass

    def _on_release(self, key):
        if key in _MOD_KEYS:
            self.mods.discard(_MOD_KEYS[key])

    def _poll_keys(self):
        while not self.keys.empty():
            key, pos, mods = self.keys.get_nowait()
            if self.key_capture:          # definindo uma hotkey do jogo: a tecla é só para isso
                self._key_captured(key, mods)
                continue
            K = keyboard.Key
            cap = getattr(K, constants.CAPTURE_KEY)
            skip = getattr(K, constants.SKIP_KEY)
            stop = getattr(K, constants.STOP_KEY)
            if self.junk_capture and key in (cap, skip, stop):
                if key == cap:
                    self._junk_key((int(pos[0]), int(pos[1])))
                else:
                    self._junk_end("Captura de lixo encerrada.")
                continue
            if (self.wiz or self.flag_capture) and key in (cap, skip, stop):
                pos = (int(pos[0]), int(pos[1]))
                if self.wiz:
                    self._wiz_end("Assistente cancelado.") if key == stop else \
                        self._wiz_key("capture" if key == cap else "skip", pos)
                else:
                    self._flag_end("Captura de flags cancelada.") if key == stop else \
                        self._flag_key("capture" if key == cap else "skip", pos)
                continue
            main.key_code(key)  # iniciar / pausar / parar (sem fechar a janela)
        self.after(50, self._poll_keys)

    def _refresh_side_keys(self):
        self.side_keys.configure(text=f"{key_name(constants.START_KEY)}  ·  iniciar\n"
                                      f"{key_name(constants.PAUSE_KEY)}  ·  pausar\n"
                                      f"{key_name(constants.STOP_KEY)}  ·  parar")

    # ══════════════════════════════════════════════════════════
    #  Atualização periódica
    # ══════════════════════════════════════════════════════════
    def _bars_worker(self):
        # thread própria para a leitura de tela não travar a janela
        while True:
            if self._calibrated():
                try:
                    self.hp = mix_vida_mana.bar_percent(constants.LIFE, constants.LIFE_COLOR)
                    self.mp = mix_vida_mana.bar_percent(constants.MANA, constants.MANA_COLOR)
                except Exception:
                    self.hp = self.mp = None
            else:
                self.hp = self.mp = None
            time.sleep(0.5)

    def _calibrated(self):
        if IS_MAC:
            return True
        cfg = calibrar.carregar()
        return all(k in cfg for k in ("MAP_REGION", "BATTLE_REGION", "ATK_X", "LIFE", "MANA"))

    def _write_log(self, text):
        self.log.configure(state="normal")
        for piece in text.splitlines(keepends=True):
            if self.log_newline:
                self.log.insert("end", time.strftime("%H:%M:%S  "), "time")
            low = piece.lower()
            if "error" in low or "traceback" in low:
                tag = "err"
            elif any(w in low for w in ("not found", "aviso", "skipping", "didn't", "not visible",
                                        "cancelad", "time out", "interromp")):
                tag = "warn"
            elif "potion" in low or "exura" in low:
                tag = "heal"
            elif any(w in low for w in ("dead", "salv", "conclu", "capturad", "started")):
                tag = "ok"
            else:
                tag = None
            if tag:
                self.log.insert("end", piece, tag)
            else:
                self.log.insert("end", piece)
            self.log_newline = piece.endswith("\n")
        lines = int(self.log.index("end-1c").split(".")[0])
        if lines > 600:
            self.log.delete("1.0", f"{lines - 600}.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.log_newline = True

    def _tick(self):
        try:
            self._update()
        finally:
            self.after(150, self._tick)

    def _update(self):
        chunks = []
        while not LOG_QUEUE.empty():
            chunks.append(LOG_QUEUE.get_nowait())
        if chunks:
            self._write_log("".join(chunks))

        # estado
        state = main.bot.state()
        text, color = STATE_STYLE[state]
        self.pill.configure(text=f"●  {text}", text_color=color)
        self.state_big.configure(text=text, text_color=color)
        running = state in ("rodando", "pausado")
        self.b_start.configure(state="normal" if state == "parado" else "disabled")
        self.b_pause.configure(state="normal" if running else "disabled",
                               text=" Retomar" if state == "pausado" else " Pausar",
                               image=ui_icon("iniciar" if state == "pausado" else "pausar", 18))
        self.b_stop.configure(state="normal" if running else "disabled")
        if running and self.run_started is None:
            self.run_started = time.time()
        elif state == "parado":
            self.run_started = None

        # aviso de calibração pendente
        nflags = sum(os.path.exists(self._flag_file(n)) for n in self.tiles)
        total = len(self.tiles)
        if not self._calibrated():
            msg = "Calibração incompleta: o bot ainda não sabe onde ficam as coisas na sua tela."
        elif nflags < total:
            msg = f"Faltam flags da rota: {nflags} de {total} capturadas."
        else:
            msg = None
        if msg:
            self.banner_text.configure(text=msg)
            if not self.banner.winfo_ismapped():
                self.banner.pack(fill="x", pady=(0, 12), before=self.hero)
        elif self.banner.winfo_ismapped():
            self.banner.pack_forget()

        # personagem
        for bar, val in ((self.s_hp, self.hp), (self.s_mp, self.mp)):
            if val is None:
                bar.set(0, "—")
            else:
                bar.set(val / 100, f"{val}%")

        # rota
        st = main.status
        wp = st["waypoint"] if running else 0
        self.s_route.set(wp / (st["total"] or 1), f"{wp} / {st['total']}")
        self.cur_action.configure(text=st["acao"] if running else "Parado")
        show_wp = wp if wp in self.tiles and os.path.exists(self._flag_file(wp)) else None
        if show_wp != self.cur_wp_shown:
            if show_wp:
                self.cur_flag_img.configure(image=pixel_img(self._flag_file(show_wp), 28), text="")
            else:
                self.cur_flag_img.configure(image=None, text="")
            self.cur_wp_shown = show_wp
        if not self.flag_capture:
            for n, t in self.tiles.items():
                t["frame"].configure(border_color=ACCENT if running and n == wp else BORDER)

        # métricas
        kills = st["kills"]
        self.m_kills.set(str(kills))
        if self.run_started:
            s = int(time.time() - self.run_started)
            self.m_time.set(f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}")
            self.m_rate.set(f"{kills / (s / 3600):.0f}" if s >= 60 else "—")
        else:
            self.m_time.set("—")
            self.m_rate.set("—")

        # telas com atualização ao vivo
        if self.current == "rota":
            self._refresh_flags()
        elif self.current == "calib":
            x, y = pg.position()
            c = pg.pixel(x, y)
            self.swatch.configure(fg_color="#%02x%02x%02x" % tuple(c[:3]))
            self.live_text.configure(text=f"x = {x}   y = {y}\nRGB  {c[0]}, {c[1]}, {c[2]}")

    def _toggle_top(self):
        self.attributes("-topmost", bool(self.topmost.get()))

    def _on_close(self):
        main.bot.stop()
        try:
            self.listener.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    App().mainloop()
