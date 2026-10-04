# =============================================================
#  tools/gerar_icones_ui.py — Ícones neon da interface (assets/ui/*.png)
# =============================================================
#  Desenhados em traço, no estilo do logo do Huntix, em 192px e
#  reduzidos com antialias (a interface usa 22–28px).
#  Rode de novo para regenerar:  python tools/gerar_icones_ui.py
# =============================================================
import math
import os
from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "assets", "ui")
S = 192
W = 14  # espessura do traço

CYAN = (0, 229, 255)
PINK = (255, 61, 129)
VIOLET = (139, 92, 255)
MINT = (0, 255, 163)
AMBER = (255, 181, 71)
RED = (255, 77, 109)


def canvas():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def linha(d, pts, cor, w=W):
    d.line(pts, fill=cor, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=cor)


def finalizar(img):
    glow = img.filter(ImageFilter.GaussianBlur(7))
    out = Image.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 0)), glow)
    return Image.alpha_composite(out, img)


# ── desenhos ──────────────────────────────────────────────────
def atacar(c=CYAN):  # espada
    img, d = canvas()
    linha(d, [(48, 144), (150, 42)], c)
    d.polygon([(150, 42), (162, 30), (158, 50)], fill=c)
    linha(d, [(52, 112), (80, 140)], c)            # guarda
    linha(d, [(48, 144), (30, 162)], c, W + 4)     # cabo
    return img


def lootear(c=AMBER):  # bolsa com moeda
    img, d = canvas()
    d.rounded_rectangle([40, 70, 152, 162], radius=30, outline=c, width=W)
    linha(d, [(70, 70), (82, 40), (110, 40), (122, 70)], c)
    d.ellipse([78, 98, 114, 134], outline=c, width=W - 4)
    return img


def corda(c=AMBER):  # corda enrolada com gancho
    img, d = canvas()
    for r in (62, 42, 22):
        d.ellipse([96 - r, 112 - r, 96 + r, 112 + r], outline=c, width=W - 4)
    linha(d, [(150, 70), (150, 30), (120, 30)], c)
    return img


def coracao(c=PINK):
    img, d = canvas()
    pts = []
    for i in range(0, 361, 4):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((96 + x * 4.6, 92 - y * 4.6))
    d.line(pts + [pts[0]], fill=c, width=W, joint="curve")
    linha(d, [(70, 92), (88, 92), (98, 74), (110, 112), (120, 92), (128, 92)], c, W - 6)  # pulso
    return img


def magia(c=PINK):  # cruz de cura com brilho
    img, d = canvas()
    d.rounded_rectangle([78, 36, 114, 156], radius=12, outline=c, width=W - 2)
    d.rounded_rectangle([36, 78, 156, 114], radius=12, outline=c, width=W - 2)
    d.rectangle([84, 84, 108, 108], fill=(0, 0, 0, 0))
    for x, y in ((152, 40), (40, 152)):
        linha(d, [(x - 12, y), (x + 12, y)], c, 8)
        linha(d, [(x, y - 12), (x, y + 12)], c, 8)
    return img


def mana(c=VIOLET):  # gota
    img, d = canvas()
    d.line([(96, 28), (52, 104)], fill=c, width=W)
    d.line([(96, 28), (140, 104)], fill=c, width=W)
    d.arc([44, 64, 148, 168], start=-20, end=200, fill=c, width=W)
    linha(d, [(74, 126), (84, 146)], c, 8)
    return img


def tecla(c=CYAN):  # tecla de teclado
    img, d = canvas()
    d.rounded_rectangle([30, 46, 162, 146], radius=22, outline=c, width=W - 2)
    for x in (62, 96, 130):
        d.rounded_rectangle([x - 12, 72, x + 12, 92], radius=5, fill=c)
    d.rounded_rectangle([58, 108, 134, 122], radius=5, fill=c)
    return img


def play(c=MINT):
    img, d = canvas()
    d.polygon([(64, 40), (64, 152), (156, 96)], outline=c, width=W)
    return img


def pausa(c=AMBER):
    img, d = canvas()
    d.rounded_rectangle([54, 44, 84, 148], radius=8, outline=c, width=W - 2)
    d.rounded_rectangle([108, 44, 138, 148], radius=8, outline=c, width=W - 2)
    return img


def parar(c=RED):
    img, d = canvas()
    d.rounded_rectangle([48, 48, 144, 144], radius=18, outline=c, width=W)
    return img


def mira(c=CYAN):
    img, d = canvas()
    d.ellipse([46, 46, 146, 146], outline=c, width=W - 2)
    for a, b in (((96, 24), (96, 64)), ((96, 128), (96, 168)), ((24, 96), (64, 96)), ((128, 96), (168, 96))):
        linha(d, [a, b], c, W - 2)
    d.ellipse([88, 88, 104, 104], fill=c)
    return img


def pular(c=CYAN):
    img, d = canvas()
    d.polygon([(40, 48), (40, 144), (104, 96)], outline=c, width=W - 2)
    d.polygon([(96, 48), (96, 144), (160, 96)], outline=c, width=W - 2)
    return img


def repetir(c=CYAN):
    img, d = canvas()
    d.arc([40, 40, 152, 152], start=30, end=320, fill=c, width=W)
    d.polygon([(150, 52), (160, 96), (118, 84)], fill=c)
    return img


def escudo(c=CYAN):  # knight
    img, d = canvas()
    d.line([(96, 28), (158, 50), (150, 112), (96, 164), (42, 112), (34, 50), (96, 28)],
           fill=c, width=W, joint="curve")
    linha(d, [(96, 56), (96, 132)], c, W - 4)
    return img


def arco(c=CYAN):  # paladin
    img, d = canvas()
    d.arc([10, 28, 130, 164], start=-70, end=70, fill=c, width=W)
    linha(d, [(90, 38), (90, 154)], c, 6)
    linha(d, [(36, 96), (168, 96)], c, W - 4)
    d.polygon([(168, 96), (146, 82), (146, 110)], fill=c)
    return img


def folha(c=CYAN):  # druid
    # folha = elipse com nervura central, desenhada em pé e girada 45°
    img, d = canvas()
    d.ellipse([60, 22, 132, 150], outline=c, width=W)
    linha(d, [(96, 40), (96, 176)], c, W - 4)
    linha(d, [(96, 80), (78, 64)], c, 6)
    linha(d, [(96, 108), (114, 92)], c, 6)
    return img.rotate(-40, resample=Image.BICUBIC, center=(96, 96))


def chama(c=CYAN):  # sorcerer
    img, d = canvas()
    d.line([(96, 24), (126, 70), (146, 104), (138, 144), (96, 168), (54, 144), (46, 104), (66, 70), (96, 24)],
           fill=c, width=W, joint="curve")
    d.line([(96, 92), (112, 120), (96, 146), (80, 120), (96, 92)], fill=c, width=W - 6, joint="curve")
    return img


def pa(c=AMBER):  # shovel
    img, d = canvas()
    linha(d, [(60, 132), (148, 44)], c)                       # cabo
    linha(d, [(136, 32), (160, 56)], c, W - 2)                 # pegador
    d.polygon([(44, 120), (72, 148), (52, 172), (24, 168), (20, 144)], outline=c, width=W - 2)  # lâmina
    return img


def punho(c=CYAN):  # monk
    img, d = canvas()
    for x in (40, 68, 96):                                                     # nós dos 4 dedos (frente)
        d.rounded_rectangle([x, 44, x + 30, 98], radius=14, outline=c, width=W - 4)
    d.rounded_rectangle([124, 52, 152, 98], radius=13, outline=c, width=W - 4)
    d.rounded_rectangle([36, 92, 156, 160], radius=24, outline=c, width=W - 2)  # palma
    linha(d, [(58, 120), (118, 120)], c, W - 4)                                # polegar dobrado
    for y in (60, 96, 132):
        linha(d, [(166, y), (184, y)], c, 7)                                   # traços de impacto
    return img


def casa(c=CYAN):  # painel
    img, d = canvas()
    d.line([(28, 96), (96, 36), (164, 96)], fill=c, width=W, joint="curve")
    d.line([(52, 84), (52, 160), (140, 160), (140, 84)], fill=c, width=W, joint="curve")
    d.rounded_rectangle([82, 116, 110, 160], radius=6, outline=c, width=W - 4)
    return img


def bandeira(c=CYAN):  # rota / waypoint
    img, d = canvas()
    linha(d, [(52, 30), (52, 168)], c)
    d.polygon([(52, 36), (152, 56), (112, 80), (152, 104), (52, 112)], outline=c, width=W - 2)
    return img


def engrenagem(c=CYAN):  # ajustes
    img, d = canvas()
    for i in range(8):
        a = math.radians(i * 45)
        x, y = 96 + 62 * math.cos(a), 96 + 62 * math.sin(a)
        linha(d, [(96 + 40 * math.cos(a), 96 + 40 * math.sin(a)), (x, y)], c, W + 6)
    d.ellipse([46, 46, 146, 146], outline=c, width=W)
    d.ellipse([78, 78, 114, 114], outline=c, width=W - 4)
    return img


def ajuda(c=CYAN):
    img, d = canvas()
    d.ellipse([28, 28, 164, 164], outline=c, width=W - 2)
    d.arc([68, 50, 124, 106], start=180, end=70, fill=c, width=W - 2)
    linha(d, [(116, 98), (96, 112), (96, 124)], c, W - 2)
    d.ellipse([88, 138, 104, 154], fill=c)
    return img


def livro(c=CYAN):  # guia
    img, d = canvas()
    d.line([(96, 52), (96, 160)], fill=c, width=W - 4)
    d.line([(96, 52), (60, 40), (28, 46), (28, 150), (60, 144), (96, 160)], fill=c, width=W - 2, joint="curve")
    d.line([(96, 52), (132, 40), (164, 46), (164, 150), (132, 144), (96, 160)], fill=c, width=W - 2, joint="curve")
    return img


def personagem(c=CYAN):
    img, d = canvas()
    d.ellipse([66, 28, 126, 88], outline=c, width=W - 2)
    d.arc([36, 100, 156, 220], start=180, end=360, fill=c, width=W - 2)
    linha(d, [(36, 160), (156, 160)], c, W - 2)
    return img


def relogio(c=CYAN):
    img, d = canvas()
    d.ellipse([30, 30, 162, 162], outline=c, width=W - 2)
    linha(d, [(96, 60), (96, 98), (124, 116)], c, W - 2)
    return img


def grafico(c=CYAN):
    img, d = canvas()
    linha(d, [(32, 36), (32, 160), (164, 160)], c, W - 4)
    linha(d, [(52, 132), (86, 96), (114, 116), (156, 60)], c, W - 2)
    d.polygon([(156, 60), (134, 60), (156, 82)], fill=c)
    return img


def caveira(c=CYAN):  # abates
    img, d = canvas()
    d.chord([40, 30, 152, 140], start=150, end=30, outline=c, width=W - 2)
    d.rounded_rectangle([64, 112, 128, 160], radius=10, outline=c, width=W - 2)
    d.ellipse([62, 76, 88, 102], fill=c)
    d.ellipse([104, 76, 130, 102], fill=c)
    for x in (84, 108):
        linha(d, [(x, 136), (x, 158)], c, 6)
    return img


def terminal(c=CYAN):  # log
    img, d = canvas()
    d.rounded_rectangle([24, 40, 168, 152], radius=16, outline=c, width=W - 4)
    linha(d, [(52, 76), (76, 96), (52, 116)], c, W - 4)
    linha(d, [(92, 120), (132, 120)], c, W - 4)
    return img


def mapa(c=CYAN):  # minimapa
    img, d = canvas()
    d.line([(28, 52), (72, 36), (120, 52), (164, 36), (164, 140), (120, 156), (72, 140), (28, 156), (28, 52)],
           fill=c, width=W - 2, joint="curve")
    linha(d, [(72, 36), (72, 140)], c, 6)
    linha(d, [(120, 52), (120, 156)], c, 6)
    return img


def batalha(c=CYAN):  # lista de batalha
    img, d = canvas()
    for y in (52, 96, 140):
        d.rounded_rectangle([28, y - 14, 56, y + 14], radius=6, outline=c, width=8)
        linha(d, [(72, y - 6), (164, y - 6)], c, 8)
        linha(d, [(72, y + 8), (132, y + 8)], c, 6)
    return img


def lampada(c=AMBER):  # dica
    img, d = canvas()
    d.chord([46, 22, 146, 122], start=140, end=40, outline=c, width=W - 2)
    d.line([(62, 104), (74, 132), (118, 132), (130, 104)], fill=c, width=W - 2, joint="curve")
    linha(d, [(78, 152), (114, 152)], c, W - 4)
    linha(d, [(86, 170), (106, 170)], c, W - 4)
    return img


def mouse(c=CYAN):
    img, d = canvas()
    d.rounded_rectangle([52, 24, 140, 168], radius=44, outline=c, width=W - 2)
    linha(d, [(96, 30), (96, 78)], c, 8)
    linha(d, [(56, 78), (136, 78)], c, 8)
    return img


ICONES = {
    "pa": pa, "monk": punho, "painel": casa, "rota": bandeira, "ajustes": engrenagem, "ajuda": ajuda,
    "livro": livro, "personagem": personagem, "relogio": relogio, "grafico": grafico, "caveira": caveira,
    "log": terminal, "mapa": mapa, "batalha": batalha, "dica": lampada, "mouse": mouse,
    "atacar": atacar, "lootear": lootear, "corda": corda, "emergencia": coracao, "magia": magia,
    "mana": mana, "tecla": tecla, "iniciar": play, "pausar": pausa, "parar": parar, "capturar": mira,
    "pular": pular, "tentativas": repetir, "knight": escudo, "paladin": arco, "druid": folha,
    "sorcerer": chama,
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ESCURO = (0, 20, 26)  # para botões de fundo colorido (ciano/verde): sem brilho
    for nome, fn in ICONES.items():
        finalizar(fn()).resize((64, 64), Image.LANCZOS).save(os.path.join(OUT, f"{nome}.png"))
        fn(c=ESCURO).resize((64, 64), Image.LANCZOS).save(os.path.join(OUT, f"{nome}_dark.png"))
    print(f"{len(ICONES)} ícones (+ versão escura) em assets/ui/")
