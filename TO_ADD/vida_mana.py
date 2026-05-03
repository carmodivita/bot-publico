# =============================================================
#  vida_mana.py — Gerenciamento de vida e mana (opencv + mss)
# =============================================================
#  Substitui totalmente o life_mana.py para leitura de pixels.
#  Ao invés de usar pyautogui.pixelMatchesColor() (que é lento
#  e chama o sistema para CADA pixel), esta versão tira um
#  screenshot da região da barra com mss (muito mais rápido)
#  e processa com numpy para comparar cores.
#
#  Resultado: leitura de vida e mana em MILISSEGUNDOS.
#
#  Dependências adicionais:
#    pip install mss numpy opencv-python
#
#  pyautogui.press() ainda é usado para pressionar teclas.
#  Se quiser substituir no futuro, alternativas comentadas abaixo.
# =============================================================

import pyautogui as pg   # ainda usado para pg.press() — leitura de pixel foi migrada
import numpy as np       # arrays de pixels do screenshot
import cv2               # opencv — importado para futuras comparações avançadas
                         # (ex: template matching de ícone de buff, check_battle)
import mss               # captura de tela RÁPIDA — muito mais rápido que pyautogui
import constants         # coordenadas e cores das barras de vida/mana
import time              # para time.sleep() no intervalo do loop

# ─────────────────────────────────────────────────────────────
#  Alternativa para pressionar teclas sem pyautogui
# ─────────────────────────────────────────────────────────────
#  Para remover COMPLETAMENTE o pyautogui, use pynput para
#  pressionar teclas também. O pynput já é importado em main.py
#  para o listener, então a dependência já existe no projeto.
#
#  Descomente as duas linhas abaixo e comente o import pg acima:
#
#    from pynput.keyboard import Controller as KeyboardController
#    KEYBOARD = KeyboardController()
#
#  E substitua cada pg.press() por KEYBOARD.press() + release()
#  como mostrado nos comentários junto a cada pg.press() abaixo.
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
#  IMPORTANTE — Sistema de coordenadas com mss no macOS Retina
# ─────────────────────────────────────────────────────────────
#  O mss no macOS usa coordenadas LÓGICAS (1x) para o grab(),
#  igual ao sistema operacional. Diferente do pyautogui que
#  exigia coordenadas físicas (2x), aqui NÃO multiplicamos por
#  SCALE antes de passar para o mss.
#
#  Porém, a imagem RETORNADA pelo mss no Retina está em
#  resolução FÍSICA (2x) — um grab de 4x4 lógicos vira 8x8
#  pixels no array numpy. Por isso o centro é calculado
#  dinamicamente com shape[0]//2, shape[1]//2.
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
#  Inicialização do mss — instância única e reutilizável
# ─────────────────────────────────────────────────────────────
#  Criado UMA VEZ fora das funções. Criar mss() repetidamente
#  dentro de um loop é caro — esta instância é reutilizada
#  em todas as capturas do supplies_loop.
sct = mss.mss()


# ─────────────────────────────────────────────────────────────
#  screenshot_pixel — Lê a cor de um pixel via mss + numpy
# ─────────────────────────────────────────────────────────────
#  x, y → coordenadas em pixels LÓGICOS (1x) — mss espera isso
#          no macOS, independente de ser tela Retina ou não.
#
#  Retorna uma tupla (R, G, B).
def screenshot_pixel(x, y):
    # Captura uma pequena região ao redor do pixel alvo.
    # Usamos 4x4 lógicos para garantir que o ponto está no centro
    # mesmo em Retina (onde a imagem retornada será 8x8 físicos).
    # mss espera: {"left": x, "top": y, "width": w, "height": h}
    region = {"left": x, "top": y, "width": 4, "height": 4}

    img = sct.grab(region)

    # Converte para array numpy — shape: (altura, largura, 4) no formato BGRA
    # No Retina a imagem é 2x: um grab 4x4 lógico vira 8x8 físico.
    px = np.array(img)

    # Calcula o centro dinamicamente para funcionar tanto em 1x quanto 2x.
    # px.shape = (altura, largura, canais)
    cy = px.shape[0] // 2   # centro vertical
    cx = px.shape[1] // 2   # centro horizontal

    # mss retorna no formato BGRA — extraímos e reordenamos para RGB
    b, g, r, _ = px[cy, cx]
    print(b,g,r)
    return (int(r), int(g), int(b))   # retorna como tupla (R, G, B)


# ─────────────────────────────────────────────────────────────
#  pixel_matches_color — Compara um pixel capturado com uma cor
# ─────────────────────────────────────────────────────────────
#  Substitui pg.pixelMatchesColor().
#  x, y      → coordenadas LÓGICAS (1x) — mss espera logical
#  color     → tupla (R, G, B)
#  tolerance → margem aceitável por canal (0-255)
#
#  Retorna True se a cor está dentro da tolerância em todos os canais.
def pixel_matches_color(x, y, color, tolerance=10):
    pixel = screenshot_pixel(x, y)

    # Compara canal a canal: abs(capturado - esperado) <= tolerância
    # all() retorna True só se TODOS os três canais (R, G, B) passarem
    return all(abs(pixel[c] - color[c]) <= tolerance for c in range(3))


# ─────────────────────────────────────────────────────────────
#  calc_width — Converte percentual em pixels dentro da barra
# ─────────────────────────────────────────────────────────────
#  Igual ao life_mana.py — sem alterações.
def calc_width(percent):
    return int(constants.WIDTH * percent / 100)


# ─────────────────────────────────────────────────────────────
#  check_color — Verifica a cor em um ponto percentual da barra
# ─────────────────────────────────────────────────────────────
#  region  → tupla (x, y, largura, altura) — coordenadas LÓGICAS (1x)
#  percent → posição dentro da barra a verificar (ex: 50 = metade)
#  color   → cor esperada quando a barra está preenchida
#
#  DIFERENÇA do life_mana.py:
#  Aqui NÃO multiplicamos por 2 nem por SCALE antes de passar
#  ao mss, porque o mss já espera coordenadas lógicas (1x) no macOS.
#  O pyautogui exigia 2x, o mss não.
def check_color(region, percent, color):
    res_percent = calc_width(percent)
    x = region[0] + res_percent   # coordenada lógica (1x) — não multiplica por SCALE
    y = region[1]                  # idem

    return pixel_matches_color(x, y, color, tolerance=10)


# ─────────────────────────────────────────────────────────────
#  manage_supplies — Aplica cura e mana com ordem de prioridade
# ─────────────────────────────────────────────────────────────
#  Lógica idêntica ao life_mana.py — só a engine de pixel mudou.
#
#  pg.press() mantido. Abaixo de cada chamada há a alternativa
#  pynput comentada — descomente para remover pyautogui.
def manage_supplies():
    if not check_color(constants.LIFE, 50, constants.LIFE_COLOR):
        print("Heath potion...")
        pg.press(constants.KEY_LIFE)
        # Alternativa pynput (descomente e comente o pg.press acima):
        # KEYBOARD.press(constants.KEY_LIFE); KEYBOARD.release(constants.KEY_LIFE)
    else:
        if not check_color(constants.LIFE, 80, constants.LIFE_COLOR):
            print("Exura...")
            pg.press(constants.KEY_EXURA)
            # Alternativa pynput:
            # KEYBOARD.press(constants.KEY_EXURA); KEYBOARD.release(constants.KEY_EXURA)

        if not check_color(constants.MANA, 40, constants.MANA_COLOR):
            print("Mana Potion")
            pg.press(constants.KEY_MANA)
            # Alternativa pynput:
            # KEYBOARD.press(constants.KEY_MANA); KEYBOARD.release(constants.KEY_MANA)


# ─────────────────────────────────────────────────────────────
#  supplies_loop — Loop contínuo que roda em thread separada
# ─────────────────────────────────────────────────────────────
#  Idêntico ao life_mana.py — sem alterações na lógica.
def supplies_loop(stop_event, interval=0.8):
    while not stop_event.is_set():
        manage_supplies()
        time.sleep(interval)


# ─────────────────────────────────────────────────────────────
#  NOTAS — Migração completa para remover pyautogui do projeto
# ─────────────────────────────────────────────────────────────
#
#  Além dos pg.press() acima, ainda é necessário migrar em main.py:
#
#  pixel_atk() → pg.pixelMatchesColor()
#    Troca por: pixel_matches_color() deste arquivo (sem multiplicar por 2)
#
#  check_battle() → pg.locateOnScreen()
#    Troca por:
#      region = {"left": BATTLE_REGION[0], "top": BATTLE_REGION[1],
#                "width": BATTLE_REGION[2], "height": BATTLE_REGION[3]}
#      haystack = cv2.cvtColor(np.array(sct.grab(region)), cv2.COLOR_BGRA2BGR)
#      needle   = cv2.imread('imgs/battle.png', cv2.IMREAD_COLOR)
#      result   = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
#      _, max_val, _, _ = cv2.minMaxLoc(result)
#      return max_val >= 0.85
#
#  go_flag() → pg.locateOnScreen() + pg.moveTo() + pg.click()
#    locate_template com mss + cv2 (igual acima) retorna centro lógico.
#    Para o clique, use pyobjc (macOS nativo):
#      pip install pyobjc-framework-Quartz
#
#      from Quartz import CGEventCreateMouseEvent, CGEventPost, CGPoint
#      from Quartz import kCGHIDEventTap, kCGEventLeftMouseDown, kCGEventLeftMouseUp
#      from Quartz import kCGMouseButtonLeft
#
#      def mouse_click(x, y):
#          point = CGPoint(x, y)
#          dn = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
#          up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp,   point, kCGMouseButtonLeft)
#          CGEventPost(kCGHIDEventTap, dn)
#          CGEventPost(kCGHIDEventTap, up)
