# CLAUDE.md — bot-26

> **Audience:** AI coding agents (Claude Code, OpenCode, Cursor, etc.)
> This file describes every architectural decision, coordinate system, known bug, and TODO in this project so that any agent can contribute safely without breaking the fragile pixel-based automation.

---

## What This Project Does

`bot-26` is a **macOS automation bot for the game Tibia**. It reads the screen with `pyautogui`, simulates keypresses, and navigates a fixed list of minimap waypoints while automatically attacking monsters, looting, and managing health/mana supplies. No game API or memory reading is involved — everything is done through pixel color comparison and image template matching.

---

## How to Run

```bash
cd code_agent/bot-26
python3 main.py
```

The script sleeps 2s on start-up, then waits for keyboard input. The game window must be open and focused for pixel coordinates to be valid.

### Runtime Controls

| Key         | Effect                                                        |
|-------------|---------------------------------------------------------------|
| `Backspace` | Starts the bot (`th_run` + `th_supplies` threads)            |
| `CapsLock`  | Toggles pause / resume (only `th_run` pauses; supplies keep running) |
| `ESC`       | Stops the bot completely and exits the listener              |

> `suppress=True` was tested but blocks all physical keypresses reaching Tibia.
> Currently running **without** `suppress=True` — CapsLock was chosen as pause key
> because it does not conflict with any Tibia hotkey or macOS window shortcut.

### Dependencies

```bash
pip install pyautogui pynput Pillow opencv-python mss numpy
```

| Package         | Role                                                  |
|-----------------|-------------------------------------------------------|
| `pyautogui`     | Screen capture, pixel reading, mouse/keyboard control |
| `pynput`        | Global keyboard listener (works outside focus)        |
| `Pillow`        | Required by pyautogui for image operations            |
| `opencv-python` | Required by pyautogui for `locateOnScreen` confidence |
| `mss`           | Fast 1×1 pixel capture (used in `mix_vida_mana.py`; ~20-30x faster than pyautogui per pixel check) |
| `numpy`         | Array pixel processing (used only in `_vida_mana.py` legacy engine; `mix_vida_mana.py` does NOT use numpy) |

---

## File Map

```
bot-26/
├── main.py          — Entry point: game functions, keyboard listener, bot instantiation
├── thread_bot.py    — ThreadController class: threads + control events
├── mix_vida_mana.py — ★ ACTIVE: Health/mana supply management (mss 1×1 pixel engine, ~20-30x faster)
├── life_mana.py     — Legacy health/mana module (pyautogui engine, slower — kept for reference)
├── _vida_mana.py    — Legacy mss+numpy pixel engine (superseded by mix_vida_mana.py; kept for reference)
├── _rand.py         — Human-behavior randomization (Bézier mouse curves, easing, deadline timing)
├── class_teach.py   — Educational reference only; NOT imported by any module
├── constants.py     — All screen coordinates, colors, and hotkey bindings
├── info.json        — Ordered waypoint list (flag_1.png → flag_20.png)
├── pixel.py         — Standalone debug tool: prints pixel color at ATK position
└── imgs/
    ├── battle.png          — Template to detect an active battle list entry
    ├── flag_1.png
    │   ...
    ├── flag_20.png         — Minimap waypoint flag screenshots (2x resolution)
    └── mapa.png            — Full minimap reference (currently unused in code)
```

---

## ⚠️ Critical: macOS HiDPI / Retina 2x Coordinate System

This is the single most important thing to understand before touching any coordinate.

`constants.MAC = True` activates 2x scaling mode. The display is a Retina screen where one **logical pixel** equals **two physical pixels**.

### Rules — read carefully before editing any coordinate

| Situation | Rule |
|-----------|------|
| `ATK_X`, `ATK_Y` in `constants.py` | Stored **pre-multiplied** (`1105*2`, `73*2`). Pass directly to `pg.pixelMatchesColor()` and `pg.pixel()`. Do **not** multiply again. |
| `MAP_REGION`, `BATTLE_REGION` in `constants.py` | Also stored at **2x values**. Pass directly to `locateOnScreen(region=...)`. Do **not** multiply again. |
| `LIFE`, `MANA` regions in `constants.py` | Stored at **1x logical coords**. `mix_vida_mana.py` passes them directly to mss (mss expects 1x). `life_mana.py` multiplies by 2 internally. Do **not** pre-multiply these. |
| `locateOnScreen` return value (center) | Is in **2x physical coordinates**. Divide by `SCALE` (= 2) before passing to `pg.moveTo()`. See `go_flag()` in `main.py`. |

**Golden rule:** every coordinate reaches `pyautogui` functions as a **2x physical pixel value** — but take care about *where* the multiplication happens to avoid double-multiplying.

---

## Architecture & Threading

```
main.py
  └── imports ThreadController from thread_bot.py
  └── defines game functions (go_flag, pixel_atk, atk_monster, run)
  └── bot = ThreadController(run_func=run)
  └── key_code → bot.start() / bot.stop() / bot.toggle_pause()
  └── Listener blocks main thread forever

thread_bot.py
  └── class ThreadController
        └── owns: event_th, pause_th (threading.Event)
        └── owns: th_run, th_supplies (threading.Thread)
        └── methods: start(), stop(), toggle_pause()
        └── imports mix_vida_mana as life_mana for th_supplies target
```

### The Three Threads

| Thread | Started by | Target function | Pauses with CapsLock? | Stops with ESC? |
|--------|-----------|-----------------|----------------------|----------------|
| **Main thread** | Script start | `listener.join()` | No | Yes (listener.stop()) |
| **`th_run`** | `bot.start()` | `run()` in main.py | **Yes** — via `bot.pause_th.wait()` | Yes — via `bot.event_th.is_set()` |
| **`th_supplies`** | `bot.start()` | `mix_vida_mana.supplies_loop()` | **No** — heals even when paused | Yes — via `event_th.is_set()` |

### Thread Control — inside `ThreadController`

```python
self.event_th = threading.Event()   # STOP signal  — .set() by stop(); loops check .is_set()
self.pause_th = threading.Event()   # PAUSE signal — starts SET; .clear() pauses th_run
```

**How pause works:**
- `pause_th` starts **set** (active) → `bot.pause_th.wait()` returns immediately → bot runs
- CapsLock → `pause_th.clear()` → `bot.pause_th.wait()` **blocks** the thread → bot freezes
- CapsLock again → `pause_th.set()` → `wait()` unblocks → bot resumes from where it stopped

**How stop works:**
- ESC → `event_th.set()` + `pause_th.set()`
- `pause_th.set()` is critical: if the bot is paused (stuck in `.wait()`), `event_th.set()` alone
  would not unblock it. `pause_th.set()` unblocks the wait first, then the loop checks
  `event_th.is_set()` and returns.

### Pattern every loop in `main.py` must follow

```python
def any_loop_function():
    while <condition>:
        bot.pause_th.wait()       # 1. block here if paused
        if bot.event_th.is_set(): # 2. exit if ESC was pressed
            return
        # ... actual work ...
```

---

## Game Loop Flow

```
Backspace pressed
  └── bot.start()
        ├── th_run.start()
        │     └── run()
        │           └── for each item in dados (info.json):
        │                 ├── bot.pause_th.wait()
        │                 ├── if bot.event_th.is_set() → return
        │                 ├── atk_monster()
        │                 │     └── while not check_battle():
        │                 │           ├── bot.pause_th.wait()
        │                 │           ├── if bot.event_th.is_set() → return
        │                 │           ├── pg.press(KEY_LOOT)
        │                 │           ├── pg.sleep(0.3)
        │                 │           ├── pg.press(KEY_ATK)
        │                 │           └── pixel_atk()
        │                 │                 └── while True:
        │                 │                       ├── bot.pause_th.wait()
        │                 │                       ├── if bot.event_th.is_set() → return
        │                 │                       └── pixelMatchesColor(ATK_X, ATK_Y)
        │                 │                             ├── match  → alive → sleep → break
        │                 │                             └── no match → dead → return False
        │                 └── go_flag(item["path"], wait=5)
        │                       └── locateOnScreen(flag_N.png, region=MAP_REGION)
        │                             ├── found → center/SCALE → moveTo() → click()
        │                             └── not found → print warning, return False
        │
        └── th_supplies.start()
              └── life_mana.supplies_loop(event_th, interval=0.8)
                    └── while not event_th.is_set():
                          ├── manage_supplies()   ← does NOT check pause_th
                          └── time.sleep(0.8)
```

---

## `thread_bot.py` — ThreadController

The class owns all threading state. `main.py` only interacts with it through methods.

| Method | What it does |
|--------|-------------|
| `__init__(run_func)` | Creates events and threads. Does **not** start them. `run_func` is passed in to avoid circular imports. |
| `start()` | Calls `.start()` on both threads. Can only be called **once** per instance. |
| `stop()` | Sets `event_th` (signals loops to exit) + sets `pause_th` (unblocks any `.wait()`). |
| `toggle_pause()` | Clears `pause_th` to pause, sets it to resume. Only affects threads that call `pause_th.wait()`. |

**Why `run_func` is passed as a parameter and not imported:**
`thread_bot.py` already imports `life_mana`. If it also imported `main`, and `main` imports `thread_bot`, that would be a **circular import** and Python would fail. Passing `run_func` as an argument breaks the cycle.

---

## `life_mana.py` — Supply Logic

### `check_color(region, percent, color)`

Checks whether the pixel at `percent`% along the bar `region` matches `color`.

```python
x = region[0] + int(WIDTH * percent / 100)
y = region[1]
pg.pixelMatchesColor(x * 2, y * 2, color, tolerance=10)
```

The `* 2` here is the only place `LIFE`/`MANA` coordinates are scaled.

### `manage_supplies()` — Priority Order

1. **Life < 50%** → `pg.press(KEY_LIFE)` — health potion, critical; skips spell check
2. **Life < 80%** (only if life ≥ 50%) → `pg.press(KEY_EXURA)` — healing spell
3. **Mana < 40%** (independent of life branch) → `pg.press(KEY_MANA)`

### `supplies_loop(stop_event, interval=0.8)`

Runs in `th_supplies`. Loops until `stop_event.is_set()`. Does **not** receive `pause_th` — healing continues even when the bot is paused via CapsLock.

---

## `constants.py` — Full Reference

```python
# Screen regions (2x physical pixels, used directly in locateOnScreen)
MAP_REGION    = (2538, 122, 228, 226)   # minimap bounding box
BATTLE_REGION = (2182, 118, 344, 414)   # battle list bounding box

# Attack-state indicator pixel (2x physical pixels, used directly in pyautogui)
ATK_X = 1105 * 2   # = 2210
ATK_Y = 73   * 2   # = 146

# Colors that indicate an active attack target (tolerance=20 in pixel_atk)
RED_ATK = (234,  51,  35)
PNK_ATK = (239, 135, 132)

# Life/Mana bar regions — stored in 1x logical coords; check_color() multiplies by 2
LIFE  = (1290, 345, 86, 0)
MANA  = (1290, 360, 86, 0)
WIDTH = 86

# Bar fill colors (matched with tolerance=10 in check_color)
LIFE_COLOR = (238, 121, 117)
MANA_COLOR = (115, 113, 213)

# Hotkeys (sent via pg.press())
KEY_ATK   = 't'   # attack current target
KEY_LOOT  = 'f'   # open/loot nearby corpse
KEY_EXURA = '1'   # light healing spell
KEY_LIFE  = '3'   # health potion
KEY_MANA  = '4'   # mana potion
```

---

## `pixel.py` — Debug Utility

Run standalone to print the live pixel color at the attack indicator position once per second. Use this to calibrate `RED_ATK` and `PNK_ATK` in `constants.py`.

```bash
python3 pixel.py
```

---

## `info.json` — Waypoint List

An ordered JSON array of 20 entries. The bot iterates top-to-bottom on every `run()` call.

```json
[
  { "flag": 1, "path": "imgs/flag_1.png" },
  ...
  { "flag": 20, "path": "imgs/flag_20.png" }
]
```

To change the route: edit this file and replace the corresponding screenshots in `imgs/`.

---

## `_rand.py` — Randomization Module

Provides human-behavior simulation to reduce bot detectability. **Not currently imported by `main.py`** — functions exist but are not wired into the main bot loop.

| Function | What it does |
|----------|-------------|
| `human_move(x, y, duration=None)` | Moves mouse along a quadratic Bézier curve with ±2px jitter. Expects **1x logical coords** (standard `pg.moveTo` format). Duration defaults to 0.1–0.3s random. |
| `human_click()` | Calls `pg.click()`, then 30% chance of a 0.1–0.3s post-click pause. |
| `human_press(key)` | Holds key for 30–120ms, then waits 20–150ms before returning. |
| `variable_sleep(base_time, variance_factor=0.3)` | Sleeps for `base ± 30%`. Returns the actual sleep time. |
| `aleatorio()` | 30% chance: moves mouse to a random point in (350–750, 300–600). |
| `occasional_human_behavior()` | Stub — currently `pass`. Placeholder for future random non-gameplay actions. |

### Integration TODOs

- Replace `pg.sleep(0.3)` calls in `atk_monster()` with `variable_sleep(0.3)`
- Call `aleatorio()` after each `go_flag()` in `run()` for natural post-click drift
- Replace `pg.press()` calls in `main.py` with `human_press()` for variable key timing

---

## `_vida_mana.py` — Fast MSS Pixel Engine

A drop-in replacement for `life_mana.py` that uses `mss` + `numpy` instead of `pyautogui.pixelMatchesColor()`. The logic (`manage_supplies`, `supplies_loop`) is identical — only the pixel-reading engine changes.

**Why faster:** `pyautogui.pixelMatchesColor()` makes a system call per pixel. `mss.grab()` captures a region in one shot and `numpy` processes it in memory.

**Not currently active.** `thread_bot.py` still imports `life_mana`. To switch engines, change one line in `thread_bot.py`:
```python
# from life_mana import supplies_loop   ← current
from _vida_mana import supplies_loop    # ← faster engine
```

### Critical coordinate difference vs `life_mana.py`

| | `life_mana.py` | `_vida_mana.py` |
|---|---|---|
| `check_color()` input | 1x logical → internally `* 2` before `pg.pixelMatchesColor` | 1x logical → passed directly to `mss.grab()` (no multiplication) |
| Pixel check in `pixel_atk()` | `ATK_X, ATK_Y` (2x pre-multiplied) | `ATK_X // 2, ATK_Y // 2` (mss expects 1x) |

The `mss` image returned on Retina IS 2x physical — the center is found dynamically with `shape[0]//2, shape[1]//2` to handle both 1x and 2x screens automatically.

### Migration path for `main.py` (when ready)

Replace `pg.locateOnScreen()` in `check_battle()` and `go_flag()` with `cv2.matchTemplate` over an `mss` screenshot:

```python
region = {"left": BATTLE_REGION[0]//2, "top": BATTLE_REGION[1]//2,
          "width": BATTLE_REGION[2]//2, "height": BATTLE_REGION[3]//2}
haystack = cv2.cvtColor(np.array(sct.grab(region)), cv2.COLOR_BGRA2BGR)
needle   = cv2.imread('imgs/battle.png', cv2.IMREAD_COLOR)
result   = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
_, max_val, _, _ = cv2.minMaxLoc(result)
return max_val >= 0.85
```

Note: `BATTLE_REGION` values must be divided by 2 because mss expects 1x logical coords.

---

## `class_teach.py` — Educational Reference

**Not imported by any file.** Read-only reference document written as annotated code.

Contains:
- Annotated duplicate of `ThreadController` explaining each attribute and method line by line
- Guide on adding a new thread (`th_walker` example)
- Guide on splitting into a sub-class (`WalkerController`)
- Explanation of the difference between attributes (`bot.event_th`) and methods (`bot.start()`)
- Suggestion to encapsulate internal events behind methods (`wait_if_paused()`, `should_stop()`) for cleaner `main.py` code

Safe to delete without affecting bot operation.

---

## Known Bugs

### `pixel_atk()` never returns `True` — `main.py`

`atk_monster()` calls `if pixel_atk(): break`. `pixel_atk()` can only return `None` or `False`, never `True`, so the `break` is unreachable and `"Time out...leaving atk..."` never prints.

- Dead path currently returns `False` → the `if pixel_atk():` check is never truthy
- Fix: decide what `True` should mean and add an explicit `return True` on that path

---

## Known Gaps / TODO

| Item | File | Notes |
|------|------|-------|
| `player_pos()` is a stub | `main.py` | Body is `pass`; not called anywhere |
| `mapa.png` is unused | `imgs/` | Full minimap reference exists but no code reads it |
| Single-pass waypoints | `main.py` | `run()` iterates `dados` once and exits; consider wrapping in `while not bot.event_th.is_set():` for continuous farming |
| `th_run` cannot restart | `thread_bot.py` | A `threading.Thread` can only be `.start()`ed once. If the bot finishes and you press Backspace again, it crashes. Needs a restart mechanism (recreate the thread). |
| No key-collision protection | `main.py` / `life_mana.py` | `th_run` and `th_supplies` both call `pg.press()` concurrently. No lock or cooldown exists yet. |
| `_rand.py` not integrated | `main.py` | Human-behavior functions exist but are not called; `pg.sleep()` calls not yet replaced with `variable_sleep()` and `aleatorio()` not called after `go_flag()`. |
| `_vida_mana.py` not active | `thread_bot.py` | Drop-in replacement ready; one import change switches the pixel engine from pyautogui to mss+numpy. |

---

## Scaling 2x — Guia para Funcionalidades Futuras

Este é o mapa completo do sistema de coordenadas. Consulte esta seção **sempre** que implementar algo novo que use posições na tela.

---

### Referência rápida — o que cada função do pyautogui espera

| Função pyautogui | Tipo de coordenada esperada | O que fazer |
|------------------|-----------------------------|-------------|
| `pg.moveTo(x, y)` | **1x lógica** | Se vier de `locateOnScreen`, dividir por `SCALE` |
| `pg.click(x, y)` | **1x lógica** | Mesma regra do `moveTo` |
| `pg.pixelMatchesColor(x, y, ...)` | **2x física** | Usar constantes pré-multiplicadas OU multiplicar por 2 |
| `pg.pixel(x, y)` | **2x física** | Mesma regra do `pixelMatchesColor` |
| `pg.locateOnScreen(region=(x,y,w,h))` | **2x física** | Usar regiões de `constants.py` diretamente |
| `pg.locateOnScreen()` — valor retornado | **2x física** | Dividir por `SCALE` antes de passar ao `moveTo` |
| `pg.press(key)` | Sem coordenada | Nenhuma conversão necessária |
| `pg.sleep(t)` | Sem coordenada | Nenhuma conversão necessária |

---

### O que já está implementado corretamente — NÃO mexa

| Arquivo | Linha(s) | O que faz | Por quê está correto |
|---------|----------|-----------|---------------------|
| `main.py` | 35 | `is_MAC = constants.MAC` | Lê a flag de plataforma |
| `main.py` | 39 | `SCALE = 2 if is_MAC else 1` | Define o divisor global |
| `main.py` `go_flag()` | 62–63 | `center_x / SCALE` e `center_y / SCALE` | `locateOnScreen` retorna 2x → divide antes do `moveTo` |
| `main.py` `pixel_atk()` | usa `ATK_X, ATK_Y` | Passa direto ao `pixelMatchesColor` | `ATK_X` e `ATK_Y` já são 2x em `constants.py` |
| `main.py` `check_battle()` | usa `BATTLE_REGION` | Passa direto ao `locateOnScreen` | `BATTLE_REGION` já é 2x em `constants.py` |
| `main.py` `go_flag()` | usa `MAP_REGION` | Passa direto ao `locateOnScreen` | `MAP_REGION` já é 2x em `constants.py` |
| `life_mana.py` `check_color()` | `x*2, y*2` | Multiplica antes do `pixelMatchesColor` | `LIFE` e `MANA` em `constants.py` são 1x lógicas → multiplica aqui |
| `constants.py` | `ATK_X = 1105*2` | Pré-multiplicado | Usado diretamente em `pixelMatchesColor`, não passa por SCALE |
| `constants.py` | `ATK_Y = 73*2` | Pré-multiplicado | Mesma razão do `ATK_X` |
| `constants.py` | `MAP_REGION`, `BATTLE_REGION` | Pré-multiplicados 2x | Usados diretamente em `locateOnScreen(region=)` |
| `constants.py` | `LIFE`, `MANA` | Guardados em 1x lógico | `check_color()` faz o `*2` internamente |

---

### Onde ESCALA precisará ser aplicada no futuro

Estas são as partes do código que ainda não existem ou são stubs. Ao implementar, siga as regras indicadas.

#### `player_pos()` — `main.py` (atualmente `pass`)

Quando implementada, esta função provavelmente vai:
- Usar `pg.locateOnScreen()` para encontrar o personagem no mapa → resultado em 2x → **dividir por `SCALE`** antes de qualquer `moveTo` ou `click`
- Ou ler um pixel de posição com `pg.pixel(x, y)` → **coordenadas devem ser 2x** → usar constante pré-multiplicada ou `valor * 2`

```
# Padrão correto para locateOnScreen → moveTo:
data = pg.locateOnScreen('imgs/player.png', region=ALGUMA_REGION)
if data:
    cx, cy = pg.center(data)
    pg.moveTo(cx / SCALE, cy / SCALE)   # ← obrigatório
```

#### Qualquer nova função que clique em elementos da UI

Se você implementar clique em inventário, spell bar, itens no chão, NPCs etc.:
- Se a posição vier de `locateOnScreen` → sempre **`/ SCALE`** antes do `moveTo`/`click`
- Se a posição for hardcoded (coordenada fixa) → guarde em `constants.py` como 1x lógico e aplique `/ SCALE` no uso, ou guarde como 2x e aplique `/ SCALE` ao passar para `moveTo`

#### Qualquer novo indicador de pixel em `pixel_atk()` ou função similar

Se você adicionar mais pixels para verificar (ex: cooldown de spell, estado de buff):
- Adicione a coordenada em `constants.py` **pré-multiplicada por 2** (igual `ATK_X = 1105*2`)
- Use direto em `pg.pixelMatchesColor()` sem modificação

#### Qualquer nova barra adicionada em `life_mana.py`

Se você adicionar novas barras (ex: stamina, experiência, soul points):
- Guarde a região em `constants.py` como **1x lógica** (igual `LIFE` e `MANA`)
- Passe para `check_color()` que já aplica o `*2` internamente
- **Não** multiplique por 2 antes de passar para `check_color()`

---

### O que NUNCA fazer — causaria dupla multiplicação

| O que não fazer | Por quê é erro |
|-----------------|----------------|
| `pg.moveTo(ATK_X / SCALE, ATK_Y / SCALE)` | `ATK_X` já é 2x. Dividir geraria coordenada errada. |
| `pg.pixelMatchesColor(ATK_X * 2, ATK_Y * 2, ...)` | `ATK_X` já é 2x. Multiplicar de novo seria 4x. |
| `pg.locateOnScreen(region=(MAP_REGION[0]*2, ...))` | `MAP_REGION` já é 2x. Multiplicar seria 4x. |
| Adicionar `*2` dentro de `check_color()` novamente | Já existe `x*2` na linha 44 de `life_mana.py`. |
| Guardar nova região de barra em `constants.py` como 2x | `check_color()` vai multiplicar por 2 → ficaria 4x. |
| Passar `LIFE` ou `MANA` diretamente para `pg.pixelMatchesColor()` sem `*2` | São 1x → pixel seria lido na posição errada. |

---

## Safe Editing Checklist

Before modifying any coordinate:

- [ ] Passed to `pg.pixelMatchesColor()` or `pg.pixel()`? → Must be **2x physical**
- [ ] Passed to `locateOnScreen(region=...)`? → Must be **2x physical**
- [ ] Passed to `pg.moveTo()` or `pg.click()`? → Must be **1x logical** (divide by `SCALE`)
- [ ] A `LIFE`/`MANA` region in `constants.py`? → Keep **1x logical**; `check_color()` scales it

Before adding a new loop or thread:

- [ ] Does it need to pause with CapsLock? → Add `bot.pause_th.wait()` at each iteration
- [ ] Does it need to stop with ESC? → Add `if bot.event_th.is_set(): return` after the wait
- [ ] Is it a new thread? → Add it to `ThreadController.__init__` and `start()`
- [ ] Does it call `pg.press()`? → Be aware of potential key collision with other threads
