import mss
import pyautogui as pg
import platform

#Detecta o sistema operaciona
is_mac = platform.system() == "Darwin"

if is_mac:
    # Coordenada LÓGICA (1x) — equivale a pg.pixel(1321*2, 356*2)
    x, y = 1321, 356 # MacOS
    #PyAutoGUI ( usa coordenada físicas 2x no Retina))
    print("pyautogui:", pg.pixel(x * 2, y * 2)) # to MAC
else:
    #Linux - 4k 150%
    x,y = 4884,814 # Linux
    print("PyAutoGUI: ", pg.pixel(x,y))

# mss — mesmo engine do mix_vida_mana.py (usa coordenadas lógicas 1x)
sct = mss.MSS()
monitor = {"top": y, "left": x, "width": 1, "height": 1}
screenshot = sct.grab(monitor)
b, g, r = screenshot.pixel(0, 0)
print("mss:      ", (r, g, b))
print("mss correto", (b,g,r))
