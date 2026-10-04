# =============================================================
#  constants.py — Configurações globais do bot
# =============================================================
#  Todas as coordenadas, cores e teclas usadas no bot ficam aqui.
#  Centralizar neste arquivo facilita calibrar o bot sem precisar
#  alterar nenhuma lógica em main.py ou life_mana.py.
#
#  SISTEMA DE COORDENADAS 2x (HiDPI / Retina):
#  No macOS com tela Retina, cada pixel lógico equivale a 2 pixels físicos.
#  O pyautogui trabalha com pixels físicos, então a maioria das coordenadas
#  aqui já está multiplicada por 2. Veja SCALE em main.py para o tratamento.
# =============================================================

# Região do minimapa na tela (x, y, largura, altura) — valores 2x físicos.
# Usada em locateOnScreen() para limitar a busca das imagens de waypoint.
# Limitar a região reduz o tempo de busca pois não varre a tela inteira.
MAP_REGION = (2538, 122, 228, 226)  # Valores no 2X conf=0.8

# Região da lista de batalha na tela (x, y, largura, altura) — valores 2x físicos.
# Usada em check_battle() para detectar se há um inimigo na lista de batalha.
BATTLE_REGION = (2182, 118, 344, 414)  # Valores 2x conf=0.8

# Indica se o sistema é macOS com tela Retina (HiDPI).
# True  → SCALE = 2 em main.py → coordenadas retornadas por locateOnScreen
#         são divididas por 2 antes de passar para moveTo() e click().
# False → SCALE = 1 → coordenadas usadas diretamente.
#MAC = True #If MacOS return True to use HIGH_DPI 2x

#Attack Value
# Cores que indicam que o personagem está com um alvo selecionado/atacando.
# O pixel em (ATK_X, ATK_Y) assume essas cores quando há alvo ativo.
# Duas cores pois o tom pode variar conforme o estado do alvo.
RED_ATK = (234,51,35)    # vermelho — cor principal de ataque ativo
PNK_ATK = (239,135,132)  # rosa — variação da cor de ataque

# Posição do pixel que indica estado de ataque — já armazenado em 2x físico.
# Este pixel fica na barra de ataque/alvo do Tibia.
# Lido diretamente com pg.pixelMatchesColor() em pixel_atk() no main.py.
ATK_X = 1105*2  # = 2210 pixels físicos (1105 lógicos × 2)
ATK_Y = 73*2    # = 146  pixels físicos (73 lógicos × 2)

#Posição das Flags no centro do mini mapa, para ver se o player está na posição
# esperada e se já pode prosseguir para o próximo algo
flag_x = 1325
flag_y = 117
#Tentativas que o player tenta chegar ao waypoint antes de ir para o próximo
MAX_WAYPOINT_ATTEMPTS = 4

#LIFE_MANA VALUES
# Coordenadas antigas (comentadas) — mantidas para referência histórica.
#LIFE_POTION = (1331,345)
#MANA_POTION =(1317,358)
#START_LIFE = (1290,345)
#END_LIFE = (1376,345)


#PERCENT VALUES
# Regiões das barras de vida e mana no formato (x, y, largura, altura).
# ATENÇÃO: estas são coordenadas LÓGICAS (1x), não físicas (2x).
# A função check_color() em life_mana.py multiplica por 2 internamente.
# Não multiplique por 2 antes de passar para check_color().
LIFE = (1290,345,86,0)  # barra de vida — inicia em x=1290, y=345, largura=86px
MANA = (1290,360,86,0)  # barra de mana — inicia em x=1290, y=360, largura=86px

# Largura das barras em pixels lógicos (1x).
# Usada em calc_width() para calcular quantos pixels representam um percentual.
WIDTH = 86

# COLOR VALUES
# Cor que a barra de mana apresenta quando está preenchida naquele ponto.
# Se pixelMatchesColor() encontrar essa cor, a mana está acima do percentual verificado.
MANA_COLOR = (115,113,213)  # azul/roxo

# Cor que a barra de vida apresenta quando está preenchida naquele ponto.
LIFE_COLOR = (238,121,117)  # vermelho/rosa
#
#HOTKEYS
# Teclas enviadas via pg.press() para controlar o personagem no Tibia.
# Altere aqui se você reconfigurar os hotkeys dentro do jogo.
KEY_ATK = 't'    # atacar o alvo selecionado
KEY_LOOT = 'f'   # abrir / lootar cadáver próximo
KEY_EXURA = '1'  # feitiço de cura leve (Exura)
KEY_LIFE = '3'   # usar poção de vida
KEY_MANA = '4'   # usar poção de mana
KEY_ROPE = 'r'
KEY_SHOVEL = 'f9'  # pá (shovel) — usada nas flags com "shovel": true

# Teclas de CONTROLE do bot (nomes de pynput.keyboard.Key: "insert", "home",
# "end", "pause", "scroll_lock", "f12"...). Evite F1–F12: são hotkeys do Tibia.
START_KEY = "insert"     # iniciar
PAUSE_KEY = "caps_lock"  # pausar / retomar
STOP_KEY = "end"         # parar (Esc fica livre para fechar janelas no Tibia)

# Teclas do calibrar.py (o cancelar é a mesma STOP_KEY acima)
CAPTURE_KEY = "home"      # captura a posição/cor sob o mouse
SKIP_KEY = "page_down"    # pula o passo atual

#Posições do char(personagem) no jogo
#Clique escada
stairs_x = 561
stairs_y = 432
ROPE_X = 549
ROPE_Y = 432 #MUDAR
# Onde usar a pá (o buraco fica, em geral, no sqm ao lado do personagem)
SHOVEL_X = 549
SHOVEL_Y = 432

# Descarte de lixo (aba Lixo) — calibrados no grupo "Lixo"; None = desligado
BACKPACK_REGION = None   # (x, y, largura, altura) da mochila onde cai o loot
DROP_X = None            # ponto do chão onde o lixo é jogado
DROP_Y = None

# Pasta das imagens de template (flags do minimapa e battle.png).
# As imagens de imgs/ foram capturadas num Mac Retina (2x) e NÃO batem
# numa tela 1x do Windows, por isso o Windows usa uma pasta própria.
IMG_DIR = "imgs"

# =============================================================
#  WINDOWS — sobrescreve os valores acima com coords_windows.json
# =============================================================
#  No Windows não existe a mistura 1x/2x do Retina: o pyautogui e o mss
#  trabalham os dois em pixels físicos, então TODAS as coordenadas do
#  JSON estão na mesma escala e são usadas direto (SCALE = 1 em main.py).
#  O arquivo é gerado por calibrar.py — rode-o com o Tibia aberto.
import json as _json
import os as _os
import platform as _platform

if _platform.system() != "Darwin":
    IMG_DIR = "imgs_windows"
    _cfg_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "coords_windows.json")
    if _os.path.exists(_cfg_path):
        with open(_cfg_path, "r", encoding="utf-8") as _f:
            _cfg = _json.load(_f)
        for _k, _v in _cfg.items():
            globals()[_k] = tuple(_v) if isinstance(_v, list) else _v
    elif not _os.environ.get("BOT_CALIBRANDO"):  # o calibrar.py é quem cria o arquivo
        print("AVISO: coords_windows.json não encontrado — rode 'python calibrar.py' antes do bot.")

# Percentuais de cura (usados em mix_vida_mana.manage_supplies)
LIFE_POTION_PCT = 50  # vida abaixo disso → poção de vida
EXURA_PCT = 80        # vida abaixo disso → exura
MANA_PCT = 40         # mana abaixo disso → poção de mana

# Cura escolhida na aba Ajustes (só informativo: o bot usa a hotkey de cada uma)
CURA_VOCACAO = "knight"
CURA_EMERG_ITEM = "Health Potion"           # vida crítica  → KEY_LIFE
CURA_MAGIA_ITEM = "Wound Cleansing"         # vida baixa    → KEY_EXURA
CURA_MANA_ITEM = "Mana Potion"              # mana baixa    → KEY_MANA
CURA_EMERG_ON = True
CURA_MAGIA_ON = True
CURA_MANA_ON = True

# =============================================================
#  AJUSTES — ajustes.json (gravado pela aba "Ajustes" da interface)
# =============================================================
#  Vale em qualquer sistema e vem por último: hotkeys do jogo, teclas
#  de controle e percentuais de cura escolhidos na interface.
AJUSTES_KEYS = ("KEY_ATK", "KEY_LOOT", "KEY_EXURA", "KEY_LIFE", "KEY_MANA", "KEY_ROPE", "KEY_SHOVEL",
                "START_KEY", "PAUSE_KEY", "STOP_KEY", "CAPTURE_KEY", "SKIP_KEY",
                "LIFE_POTION_PCT", "EXURA_PCT", "MANA_PCT", "MAX_WAYPOINT_ATTEMPTS",
                "CURA_VOCACAO", "CURA_EMERG_ITEM", "CURA_MAGIA_ITEM", "CURA_MANA_ITEM",
                "CURA_EMERG_ON", "CURA_MAGIA_ON", "CURA_MANA_ON")
_aj_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ajustes.json")
if _os.path.exists(_aj_path):
    with open(_aj_path, "r", encoding="utf-8") as _f:
        for _k, _v in _json.load(_f).items():
            if _k in AJUSTES_KEYS:
                globals()[_k] = _v
