# =============================================================
#  mix_vida_mana.py — Gerenciamento de vida e mana (mss nativo)
# =============================================================
#  Combina o melhor dos dois módulos:
#
#  Engine de pixel → tortoise/life_mana.py
#    Usa sct.grab(1×1) + screenshot.pixel(0,0) diretamente.
#    Sem numpy — leitura simples e direta pelo método nativo do mss.
#
#  Estrutura de lógica → _vida_mana.py
#    check_color() com percentual de barra, manage_supplies()
#    com prioridade organizada, supplies_loop() para uso em thread.
#
#  Coordenadas: LÓGICAS (1x) — mss no macOS espera 1x, não 2x.
#  Constantes LIFE e MANA em constants.py já estão em 1x.
# =============================================================

import pyautogui as pg   # usado para pg.press() — pressionar teclas
import mss               # captura de tela rápida
import constants         # coordenadas e cores das barras
import time


# ─────────────────────────────────────────────────────────────
#  Instância única do mss — criada uma vez, reutilizada sempre
# ─────────────────────────────────────────────────────────────
sct = mss.mss()


# ─────────────────────────────────────────────────────────────
#  pxl_match_color — Lê e compara um pixel via mss nativo
# ─────────────────────────────────────────────────────────────
#  x, y         → coordenadas LÓGICAS (1x)
#  target_color → tupla (R, G, B)
#  tolerance    → margem por canal (padrão 20, igual tortoise)
#
#  O mss.grab() retorna a imagem em formato BGRA.
#  screenshot.pixel(0,0) retorna (B, G, R) — reordenamos para (R, G, B)
#  antes de comparar com as cores em constants.py que estão em RGB.
def pxl_match_color(x, y, target_color, tolerance=20):
    monitor = {"top": y, "left": x, "width": 1, "height": 1}
    screenshot = sct.grab(monitor)
    b, g, r = screenshot.pixel(0, 0)
    #actual_color = (r, g, b)
    actual_color = (b,g,r)
    return all(abs(a - b) <= tolerance for a, b in zip(actual_color, target_color))


# ─────────────────────────────────────────────────────────────
#  calc_width — Converte percentual em pixels dentro da barra
# ─────────────────────────────────────────────────────────────
def calc_width(percent):
    return int(constants.WIDTH * percent / 100)


# ─────────────────────────────────────────────────────────────
#  check_color — Verifica a cor em um ponto percentual da barra
# ─────────────────────────────────────────────────────────────
#  region  → tupla (x, y, largura, altura) — coordenadas LÓGICAS (1x)
#  percent → posição dentro da barra (ex: 50 = metade da barra)
#  color   → cor esperada quando a barra está preenchida ali
#
#  Não multiplica por 2 — mss espera 1x lógico no macOS.
def check_color(region, percent, color):
    x = region[0] + calc_width(percent)
    y = region[1]
    return pxl_match_color(x, y, color)


# ─────────────────────────────────────────────────────────────
#  manage_supplies — Aplica cura e mana com ordem de prioridade
# ─────────────────────────────────────────────────────────────
#  Prioridade:
#    1. vida < 50% → poção de vida (crítico — para aqui, não verifica exura)
#    2. vida < 80% → exura         (só se vida ≥ 50%)
#    3. mana < 40% → poção de mana (sempre, independente do branch de vida)
def manage_supplies():
    if not check_color(constants.LIFE, 50, constants.LIFE_COLOR):
        print("Heath potion...")
        pg.press(constants.KEY_LIFE)
    else:
        if not check_color(constants.LIFE, 80, constants.LIFE_COLOR):
            print("Exura...")
            pg.press(constants.KEY_EXURA)

        if not check_color(constants.MANA, 40, constants.MANA_COLOR):
            print("Mana Potion")
            pg.press(constants.KEY_MANA)


# ─────────────────────────────────────────────────────────────
#  supplies_loop — Loop contínuo para rodar em thread separada
# ─────────────────────────────────────────────────────────────
#  stop_event → threading.Event do ThreadController (para com ESC)
#  interval   → intervalo entre checagens em segundos
#
#  Não recebe pause_event — cura continua mesmo quando bot pausado.
def supplies_loop(stop_event, interval=0.8):
    while not stop_event.is_set():
        manage_supplies()
        time.sleep(interval)
