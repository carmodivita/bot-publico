# =============================================================
#  thread_bot.py — Controlador de threads do bot
# =============================================================
#  Define a classe ThreadController que centraliza todo o
#  gerenciamento de threads e eventos de controle do bot.
#
#  Separado do main.py para manter o código organizado:
#    main.py      → lógica de jogo (ataque, loot, navegação)
#    thread_bot.py → controle de execução (iniciar, parar, pausar)
#
#  O main.py importa esta classe e cria o objeto "bot":
#    bot = ThreadController(run_func=run)
# =============================================================

import threading   # biblioteca padrão do Python para criar e controlar threads
import mix_vida_mana as life_mana


# ─────────────────────────────────────────────────────────────
#  ThreadController — Classe que gerencia as threads do bot
# ─────────────────────────────────────────────────────────────
#  Agrupa em um único objeto todos os controles de execução:
#    - event_th    → sinal para PARAR o bot (ESC)
#    - pause_th    → sinal para PAUSAR o bot (CapsLock)
#    - th_run      → thread do loop principal de jogo
#    - th_supplies → thread de cura e mana
#
#  Métodos públicos:
#    bot.start()        → inicia as threads (pode ser chamado de novo após stop())
#    bot.stop()         → para tudo
#    bot.toggle_pause() → pausa ou retoma
#    bot.state()        → "parado" | "rodando" | "pausado" | "parando"
class ThreadController:

    # run_func → a função run() do main.py passada como parâmetro.
    # Por que parâmetro e não import? Se thread_bot importasse main.py
    # e main.py importa thread_bot, seria uma importação circular.
    def __init__(self, run_func):
        self.run_func = run_func

        # Evento de parada: .set() pelo stop(); os loops checam .is_set() e retornam.
        self.event_th = threading.Event()

        # Evento de pausa: começa SETADO → .wait() passa direto.
        # CapsLock → .clear() → .wait() TRAVA a th_run até o próximo .set().
        self.pause_th = threading.Event()
        self.pause_th.set()

        # As threads são criadas no start(): um threading.Thread só pode
        # receber .start() UMA vez, então cada execução ganha threads novas.
        # (Antes elas eram criadas aqui e apertar a tecla de iniciar duas vezes derrubava o bot.)
        self.th_run = None
        self.th_supplies = None

        # Lock para start/stop não rodarem ao mesmo tempo (GUI + hotkey global)
        self._lock = threading.Lock()

    def _alive(self):
        return any(t is not None and t.is_alive() for t in (self.th_run, self.th_supplies))

    def state(self):
        if not self._alive():
            return "parado"
        if self.event_th.is_set():
            return "parando"   # ESC já foi dado, mas a thread ainda está terminando um sleep
        if not self.pause_th.is_set():
            return "pausado"
        return "rodando"

    # ─────────────────────────────────────────────────────────
    #  start — Inicia (ou reinicia) as threads
    # ─────────────────────────────────────────────────────────
    #  Retorna True se iniciou, False se já estava rodando ou ainda parando.
    def start(self):
        with self._lock:
            if self._alive():
                # Se as threads antigas ainda estão vivas (mesmo depois do ESC,
                # podem estar no meio de um pg.sleep), NÃO limpamos o event_th:
                # senão a thread antiga "ressuscitaria" junto com a nova.
                print("Bot já está rodando (ou ainda encerrando) — aguarde.")
                return False

            self.event_th.clear()
            self.pause_th.set()

            # daemon=True → threads encerram junto com o programa principal
            self.th_run = threading.Thread(target=self.run_func, daemon=True, name="th_run")
            self.th_supplies = threading.Thread(
                target=life_mana.supplies_loop,
                args=(self.event_th, 0.8),
                daemon=True,
                name="th_supplies",
            )
            self.th_run.start()
            self.th_supplies.start()
            print("Bot started....")
            return True

    # ─────────────────────────────────────────────────────────
    #  stop — Para todas as threads
    # ─────────────────────────────────────────────────────────
    #  pause_th.set() é essencial: se o bot estiver pausado (travado em
    #  .wait()), event_th.set() sozinho não destravaria a thread.
    def stop(self):
        with self._lock:
            if not self._alive():
                return
            self.event_th.set()
            self.pause_th.set()
            print("Bot stopped")

    # ─────────────────────────────────────────────────────────
    #  toggle_pause — Alterna entre pausado e rodando
    # ─────────────────────────────────────────────────────────
    #  Só afeta a th_run; th_supplies continua curando enquanto pausado.
    def toggle_pause(self):
        if not self._alive() or self.event_th.is_set():
            return
        if self.pause_th.is_set():
            self.pause_th.clear()
            print("Pausing...")
        else:
            self.pause_th.set()
            print("Resuming...")
