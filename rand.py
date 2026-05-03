# =============================================================
#  _rand.py — Módulo de Aleatoriedade e Comportamento Humano
# =============================================================
#  Este arquivo contém funções projetadas para simular ações
#  humanas, tornando os movimentos do mouse, cliques e pressionar
#  de teclas menos previsíveis para sistemas de detecção de bots.
#
#  Principais funcionalidades:
#    - Movimentação curva e variável do mouse (human_move)
#    - Cliques com variações de tempo (human_click)
#    - Digitação com delays aleatórios (human_press)
#    - Pausas variáveis (variable_sleep)
#    - Movimentos de exploração aleatórios (aleatorio)
# =============================================================

import random           # Para gerar valores aleatórios
import constants        # Acesso às configurações globais do bot
import time             # Controle de pausas e medição de tempo
import pyautogui as pg  # Controle de mouse e teclado
import math             # Cálculos matemáticos para trajetória curva

# Opcionais/Em desenvolvimento:
# import actions
# import hardware

# ─────────────────────────────────────────────────────────────
#  aleatorio — Movimentação exploratória aleatória
# ─────────────────────────────────────────────────────────────
#  Realiza um movimento aleatório do cursor para uma área do jogo.
#  Útil para simular o jogador olhando o cenário ou ajustando a câmera.
def aleatorio():
    """
    Depois de clicar na bandeira (waypoint), move aleatoriamente
    para uma posição entre as coordenadas X(350-750) e Y(300-600).
    """
    # 30% de chance de realizar o movimento para não ser repetitivo
    if random.random() < 0.3:
        random_x = random.randint(350, 750)
        random_y = random.randint(300, 600)

        # Realiza o movimento de forma humanizada
        human_move(random_x, random_y)


# ─────────────────────────────────────────────────────────────
#  human_move — Movimentação humanizada do mouse
# ─────────────────────────────────────────────────────────────
#  x, y     → Coordenadas de destino
#  duration → Tempo total do movimento (opcional)
def human_move(x, y, duration=None):
    """
    Move o cursor de forma natural usando curva de Bézier,
    ease-in-out espacial e timing preciso por deadline.
    """
    if duration is None:
        duration = random.uniform(0.1, 0.3)

    start_x, start_y = pg.position()

    # Número de passos proporcional à distância
    distance = math.sqrt((x - start_x)**2 + (y - start_y)**2)
    steps = max(int(distance / 60), 5)

    # Ponto de controle aleatório para a curva quadrática
    control_x = (start_x + x) / 2 + random.uniform(-30, 30)
    control_y = (start_y + y) / 2 + random.uniform(-30, 30)

    # Tempo alocado por passo
    step_duration = duration / steps
    start_time = time.perf_counter()

    for i in range(steps + 1):
        # Deadline absoluto deste passo (evita deriva acumulativa)
        deadline = start_time + i * step_duration

        t = i / steps

        # Ease-in-out espacial: acelera no início, desacelera no fim
        eased_t = t * t * (3 - 2 * t)

        # Curva quadrática de Bézier
        ix = (1 - eased_t)**2 * start_x + 2 * (1 - eased_t) * eased_t * control_x + eased_t**2 * x
        iy = (1 - eased_t)**2 * start_y + 2 * (1 - eased_t) * eased_t * control_y + eased_t**2 * y

        # Tremor de mão em todos os passos exceto o último
        if i != steps:
            ix += random.uniform(-2, 2)
            iy += random.uniform(-2, 2)

        pg.moveTo(ix, iy)

        # Espera só o tempo restante até o deadline
        if i < steps:
            remaining = deadline - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)

    # Correção final só se houver desvio real (>1px)
    cur_x, cur_y = pg.position()
    if abs(cur_x - x) > 1 or abs(cur_y - y) > 1:
        pg.moveTo(x, y)



# ─────────────────────────────────────────────────────────────
#  human_click — Clique de mouse humanizado
# ─────────────────────────────────────────────────────────────
def human_click():
    """
    Realiza um clique simulando a pressão humana, que não é instantânea.
    """
    pg.mouseDown()
    time.sleep(random.uniform(0.05, 0.15))  # hold time
    pg.mouseUp()
    # Simula a hesitação pós-clique que um humano pode ter
    # 30% de chance de aguardar um breve momento (0.1s a 0.3s)
    if random.random() < 0.3:
        time.sleep(random.uniform(0.1, 0.3))



# ─────────────────────────────────────────────────────────────
#  human_press — Pressionar de tecla humanizado
# ─────────────────────────────────────────────────────────────
#  key → Tecla a ser pressionada (ex: 'f1', 'a', 'enter')
def human_press(key):
    """
    Simula o pressionar de uma tecla com tempo de retenção variável.
    """
    # Pressiona a tecla
    pg.keyDown(key)

    # Mantém a tecla pressionada por um tempo aleatório (30ms a 120ms)
    time.sleep(random.uniform(0.03, 0.12))

    # Solta a tecla
    pg.keyUp(key)

    # Pequeno intervalo antes da próxima ação para não sobrecarregar o buffer
    time.sleep(random.uniform(0.02, 0.15))


# ─────────────────────────────────────────────────────────────
#  variable_sleep — Pausa com variação aleatória
# ─────────────────────────────────────────────────────────────
#  base_time       → Tempo de espera pretendido em segundos
#  variance_factor → Porcentagem de variação (0.3 = 30%)
def variable_sleep(base_time, variance_factor=0.3):
    """
    Dificulta a detecção de padrões temporais adicionando
    ruído aleatório ao tempo de sleep.
    """
    min_factor = max(0.01, 1 - variance_factor)
    max_factor = 1 + variance_factor

    # Calcula um tempo entre (base - 30%) e (base + 30%)
    sleep_time = random.uniform(base_time * min_factor, base_time * max_factor)
    time.sleep(sleep_time)

    return sleep_time


# ─────────────────────────────────────────────────────────────
#  occasional_human_behavior — Comportamentos extras aleatórios
# ─────────────────────────────────────────────────────────────
#  (Em desenvolvimento / Desativado)
#  Esta função pode ser chamada periodicamente para realizar
#  ações sem propósito de jogo, apenas para parecer humano.
def occasional_human_behavior():
    """
    Executa comportamentos aleatórios como olhar ao redor,
    abrir inventários ou checar status.
    """
    pass  # Atualmente desativado

    # Exemplo de lógica futura:
    """
    behaviors = [
        # Movimento leve de "ajuste" do mouse
        lambda: human_move(pg.position()[0] + random.randint(-50, 50),
                          pg.position()[1] + random.randint(-50, 50)),

        # Simular checar hotkeys ou status (ex: tecla 'u')
        lambda: hardware.hard_key('u'),

        # Mover o mouse como se estivesse acompanhando algo na tela
        lambda: (human_move(pg.position()[0] + random.randint(-100, 100),
                           pg.position()[1] + random.randint(-80, 80)),
                 variable_sleep(0.5))
    ]

    # Escolhe e executa uma ação da lista aleatoriamente
    random.choice(behaviors)()
    """
