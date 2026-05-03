# =============================================================
#  life_mana.py — Gerenciamento de vida e mana
# =============================================================
#  Verifica as barras de vida e mana do personagem e pressiona
#  as teclas de cura/poção quando os valores estão baixos.
#
#  Roda em uma thread separada (th_supplies no ThreadController)
#  para funcionar em paralelo com o loop de ataque do bot.
#  Isso garante que a cura acontece mesmo durante combate intenso.
# =============================================================

import pyautogui as pg  # para pressionar teclas e ler pixels da tela
import constants         # coordenadas e cores das barras de vida/mana
import time              # para time.sleep() no intervalo do loop

# ─────────────────────────────────────────────────────────────
#  calc_width — Converte percentual em pixels dentro da barra
# ─────────────────────────────────────────────────────────────
#  Recebe um percentual (ex: 50 para 50%) e retorna quantos pixels
#  isso representa dentro da barra, baseado em constants.WIDTH.
#
#  Exemplo: calc_width(50) → int(86 * 50 / 100) → 43 pixels
#  Esses 43 pixels representam o ponto na metade da barra.
def calc_width(percent):
    return int(constants.WIDTH * percent / 100)

# ─────────────────────────────────────────────────────────────
#  check_color — Verifica a cor em um ponto percentual da barra
# ─────────────────────────────────────────────────────────────
#  region  → tupla (x, y, largura, altura) da barra — coordenadas 1x lógicas
#  percent → posição dentro da barra a verificar (ex: 50 = metade da barra)
#  color   → cor esperada quando a barra está preenchida até aquele ponto
#
#  Lógica: se o pixel naquele ponto TEM a cor esperada → barra está preenchida ali.
#          se o pixel NÃO tem a cor → aquela parte da barra está vazia → valor baixo.
#
#  Retorna True  → barra preenchida até o percentual indicado
#  Retorna False → barra abaixo do percentual (aquele ponto está vazio)
def check_color(region, percent, color):
    res_percent = calc_width(percent)    # posição em pixels dentro da barra
    x = region[0] + res_percent          # x absoluto na tela = início da barra + deslocamento
    y = region[1]                         # y fixo — topo da barra
    return pg.pixelMatchesColor(x*2, y*2, color, 10)
    # x*2 e y*2 → converte coordenadas lógicas (1x) para físicas (2x) — obrigatório no macOS Retina
    # tolerance=10 → aceita pequenas variações de cor causadas por render/compressão

# ─────────────────────────────────────────────────────────────
#  manage_supplies — Aplica cura e mana com ordem de prioridade
# ─────────────────────────────────────────────────────────────
#  Verifica vida e mana e pressiona as teclas de cura/poção.
#
#  Prioridade de verificação:
#    1. Vida < 50%  → poção de vida (emergência — ignora o resto)
#    2. Vida < 80%  → feitiço Exura (só executado se vida estiver entre 50-80%)
#    3. Mana < 40%  → poção de mana (verificado independente da vida)
def manage_supplies():
    # Verifica se a vida está abaixo de 50% (situação crítica)
    # check_color retorna False quando o pixel naquele ponto NÃO tem a cor da vida
    # → significa que aquela parte da barra está vazia → vida abaixo de 50%
    if not check_color(constants.LIFE, 50, constants.LIFE_COLOR):
        print("Heath potion...")
        pg.press(constants.KEY_LIFE)  # pressiona a tecla da poção de vida (KEY_LIFE = '3')
    else:
        # Vida está acima de 50% — verifica se precisa de cura moderada ou mana

        if not check_color(constants.LIFE, 80, constants.LIFE_COLOR):
            # Vida entre 50% e 80% → usa feitiço de cura leve
            print("Exura...")
            pg.press(constants.KEY_EXURA)  # pressiona tecla do feitiço (KEY_EXURA = '1')

        if not check_color(constants.MANA, 40, constants.MANA_COLOR):
            # Mana abaixo de 40% → usa poção de mana
            # Este check é independente do bloco de vida acima
            print("Mana Potion")
            pg.press(constants.KEY_MANA)  # pressiona tecla da poção de mana (KEY_MANA = '4')

# ─────────────────────────────────────────────────────────────
#  supplies_loop — Loop contínuo que roda em thread separada
# ─────────────────────────────────────────────────────────────
#  Esta função é o target da thread th_supplies no ThreadController.
#  Fica em loop chamando manage_supplies() a cada `interval` segundos.
#
#  stop_event → threading.Event() recebido do ThreadController (event_th).
#               Quando ESC é pressionado, event_th.set() é chamado e
#               o while encerra na próxima iteração.
#
#  interval   → tempo de espera entre cada verificação (padrão: 0.8 segundos).
#               Valor menor = cura mais rápida, mas usa mais CPU.
#               Valor maior = menos responsivo, mas mais leve.
#
#  IMPORTANTE: pause_th NÃO é passado para esta função propositalmente.
#  A cura continua mesmo quando o bot está pausado com CapsLock.
#  Parar de curar durante uma pausa manual seria perigoso para o personagem.
def supplies_loop(stop_event, interval=0.8):
    while not stop_event.is_set():  # continua enquanto ESC não for pressionado
        manage_supplies()            # verifica e aplica cura/mana se necessário
        time.sleep(interval)         # aguarda antes da próxima verificação
