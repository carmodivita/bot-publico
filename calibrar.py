# =============================================================
#  calibrar.py — Mede as coordenadas e cores do bot na SUA tela
# =============================================================
#  Gera coords_windows.json (lido por constants.py) e as imagens de
#  template em imgs_windows/. Rode com o Tibia aberto e visível.
#
#  Uso:
#    python calibrar.py                 → coordenadas, cores e battle.png
#    python calibrar.py flags           → captura as 20 flags do minimapa
#    python calibrar.py flags 17        → recomeça as flags a partir da 17
#
#  Em cada passo: posicione o mouse no lugar pedido (dentro do Tibia)
#  e aperte Home. Page Down pula o passo (mantém o valor atual), End cancela.
#  As teclas ficam em constants.py (CAPTURE_KEY, SKIP_KEY, STOP_KEY) —
#  F1–F12 foram evitadas porque são hotkeys do Tibia.
# =============================================================

import json
import os
import sys
import threading

import pyautogui as pg  # importar o pyautogui já liga o modo DPI-aware no Windows

# Terminais antigos do Windows (cp1252) não têm "→" e "✗": troca por "?" em vez de travar
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
from pynput import keyboard

os.environ["BOT_CALIBRANDO"] = "1"  # silencia o aviso de "coords não encontradas"
import constants


def _nome(name):
    """Nome amigável da tecla (page_down → PageDown)."""
    return "".join(p.capitalize() for p in name.split("_"))


CAPTURE_KEY = getattr(keyboard.Key, constants.CAPTURE_KEY)
SKIP_KEY = getattr(keyboard.Key, constants.SKIP_KEY)
# Mesma tecla de parar do bot — o Esc fica livre para fechar janelas no Tibia
CANCEL_KEY = getattr(keyboard.Key, constants.STOP_KEY)
CAPTURE_NAME = _nome(constants.CAPTURE_KEY)
SKIP_NAME = _nome(constants.SKIP_KEY)
CANCEL_NAME = _nome(constants.STOP_KEY)

BASE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE, "coords_windows.json")
IMG_DIR = os.path.join(BASE, "imgs_windows")
FLAG_SIZE = 9  # lado (px) do recorte de cada flag; as do Mac eram 14px em 2x ≈ 7px em 1x

_key = None
_pressed = threading.Event()


def _on_press(key):
    global _key
    if key in (CAPTURE_KEY, SKIP_KEY, CANCEL_KEY):
        _key = key
        _pressed.set()


def esperar_tecla(msg):
    """Mostra a instrução e espera a tecla de capturar, pular ou cancelar.
    Retorna (x, y) do mouse, ou None se pulou."""
    print(f"\n→ {msg}\n   [{CAPTURE_NAME} captura | {SKIP_NAME} pula | {CANCEL_NAME} sai]")
    _pressed.clear()
    _pressed.wait()
    if _key == CANCEL_KEY:
        print("Cancelado. O que já foi capturado está salvo.")
        sys.exit(0)
    if _key == SKIP_KEY:
        print("   pulado")
        return None
    x, y = pg.position()
    print(f"   capturado: ({x}, {y})  cor={pg.pixel(x, y)}")
    return x, y


# ─────────────────────────────────────────────────────────────
#  Arquivo de coordenadas
# ─────────────────────────────────────────────────────────────
def carregar():
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ─────────────────────────────────────────────────────────────
#  Passos da calibração
# ─────────────────────────────────────────────────────────────
#  Cada passo captura UM ponto (posição do mouse). A função "aplicar"
#  recebe o cfg e todos os pontos já capturados e grava o que der.
#  Regiões e barras usam dois pontos: o 2º passo lê o ponto do 1º.
#  A interface (gui.py) usa esta mesma lista no assistente de calibração.
def _cor(p):
    return list(pg.pixel(*p))


def _ap_mapa(cfg, pts):
    a, b = pts.get("map_tl"), pts["map_br"]
    if not a:
        return False
    r = [a[0], a[1], b[0] - a[0], b[1] - a[1]]
    cfg["MAP_REGION"] = r
    # O personagem fica sempre no centro do minimapa — player_pos() compara com isso
    cfg["flag_x"], cfg["flag_y"] = r[0] + r[2] // 2, r[1] + r[3] // 2
    return True


def _ap_battle(cfg, pts):
    a, b = pts.get("battle_tl"), pts["battle_br"]
    if not a:
        return False
    r = [a[0], a[1], b[0] - a[0], b[1] - a[1]]
    cfg["BATTLE_REGION"] = r
    # battle.png é o print da lista vazia: o bot ataca enquanto ela NÃO estiver assim
    os.makedirs(IMG_DIR, exist_ok=True)
    pg.screenshot(region=tuple(r)).save(os.path.join(IMG_DIR, "battle.png"))
    return True


def _ap_atk(cfg, pts):
    p = pts["atk"]
    cfg["ATK_X"], cfg["ATK_Y"] = p
    cfg["RED_ATK"] = _cor(p)
    return True


def _ap_atk_pink(cfg, pts):
    cfg["PNK_ATK"] = _cor(pts["atk_pink"])
    return True


def _barra(cfg, pts, ini, fim, chave, chave_cor):
    a, b = pts.get(ini), pts[fim]
    if not a:
        return False
    y, largura = a[1], b[0] - a[0]
    cfg[chave] = [a[0], y, largura, 0]
    cfg[chave_cor] = _cor((a[0] + largura // 2, y))  # cor no meio da barra cheia
    return True


def _ap_life(cfg, pts):
    ok = _barra(cfg, pts, "life_l", "life_r", "LIFE", "LIFE_COLOR")
    if ok:
        cfg["WIDTH"] = cfg["LIFE"][2]
    return ok


def _ap_mana(cfg, pts):
    return _barra(cfg, pts, "mana_l", "mana_r", "MANA", "MANA_COLOR")


def _ap_stairs(cfg, pts):
    cfg["stairs_x"], cfg["stairs_y"] = pts["stairs"]
    return True


def _ap_rope(cfg, pts):
    cfg["ROPE_X"], cfg["ROPE_Y"] = pts["rope"]
    return True


def _ap_shovel(cfg, pts):
    cfg["SHOVEL_X"], cfg["SHOVEL_Y"] = pts["shovel"]
    return True


def _ap_bp(cfg, pts):
    a, b = pts.get("bp_tl"), pts["bp_br"]
    if not a:
        return False
    cfg["BACKPACK_REGION"] = [a[0], a[1], b[0] - a[0], b[1] - a[1]]
    return True


def _ap_drop(cfg, pts):
    cfg["DROP_X"], cfg["DROP_Y"] = pts["drop"]
    return True


STEPS = [
    {"id": "map_tl", "curto": "Canto superior esquerdo", "grupo": "Minimapa", "texto": "Canto SUPERIOR ESQUERDO do minimapa", "aplicar": None},
    {"id": "map_br", "curto": "Canto inferior direito", "grupo": "Minimapa", "texto": "Canto INFERIOR DIREITO do minimapa", "aplicar": _ap_mapa},
    {"id": "battle_tl", "curto": "Canto superior esquerdo", "grupo": "Lista de batalha",
     "texto": "Canto SUPERIOR ESQUERDO da lista de batalha (deixe-a VAZIA)", "aplicar": None},
    {"id": "battle_br", "curto": "Canto inferior direito", "grupo": "Lista de batalha",
     "texto": "Canto INFERIOR DIREITO da lista de batalha (ainda vazia)", "aplicar": _ap_battle},
    {"id": "atk", "curto": "Borda vermelha do alvo", "grupo": "Ataque",
     "texto": "Ataque um monstro e ponha o mouse na BORDA VERMELHA dele na lista de batalha", "aplicar": _ap_atk},
    {"id": "atk_pink", "curto": "Borda rosa do alvo", "grupo": "Ataque",
     "texto": "(Opcional) a mesma borda na variação ROSA, se aparecer — senão pule", "aplicar": _ap_atk_pink},
    {"id": "life_l", "curto": "Ponta esquerda da barra", "grupo": "Vida",
     "texto": "Com a vida CHEIA: ponta ESQUERDA da barra de vida, no meio da altura", "aplicar": None},
    {"id": "life_r", "curto": "Ponta direita da barra", "grupo": "Vida", "texto": "Ponta DIREITA da barra de vida (mesma altura)", "aplicar": _ap_life},
    {"id": "mana_l", "curto": "Ponta esquerda da barra", "grupo": "Mana",
     "texto": "Com a mana CHEIA: ponta ESQUERDA da barra de mana, no meio da altura", "aplicar": None},
    {"id": "mana_r", "curto": "Ponta direita da barra", "grupo": "Mana", "texto": "Ponta DIREITA da barra de mana (mesma altura)", "aplicar": _ap_mana},
    {"id": "stairs", "curto": "Clique na escada/buraco", "grupo": "Ações", "texto": "Ponto onde clicar na ESCADA/BURACO (flags com clique esquerdo ou direito)",
     "aplicar": _ap_stairs},
    {"id": "rope", "curto": "Uso da corda", "grupo": "Ações", "texto": "Ponto onde usar a CORDA (flags com \"rope\")", "aplicar": _ap_rope},
    {"id": "shovel", "curto": "Uso da pá", "grupo": "Ações", "texto": "Ponto onde usar a PÁ (flags com \"shovel\")", "aplicar": _ap_shovel},
    {"id": "bp_tl", "curto": "Canto superior esquerdo", "grupo": "Lixo",
     "texto": "Canto SUPERIOR ESQUERDO da mochila onde cai o loot", "aplicar": None},
    {"id": "bp_br", "curto": "Canto inferior direito", "grupo": "Lixo",
     "texto": "Canto INFERIOR DIREITO da mochila do loot", "aplicar": _ap_bp},
    {"id": "drop", "curto": "Onde jogar o lixo", "grupo": "Lixo",
     "texto": "Ponto do CHÃO onde jogar o lixo (ex.: o sqm do seu personagem)", "aplicar": _ap_drop},
]

# ─────────────────────────────────────────────────────────────
#  Itens de lixo (aba Lixo da interface)
# ─────────────────────────────────────────────────────────────
#  Cada item é um recorte do ícone dele na mochila, salvo em
#  imgs_windows/lixo/. O bot procura esses recortes na mochila do loot
#  e arrasta o que achar para o chão (main.drop_junk).
JUNK_DIR = os.path.join(IMG_DIR, "lixo")
JUNK_SIZE = 16  # recorte do MEIO do ícone (32px): evita a borda do slot e o número da pilha


def itens_lixo():
    """Caminhos dos recortes de lixo, em ordem de nome."""
    if not os.path.isdir(JUNK_DIR):
        return []
    return sorted(os.path.join(JUNK_DIR, f) for f in os.listdir(JUNK_DIR) if f.lower().endswith(".png"))


def salvar_lixo(p):
    """Recorta o ícone sob o mouse e salva como novo item de lixo. Retorna o caminho ou None."""
    meio = JUNK_SIZE // 2
    shot = pg.screenshot(region=(p[0] - meio, p[1] - meio, JUNK_SIZE, JUNK_SIZE))
    if _tudo_preto(shot):
        print(f"✗ Lixo: {AVISO_PRETO}")
        return None
    if all(hi - lo < 25 for lo, hi in shot.convert("RGB").getextrema()):
        print("✗ Lixo: o recorte saiu liso (uma cor só) — o mouse não estava sobre o item. Tente de novo.")
        return None
    os.makedirs(JUNK_DIR, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(JUNK_DIR, f"item_{n}.png")):
        n += 1
    caminho = os.path.join(JUNK_DIR, f"item_{n}.png")
    shot.save(caminho)
    return caminho


# ─────────────────────────────────────────────────────────────
#  Captura bloqueada (print preto)
# ─────────────────────────────────────────────────────────────
#  Alguns clientes escondem a janela de capturas de tela: o print sai
#  todo (0, 0, 0). Gravar isso como cor/template deixa o bot "cego"
#  sem nenhum erro aparente, então os passos que leem a tela recusam.
AVISO_PRETO = ("Captura de tela bloqueada: o print saiu todo preto. O cliente do jogo está "
               "escondendo a janela de capturas — o bot não consegue enxergar nada nele.")

# Passos que leem cor/imagem da tela (os demais só guardam a posição do mouse)
LE_TELA = {"battle_br", "atk", "atk_pink", "life_r", "mana_r"}


def _tudo_preto(img):
    return all(hi <= 3 for _, hi in img.convert("RGB").getextrema())


def captura_bloqueada(step, pts, p):
    """True se o passo lê a tela e o print da área dele saiu todo preto."""
    if step["id"] not in LE_TELA:
        return False
    a = pts.get("battle_tl") if step["id"] == "battle_br" else None
    if a and p[0] > a[0] and p[1] > a[1]:
        region = (a[0], a[1], p[0] - a[0], p[1] - a[1])
    else:
        region = (p[0] - 4, p[1] - 4, 9, 9)
    return _tudo_preto(pg.screenshot(region=region))


def aplicar_passo(step, cfg, pts, p):
    """Registra o ponto p do passo, aplica no cfg e salva. Retorna True se gravou algo."""
    pts[step["id"]] = p
    if step["aplicar"] and step["aplicar"](cfg, pts):
        salvar(cfg)
        return True
    return False


def salvar_flag(nome, p):
    """Recorta FLAG_SIZE×FLAG_SIZE centrado em p e salva em imgs_windows/<nome>.
    Recusa recortes de uma cor só (mouse fora da flag): uma imagem lisa
    "combinaria" com qualquer área da mesma cor e o bot clicaria no lugar errado.
    Retorna True se salvou."""
    meio = FLAG_SIZE // 2
    shot = pg.screenshot(region=(p[0] - meio, p[1] - meio, FLAG_SIZE, FLAG_SIZE))
    if _tudo_preto(shot):
        print(f"✗ {nome}: {AVISO_PRETO}")
        return False
    if all(hi - lo < 25 for lo, hi in shot.convert("RGB").getextrema()):
        print(f"✗ {nome}: o recorte saiu liso (uma cor só) — o mouse não estava sobre a flag. Tente de novo.")
        return False
    os.makedirs(IMG_DIR, exist_ok=True)
    shot.save(os.path.join(IMG_DIR, nome))
    return True


# ─────────────────────────────────────────────────────────────
#  Modo terminal
# ─────────────────────────────────────────────────────────────
def calibrar_coords():
    cfg, pts = carregar(), {}
    grupo = None
    for step in STEPS:
        if step["grupo"] != grupo:
            grupo = step["grupo"]
            print(f"\n=== {grupo} ===")
        p = esperar_tecla(step["texto"])
        while p and captura_bloqueada(step, pts, p):
            print(f"✗ {AVISO_PRETO}")
            p = esperar_tecla(step["texto"] + " (de novo)")
        if p and aplicar_passo(step, cfg, pts, p):
            print("   salvo")
    print(f"\nPronto! Salvo em {CFG_PATH}")
    print("Agora capture as flags com:  python calibrar.py flags")


def calibrar_flags(inicio=1):
    with open(os.path.join(BASE, "info.json"), "r", encoding="utf-8") as f:
        dados = json.load(f)
    print("Ande pela rota; quando cada flag aparecer no minimapa, ponha o mouse no CENTRO dela.")
    for item in dados:
        if item["file"] < inicio:
            continue
        nome = os.path.basename(item["path"])
        p = esperar_tecla(f"Flag {item['file']} ({nome}): mouse no centro da flag no minimapa")
        while p and not salvar_flag(nome, p):
            p = esperar_tecla(f"Flag {item['file']} de novo: mouse bem no centro da flag")
        if p:
            print(f"   imgs_windows/{nome} salvo")
    print("\nFlags concluídas.")


if __name__ == "__main__":
    listener = keyboard.Listener(on_press=_on_press)
    listener.start()
    if len(sys.argv) > 1 and sys.argv[1] == "flags":
        calibrar_flags(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    else:
        calibrar_coords()
