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
#import life_mana   # módulo de cura/mana — usado como target da thread th_supplies
import mix_vida_mana as life_mana
# ─────────────────────────────────────────────────────────────
#  ThreadController — Classe que gerencia as threads do bot
# ─────────────────────────────────────────────────────────────
#  Agrupa em um único objeto todos os controles de execução:
#    - event_th  → sinal para PARAR o bot (ESC)
#    - pause_th  → sinal para PAUSAR o bot (CapsLock)
#    - th_run    → thread do loop principal de jogo
#    - th_supplies → thread de cura e mana
#
#  Métodos públicos acessados pelo main.py:
#    bot.start()        → inicia as threads
#    bot.stop()         → para tudo
#    bot.toggle_pause() → pausa ou retoma
class ThreadController:

    # ─────────────────────────────────────────────────────────
    #  __init__ — Construtor da classe
    # ─────────────────────────────────────────────────────────
    #  Executado automaticamente quando bot = ThreadController(run_func=run).
    #  Cria os eventos e as threads, mas NÃO as inicia ainda.
    #  As threads só iniciam quando bot.start() for chamado.
    #
    #  run_func → a função run() do main.py passada como parâmetro.
    #  Por que parâmetro e não import? Se thread_bot importasse main.py
    #  e main.py importa thread_bot, seria uma importação circular e
    #  o Python falharia ao iniciar. Passar como argumento evita isso.
    def __init__(self, run_func):

        # ── Evento de parada ──────────────────────────────────
        # threading.Event() cria um sinal binário que pode ser:
        #   .set()    → ativa o sinal (True)
        #   .clear()  → desativa (False)
        #   .is_set() → retorna o estado atual (True ou False)
        #   .wait()   → TRAVA a thread até o sinal ficar ativo

        # Começa NÃO setado (False) → bot pode rodar normalmente.
        # Quando ESC é pressionado → stop() chama .set() → True.
        # Todos os loops em main.py checam .is_set() e retornam.
        self.event_th = threading.Event()

        # ── Evento de pausa ───────────────────────────────────
        # Começa SETADO (True) → .wait() passa direto → bot não está pausado.
        # CapsLock → toggle_pause() chama .clear() → .wait() TRAVA as threads.
        # CapsLock de novo → toggle_pause() chama .set() → .wait() LIBERA.
        self.pause_th = threading.Event()
        self.pause_th.set()  # inicia ativo para o bot não começar pausado

        # ── Thread principal do jogo ──────────────────────────
        # Executa run() do main.py: percorre waypoints, ataca e loota.
        # Respeita pause_th (pausa com CapsLock) via bot.pause_th.wait() em main.py.
        # daemon=True → morre junto com o programa principal automaticamente.
        # threading.Thread() CRIA mas não inicia — .start() faz isso.
        self.th_run = threading.Thread(target=run_func, daemon=True)

        # ── Thread de suprimentos ─────────────────────────────
        # Executa supplies_loop() de life_mana.py: verifica e aplica cura/mana.
        # args=(self.event_th, 0.8) → passa event_th como stop_event e 0.8s de intervalo.
        # NÃO passa pause_th propositalmente → cura continua mesmo com bot pausado.
        self.th_supplies = threading.Thread(
            target=life_mana.supplies_loop,
            args=(self.event_th, 0.8),
            daemon=True
        )

    #metodos da classes(funcoes)

    # ─────────────────────────────────────────────────────────
    #  start — Inicia as threads do bot
    # ─────────────────────────────────────────────────────────
    #  Chamado quando Backspace é pressionado via key_code() em main.py.
    #  .start() faz cada thread começar a executar sua função target= em paralelo.
    #  ATENÇÃO: .start() só pode ser chamado UMA VEZ por thread.
    #  Pressionar Backspace novamente após o bot terminar causará erro.
    def start(self):
        self.th_run.start()       # th_run começa a executar run() em paralelo
        self.th_supplies.start()  # th_supplies começa supplies_loop() em paralelo
        print("Bot started....")

    # ─────────────────────────────────────────────────────────
    #  stop — Para o bot completamente
    # ─────────────────────────────────────────────────────────
    #  Chamado quando ESC é pressionado via key_code() em main.py.
    def stop(self):
        self.event_th.set()
        # Sinaliza para todas as threads pararem.
        # Loops em main.py com "if bot.event_th.is_set(): return" vão sair.
        # supplies_loop() em life_mana.py checa stop_event.is_set() e encerra.

        self.pause_th.set()
        # Caso o bot esteja PAUSADO quando ESC for pressionado:
        # a thread estará travada no .wait() e nunca checaria event_th.
        # pause_th.set() desbloqueia o .wait() → loop checa event_th → encerra.
        print("Bot stopped")

    # ─────────────────────────────────────────────────────────
    #  toggle_pause — Alterna entre pausado e rodando
    # ─────────────────────────────────────────────────────────
    #  Chamado quando CapsLock é pressionado via key_code() em main.py.
    #  Só afeta th_run — th_supplies continua rodando independente.
    def toggle_pause(self):
        if self.pause_th.is_set():
            # Bot está rodando (pause_th ativo = True) → pausa
            self.pause_th.clear()  # desativa → .wait() em main.py vai TRAVAR a thread
            print("Pausing...")
        else:
            # Bot está pausado (pause_th inativo = False) → retoma
            self.pause_th.set()    # reativa → .wait() em main.py vai LIBERAR a thread
            print("Resuming...")
