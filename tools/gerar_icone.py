# =============================================================
#  tools/gerar_icone.py — Desenha o ícone do Huntix (assets/huntix.*)
# =============================================================
#  "H" neon dentro de um hexágono com marcas de mira, no tema da
#  interface (azul-marinho + ciano). Desenhado em 1024px e reduzido
#  com antialias para cada tamanho do .ico.
# =============================================================
import math
import os
from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024
CYAN = (0, 229, 255)
CYAN_SOFT = (0, 229, 255, 90)
BG_TOP = (14, 24, 44)
BG_BOT = (5, 8, 16)


def hexagono(cx, cy, r, rot=90):
    return [(cx + r * math.cos(math.radians(rot + 60 * i)), cy + r * math.sin(math.radians(rot + 60 * i)))
            for i in range(6)]


def desenhar():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # fundo: quadrado arredondado com degradê vertical
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        gd.line([(0, y), (S, y)], fill=tuple(int(BG_TOP[i] * (1 - t) + BG_BOT[i] * t) for i in range(3)) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([24, 24, S - 24, S - 24], radius=210, fill=255)
    img.paste(grad, (0, 0), mask)

    # camada neon (desenhada uma vez nítida e uma vez borrada para o brilho)
    neon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(neon)
    c = S // 2
    d.polygon(hexagono(c, c, 380), outline=CYAN, width=34)
    # marcas de mira nos 4 lados
    for x0, y0, x1, y1 in ((c, 60, c, 150), (c, S - 150, c, S - 60), (60, c, 150, c), (S - 150, c, S - 60, c)):
        d.line([(x0, y0), (x1, y1)], fill=CYAN, width=30)
    # "H"
    w, h, bar = 88, 400, 86
    lx, rx, top = c - 150, c + 150 - w, c - h // 2
    d.rounded_rectangle([lx, top, lx + w, top + h], radius=20, fill=CYAN)
    d.rounded_rectangle([rx, top, rx + w, top + h], radius=20, fill=CYAN)
    d.rounded_rectangle([lx + w - 10, c - bar // 2, rx + 10, c + bar // 2], radius=16, fill=CYAN)
    # ponto central da mira (recorte escuro no meio do traço)
    d.ellipse([c - 26, c - 26, c + 26, c + 26], fill=BG_BOT + (255,))

    glow = neon.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, neon)

    # borda sutil do quadrado
    ImageDraw.Draw(img).rounded_rectangle([24, 24, S - 24, S - 24], radius=210, outline=(22, 50, 80, 255), width=6)
    return img


if __name__ == "__main__":
    big = desenhar()
    os.makedirs(os.path.join(BASE, "assets"), exist_ok=True)
    big.resize((512, 512), Image.LANCZOS).save(os.path.join(BASE, "assets", "huntix_512.png"))
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(BASE, "assets", "huntix_256.png"))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(BASE, "assets", "huntix.ico"),
                                               sizes=[(s, s) for s in sizes])
    print("assets/huntix.ico, huntix_256.png, huntix_512.png")
