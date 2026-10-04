# =============================================================
#  teclas.py — Envio de teclas protegido por lock
# =============================================================
#  th_run (ataque/loot/navegação) e th_supplies (cura) apertam teclas
#  ao mesmo tempo. Sem proteção, a poção podia cair no meio do combo
#  loot → ataque. Todo pg.press() do bot passa por aqui.
#
#  Uso:
#    teclas.press("f")             → uma tecla
#    teclas.press("shift+f1")      → combinação (Shift/Ctrl/Alt + tecla)
#    with teclas.KEY_LOCK: ...     → sequência que não pode ser interrompida
# =============================================================

import threading
import pyautogui as pg

# RLock: a mesma thread pode chamar press() de dentro de um "with KEY_LOCK"
KEY_LOCK = threading.RLock()


def press(key):
    with KEY_LOCK:
        if key != "+" and "+" in key:
            pg.hotkey(*key.split("+"))  # ex.: "ctrl+f1" → segura Ctrl, aperta F1
        else:
            pg.press(key)
