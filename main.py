# =============================================================
#  main.py — Ponto de entrada do bot
# =============================================================
#  Contém toda a lógica de jogo (ataque, loot, navegação) e o
#  listener de teclado que controla o bot.
#
#  Fluxo de execução ao rodar "python3 main.py":
#    1. Importações e configurações iniciais
#    2. Definição das funções de jogo
#    3. Carregamento dos waypoints (info.json)
#    4. Definição de run() — loop principal do bot
#    5. Criação do objeto bot (ThreadController)
#    6. Definição do callback de teclado (key_code)
#    7. Listener inicia e trava a thread principal aqui
# =============================================================

import json
import constants      # coordenadas, cores e hotkeys do bot
import pyautogui as pg   # controle de tela: pixel, imagem, teclado e mouse
from pynput.keyboard import Listener   # escuta o teclado globalmente (independente do foco)
from pynput import keyboard            # acesso aos objetos de teclas especiais (Key.esc, etc.)
import time
import platform
#import threading      # usado indiretamente via ThreadController
#import life_mana      # módulo de cura/mana (importado aqui para referência)


# Importa a classe que gerencia threads e eventos de controle do bot
from thread_bot import ThreadController


# Desativa a exceção que pyautogui lançaria quando locateOnScreen()
# não encontra a imagem na tela — retorna None em vez de travar o programa.
pg.useImageNotFoundException(False)

# Lê a flag de macOS definida em constants.py
if platform.system() == "Darwin":
    is_MAC = True
else:
    is_MAC = False

# SCALE converte coordenadas de físico (2x) para lógico (1x).
# locateOnScreen() retorna posições em pixels físicos (2x no Retina).
# moveTo() e click() esperam pixels lógicos (1x), então dividimos por SCALE.
SCALE = 2 if is_MAC else 1

# ─────────────────────────────────────────────────────────────
#  go_flag — Navega até um waypoint clicando no minimapa
# ─────────────────────────────────────────────────────────────
#  path → caminho da imagem do flag (ex: "imgs/flag_1.png")
#  wait → segundos para aguardar após clicar (tempo de deslocamento)
#
#  Busca o flag na região do minimapa usando template matching.
#  Se encontrar, clica para mover o personagem até lá e aguarda.
#  Retorna True se o flag foi encontrado, False se não encontrou.
def go_flag(path, wait):
    # Busca a imagem do flag dentro da região do minimapa com 80% de confiança.
    # confidence=0.8 → aceita imagem levemente diferente (variação de render).
    # region=MAP_REGION → limita a busca ao minimapa, não varre a tela inteira.
    data = pg.locateOnScreen(path, confidence=0.8, region=constants.MAP_REGION)
    if data:
        # Get the flag center
        # locateOnScreen retorna um objeto Box com coordenadas em pixels físicos (2x).
        # pg.center() extrai o ponto central desse objeto como (x, y).
        center_x, center_y = pg.center(data)
        # Divide por SCALE para converter de pixels físicos (2x) para lógicos (1x).
        # moveTo() no macOS espera coordenadas lógicas.
        flag_x = center_x / SCALE
        flag_y = center_y / SCALE
        # Run the action
        pg.moveTo(flag_x, flag_y)  # move o mouse até o flag no minimapa
        pg.click()                # clica para enviar o personagem ao waypoint
        pg.sleep(wait)            # aguarda o deslocamento do personagem

        return True
    print(f"{path} not found")
    return False  # flag não encontrado no minimapa

# ─────────────────────────────────────────────────────────────
#  player_pos — Stub (não implementado)
# ─────────────────────────────────────────────────────────────
#  TODO: futuramente detectar a posição do personagem no mapa.
def player_pos(path, file):
    player_flag = pg.locateOnScreen(path, confidence=0.75, region=constants.MAP_REGION)
    if player_flag:
        center_x, center_y = pg.center(player_flag)
        player_x = center_x // SCALE
        player_y = center_y // SCALE
        print(f"Player position: (X:{player_x}, Y:{player_y})")

        if (constants.flag_x -3 ) <= player_x <= (constants.flag_x + 3)and (constants.flag_y - 3) <= player_y <= (constants.flag_y + 3):
            return True
        else:
            print(f"Player didn't arrive at {file}.")
            return False


# ─────────────────────────────────────────────────────────────
#  pixel_atk — Detecta estado de ataque via cor de pixel
# ─────────────────────────────────────────────────────────────
#  Monitora o pixel em (ATK_X, ATK_Y) para saber se o personagem
#  ainda está atacando um alvo ou se o monstro morreu.
#
#  Como funciona:
#    - Enquanto o monstro está vivo, o pixel tem a cor de ataque (RED_ATK ou PNK_ATK).
#    - Quando o monstro morre, o pixel perde essa cor.
#
#  Retorna False → monstro morreu (pixel perdeu a cor de ataque).
#  Retorna None  → (implícito) monstro ainda vivo ou ESC pressionado.
def pixel_atk():
    colors = [constants.RED_ATK,constants.PNK_ATK]  # cores que indicam ataque ativo
    tolerance = 20  # margem de tolerância na comparação RGB (0-255)
    start_time = time.time()

    while True:

        for color in colors:
            bot.pause_th.wait() # -- pausing the bot after home key press
            # Verifica se ESC foi pressionado antes de executar qualquer ação
            if bot.event_th.is_set():
                return  # encerra pixel_atk() se o bot foi parado
            # Compara o pixel de ataque com a cor esperada
            if pg.pixelMatchesColor(constants.ATK_X,constants.ATK_Y, color, tolerance=tolerance):
                # Pixel com cor de ataque encontrado → monstro ainda vivo
                print("killing monster...")
                pg.sleep(0.3)  # pausa breve antes de checar novamente
                break           # sai do for, mas continua o while externo
        else:
            # O bloco "else" do for executa apenas quando o loop termina SEM break.
            # Significa: nenhuma das cores de ataque foi encontrada → monstro morreu.
            print("Dead....")
            return False  # sinaliza ao chamador que o alvo foi eliminado

        if time.time() - start_time > 10:
            return True  # sinaliza ao chamador que o tempo de ataque expirou

# ─────────────────────────────────────────────────────────────
#  check_battle — Verifica se há inimigo na lista de batalha
# ─────────────────────────────────────────────────────────────
#  Busca a imagem battle.png na região da lista de batalha.
#  Retorna True se encontrar (há alvo ativo), False caso contrário.
#  Usada em atk_monster() como condição de saída do loop de ataque.
def check_battle():
    battle = pg.locateOnScreen('imgs/battle.png', confidence=0.85, region=constants.BATTLE_REGION)
    if battle:
        return True
    else:
        return False

# ─────────────────────────────────────────────────────────────
#  atk_monster — Loop principal de combate
# ─────────────────────────────────────────────────────────────
#  Continua atacando enquanto NÃO houver alvo na lista de batalha.
#  check_battle() retorna True quando um alvo está na lista → loop para.
#  Usa pixel_atk() para monitorar se o monstro atual foi morto.
def atk_monster():
    while not check_battle(): # retorna True or False, old version returned None
        print("Attacking")
        bot.pause_th.wait() # -- pausing the bot after home key press
        # Verifica evento de parada logo após o desbloqueio do wait
        if bot.event_th.is_set():
            return  # ESC pressionado → sai do loop de ataque
        pg.press(constants.KEY_LOOT) # loot — tenta lootar cadáver antes de atacar
        pg.sleep(0.2) # small delay — pausa para o jogo processar
        pg.press(constants.KEY_ATK) # shortcut to attack — pressiona tecla de ataque

        if pixel_atk(): # Se True, sai de pixel e volta atk_monster
            # TODO: pixel_atk() nunca retorna True (retorna False ou None).
            # Este bloco é inalcançável no estado atual do código.
            print("Time out...leaving atk...")
            break
        pg.press(constants.KEY_LOOT) # hotkey to loot — loota após o monstro morrer

# ─────────────────────────────────────────────────────────────
#  execute_actions — Executa ações extras baseadas nas chaves do waypoint
# ─────────────────────────────────────────────────────────────
#  Cada chave em item (ex: "stairs", "rope") é mapeada para uma função
#  neste dicionário. Isso evita uma cadeia de ifs no run().
#
#  Para adicionar uma nova ação:
#    1. Crie a função
#    2. Adicione ao dicionário ACTIONS com a chave correspondente do JSON
#    3. Adicione a(s) coordenada(s) em constants.py (se necessário)
#
def action_stairs():
    #sobe estava clicando no cantinho, assim não há como bloquear ficando em cima dela.
    pg.moveTo(constants.stairs_x, constants.stairs_y)
    pg.rightClick()
    pg.sleep(0.5)

def actions_rope():
    #Usa corda: pressiona Hotkey e clica no personagem-em cima do local
    pg.moveTo(constants.ROPE_X, constants.ROPE_Y)
    pg.sleep(0.2)
    pg.press(constants.KEY_ROPE)
    pg.click()
    pg.sleep(0.4)

#Mapeamento de chaves -> função
ACTIONS = {
    "stairs": action_stairs,
    "rope": actions_rope,
}

# ─────────────────────────────────────────────────────────────
#  navigate_to_waypoint — Vai até o waypoint e confirma chegada
# ─────────────────────────────────────────────────────────────
#  1. Tenta clicar no flag via go_flag()
#  2. Se o flag não aparece no minimapa, retorna False imediatamente
#     (não adianta ficar tentando)
#  3. Se o flag foi clicado, espera o personagem chegar.
#     Se monstros bloquearem o caminho, mata-os e tenta de novo
#     até o limite de tentativas.
def go_waypoint(path,file,wait,max_attempts):
    if not go_flag(path,wait):
        return False # flag nem está no minimapa -> próximo item

    # Flag foi clicado - agora confirma que o personagem chegou
    for _ in range(max_attempts):
        if player_pos(path,file):
            return True #chegou
        atk_monster()
        if not go_flag(path,wait):
            return False # flag não apareceu no minimapa, não adianta continuar
    return False

# ─────────────────────────────────────────────────────────────
#  Carregamento dos waypoints
# ─────────────────────────────────────────────────────────────
#  Lê info.json que contém a lista ordenada de flags (waypoints).
#  Cada entrada tem "flag" (número) e "path" (caminho da imagem).
#  A variável "dados" é usada em run() para navegar em sequência.
with open("info.json", "r") as f:
    dados = json.load(f)

# ─────────────────────────────────────────────────────────────
#  run — Loop principal do bot (executado por th_run)
# ─────────────────────────────────────────────────────────────
#  Itera pelos waypoints do info.json em ordem.
#  Para cada waypoint: ataca os monstros da área, depois navega ao próximo.
#
#  Esta função é passada para ThreadController como run_func
#  e executa dentro da thread th_run em paralelo com th_supplies.
#
#  Padrão obrigatório em cada iteração:
#    1. bot.pause_th.wait() → trava se CapsLock foi pressionado
#    2. if bot.event_th.is_set() → sai se ESC foi pressionado
def run():
    while not bot.event_th.is_set():
        for item in dados:
            bot.pause_th.wait()           # trava aqui se bot estiver pausado (CapsLock)
            if bot.event_th.is_set():     # verifica se ESC foi pressionado
                return
            atk_monster()                 # ataca todos os monstros na posição atual
            if bot.event_th.is_set():     # verifica novamente após o combate
                return                    # ESC durante combate → sai sem navegar

            #Busca a bandeira, tenta ir até ela nas tentativas maximas
            go_waypoint(item["path"], item["file"], item["wait"], constants.MAX_WAYPOINT_ATTEMPTS)

            #Executa todas as ações extras definidas no JSON
            for key, func in ACTIONS.items():
                if item.get(key):
                    func()



#Criaçao do bot
# Instancia o ThreadController passando run() como função da thread principal.
# Neste ponto os eventos e threads são criados mas NÃO iniciados.
# bot deve ser criado APÓS run() ser definida pois run() é passada como argumento.
# O bot só começa a rodar quando Backspace for pressionado (bot.start()).
bot = ThreadController(run_func=run)


# ─────────────────────────────────────────────────────────────
#  key_code — Callback do listener de teclado
# ─────────────────────────────────────────────────────────────
#  Chamada pelo pynput toda vez que qualquer tecla é pressionada.
#  Recebe o objeto "key" que representa a tecla pressionada.
#
#  Filtra para processar apenas teclas especiais (ESC, CapsLock, Backspace).
#  Teclas comuns como 'f', 't' pressionadas pelo bot via pg.press()
#  também chegam aqui — o isinstance() as descarta antes de qualquer lógica.
def key_code(key):
    # isinstance(key, keyboard.Key) retorna True apenas para teclas especiais.
    # Teclas comuns ('f', 't', '1', etc.) são instâncias de keyboard.KeyCode → ignoradas.
    # Sem este filtro, cada pg.press() do bot acionaria este callback desnecessariamente.
    if not isinstance(key, keyboard.Key):
        return
    print('key ->', key)  # loga no terminal para debug

    if key == keyboard.Key.esc:
        # ESC → para o bot completamente e encerra o listener
        bot.stop()         # seta event_th e pause_th → threads encerram
        listener.stop()    # para o Listener do pynput → listener.join() retorna → programa encerra

    if key == keyboard.Key.caps_lock:
        # CapsLock → alterna entre pausado e rodando
        # Apenas th_run pausa; th_supplies continua curando o personagem
        bot.toggle_pause()

    if key == keyboard.Key.backspace:
        # Backspace → inicia as threads do bot
        # th_run começa run() e th_supplies começa supplies_loop() em paralelo
        bot.start()

# ─────────────────────────────────────────────────────────────
#  Listener de teclado — trava a thread principal aqui
# ─────────────────────────────────────────────────────────────
#  Listener escuta o teclado globalmente (independente de qual janela está em foco).
#  on_press=key_code → chama key_code() a cada tecla pressionada.
#  "with ... as listener:" → inicia o listener e garante cleanup ao sair.
#  listener.join() → TRAVA a thread principal aqui indefinidamente,
#                    mantendo o programa vivo enquanto o listener estiver ativo.
#  O programa encerra quando bot.stop() chama listener.stop() via ESC.
with Listener(on_press=key_code) as listener:
    listener.join()
