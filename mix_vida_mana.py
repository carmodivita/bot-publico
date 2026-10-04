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

import mss               # captura de tela rápida
import threading
import constants         # coordenadas e cores das barras
import teclas            # pg.press() protegido por lock (evita colisão com th_run)
import time


# ─────────────────────────────────────────────────────────────
#  Uma instância do mss POR THREAD
# ─────────────────────────────────────────────────────────────
#  No Windows o mss guarda handles de tela (GDI) que só valem na thread
#  que os criou. A cura roda na th_supplies e a interface lê as barras
#  na thread dela, então cada uma ganha a sua instância.
_local = threading.local()


def _sct():
    if not hasattr(_local, "sct"):
        _local.sct = mss.mss()
    return _local.sct


# ─────────────────────────────────────────────────────────────
#  pxl_match_color — Lê e compara um pixel via mss nativo
# ─────────────────────────────────────────────────────────────
#  x, y         → coordenadas LÓGICAS (1x)
#  target_color → tupla (R, G, B)
#  tolerance    → margem por canal (padrão 20, igual tortoise)
#
#  screenshot.pixel(0,0) do mss já devolve (R, G, B), na mesma ordem
#  das cores em constants.py.
def pxl_match_color(x, y, target_color, tolerance=20):
    monitor = {"top": y, "left": x, "width": 1, "height": 1}
    screenshot = _sct().grab(monitor)
    actual_color = screenshot.pixel(0, 0)
    return all(abs(a - t) <= tolerance for a, t in zip(actual_color, target_color))


# ─────────────────────────────────────────────────────────────
#  calc_width — Converte percentual em pixels dentro da barra
# ─────────────────────────────────────────────────────────────
def calc_width(percent, width=None):
    width = width or constants.WIDTH  # cada barra pode ter largura própria (region[2])
    return int(width * percent / 100)


# ─────────────────────────────────────────────────────────────
#  check_color — Verifica a cor em um ponto percentual da barra
# ─────────────────────────────────────────────────────────────
#  region  → tupla (x, y, largura, altura) — coordenadas LÓGICAS (1x)
#  percent → posição dentro da barra (ex: 50 = metade da barra)
#  color   → cor esperada quando a barra está preenchida ali
#
#  Não multiplica por 2 — mss espera 1x lógico no macOS.
def check_color(region, percent, color):
    x = region[0] + calc_width(percent, region[2])
    y = region[1]
    return pxl_match_color(x, y, color)


# ─────────────────────────────────────────────────────────────
#  bar_percent — Estima o percentual da barra (usado pela interface)
# ─────────────────────────────────────────────────────────────
#  Captura a linha da barra de uma vez e conta até onde vai a cor de
#  preenchimento, de 5 em 5%. Retorna 0–100.
def bar_percent(region, color, tolerance=20):
    x, y, width = region[0], region[1], region[2]
    if width <= 0:
        return 0
    shot = _sct().grab({"top": y, "left": x, "width": width, "height": 1})
    filled = 0
    for p in range(5, 101, 5):
        px = min(calc_width(p, width), width - 1)
        if all(abs(a - t) <= tolerance for a, t in zip(shot.pixel(px, 0), color)):
            filled = p
        else:
            break
    return filled


# ─────────────────────────────────────────────────────────────
#  regiao_preta — Detecta captura bloqueada pelo cliente
# ─────────────────────────────────────────────────────────────
#  Captura a linha da barra; se vier toda (0, 0, 0) a janela do jogo
#  está escondida de capturas de tela e nenhuma leitura é confiável.
def regiao_preta(region):
    x, y, width = region[0], region[1], max(region[2], 1)
    shot = _sct().grab({"top": y, "left": x, "width": width, "height": 1})
    return all(max(px) <= 3 for px in shot.pixels[0])


# ─────────────────────────────────────────────────────────────
#  manage_supplies — Aplica cura e mana com ordem de prioridade
# ─────────────────────────────────────────────────────────────
#  Prioridade (percentuais em constants.py / aba Ajustes):
#    1. vida < 50% → poção de vida (crítico — para aqui, não verifica exura)
#    2. vida < 80% → exura         (só se vida ≥ 50%)
#    3. mana < 40% → poção de mana (só se vida ≥ 50% — poção de vida tem prioridade)
def manage_supplies():
    # Cada cura pode ser desligada na aba Ajustes (CURA_*_ON)
    if constants.CURA_EMERG_ON and not check_color(constants.LIFE, constants.LIFE_POTION_PCT, constants.LIFE_COLOR):
        print(f"Health potion... ({constants.CURA_EMERG_ITEM})")
        teclas.press(constants.KEY_LIFE)
    else:
        if constants.CURA_MAGIA_ON and not check_color(constants.LIFE, constants.EXURA_PCT, constants.LIFE_COLOR):
            print(f"Exura... ({constants.CURA_MAGIA_ITEM})")
            teclas.press(constants.KEY_EXURA)

        if constants.CURA_MANA_ON and not check_color(constants.MANA, constants.MANA_PCT, constants.MANA_COLOR):
            print(f"Mana Potion ({constants.CURA_MANA_ITEM})")
            teclas.press(constants.KEY_MANA)


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
