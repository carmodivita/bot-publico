# =============================================================
#  class_teach.py — Guia de Classes aplicado ao bot-26
# =============================================================
#  Este arquivo NÃO é importado por ninguém.
#  Serve apenas para você ler, consultar e entender.
#  Todo o código aqui é comentado e explicativo.
# =============================================================


import threading
import time


# ─────────────────────────────────────────────────────────────
#  PARTE 1 — O que é uma classe?
# ─────────────────────────────────────────────────────────────
#
#  Uma classe é um "molde" ou "planta de construção".
#  Ela DESCREVE como algo funciona, mas não cria nada ainda.
#
#  Analogia:
#    Planta de uma casa  →  class ThreadController
#    Casa construída     →  bot = ThreadController(run_func=run)
#
#  Você pode construir várias casas com a mesma planta:
#    bot1 = ThreadController(run_func=run_cave)
#    bot2 = ThreadController(run_func=run_surface)
#  Cada uma é independente, com seus próprios eventos e threads.
#
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
#  PARTE 2 — Anatomia de uma classe simples
# ─────────────────────────────────────────────────────────────

class ExemploSimples:
    #
    #  __init__ = construtor
    #  ─────────────────────
    #  Roda automaticamente quando você escreve:
    #    obj = ExemploSimples("meu bot")
    #
    #  "self" = o próprio objeto sendo criado
    #  É como se "self" fosse o bot dizendo "eu mesmo tenho..."
    #  Sempre é o primeiro parâmetro, mas você nunca passa ele —
    #  o Python coloca automaticamente.
    #
    def __init__(self, nome):

        # Atributos = variáveis guardadas DENTRO do objeto.
        # Acessados com:  obj.nome_do_atributo
        self.nome     = nome   # guarda o nome recebido
        self.rodando  = False  # estado inicial: parado

    #  Métodos = funções que pertencem à classe.
    #  Chamados com:  obj.nome_do_metodo()
    #  Sempre recebem "self" para poder acessar os próprios atributos.

    def iniciar(self):
        self.rodando = True
        print(f"[{self.nome}] iniciado!")

    def parar(self):
        self.rodando = False
        print(f"[{self.nome}] parado!")

    def status(self):
        estado = "rodando" if self.rodando else "parado"
        print(f"[{self.nome}] está {estado}")


# Como usar:
#
#   obj = ExemploSimples("bot-26")  →  chama __init__, cria o objeto
#   obj.iniciar()                   →  self.rodando = True, printa
#   obj.status()                    →  printa "rodando"
#   obj.parar()                     →  self.rodando = False
#   obj.status()                    →  printa "parado"
#
#   obj2 = ExemploSimples("bot-27") →  outro objeto independente
#   obj2.iniciar()                  →  não afeta obj


# ─────────────────────────────────────────────────────────────
#  PARTE 3 — O ThreadController do bot, linha a linha
# ─────────────────────────────────────────────────────────────
#
#  Estrutura atual:
#
#  ┌─────────────────────────────────────────────┐
#  │           ThreadController                  │
#  │                                             │
#  │  Atributos (variáveis):                     │
#  │    self.event_th  →  sinal de PARAR         │
#  │    self.pause_th  →  sinal de PAUSAR        │
#  │    self.th_run    →  thread do jogo         │
#  │    self.th_supplies → thread da cura        │
#  │                                             │
#  │  Métodos (funções):                         │
#  │    start()        →  inicia as threads      │
#  │    stop()         →  para tudo              │
#  │    toggle_pause() →  pausa ou retoma        │
#  └─────────────────────────────────────────────┘

class ThreadController:

    def __init__(self, run_func):
        # run_func é a função run() que vem do main.py.
        # Passamos ela como parâmetro para evitar importar main.py aqui
        # (isso causaria "importação circular" e quebraria o programa).

        # ── Eventos ──────────────────────────────────────
        #
        # threading.Event() cria um "sinal binário":
        #   .set()    →  ativa o sinal   (True)
        #   .clear()  →  desativa        (False)
        #   .is_set() →  retorna True ou False
        #   .wait()   →  TRAVA a thread até o sinal ficar ativo (True)

        self.event_th = threading.Event()
        # Começa NÃO setado → bot pode rodar.
        # ESC chama .set() → todos os loops que checam .is_set() retornam.

        self.pause_th = threading.Event()
        self.pause_th.set()
        # Começa SETADO → .wait() passa direto → bot não está pausado.
        # CapsLock chama .clear() → .wait() TRAVA as threads → bot pausa.
        # CapsLock de novo → .set() → .wait() libera → bot retoma.

        # ── Threads ──────────────────────────────────────
        #
        # threading.Thread() CRIA a thread mas NÃO a inicia ainda.
        # target= → qual função essa thread vai executar
        # daemon=True → a thread morre junto com o programa principal
        #               sem precisar de .join() ou .stop() manual

        self.th_run = threading.Thread(
            target=run_func,  # executa run() do main.py
            daemon=True
        )

        self.th_supplies = threading.Thread(
            target=...,       # aqui entraria life_mana.supplies_loop
            args=(self.event_th, 0.8),
            # args= → parâmetros para supplies_loop(stop_event, interval)
            # só passa event_th, NÃO pause_th → cura não pausa com CapsLock
            daemon=True
        )

    # ── Métodos ──────────────────────────────────────────────

    def start(self):
        # .start() é o que REALMENTE faz a thread começar a rodar.
        # Após isso, th_run e th_supplies rodam em paralelo com o resto.
        # ATENÇÃO: .start() só pode ser chamado UMA VEZ por thread.
        self.th_run.start()
        self.th_supplies.start()
        print("Bot started....")

    def stop(self):
        self.event_th.set()
        # Todos os loops com "if bot.event_th.is_set(): return" vão sair.

        self.pause_th.set()
        # Por que isso? Se a thread estiver PAUSADA (travada no .wait()),
        # o event_th.set() sozinho não a desbloquearia — ela continuaria
        # travada esperando o pause_th ser setado.
        # Então: pause_th.set() → desbloqueia o wait() → loop checa
        # event_th.is_set() → retorna → thread encerra.
        print("Bot stopped")

    def toggle_pause(self):
        if self.pause_th.is_set():
            self.pause_th.clear()  # desativa → .wait() vai TRAVAR as threads
            print("Pausing...")
        else:
            self.pause_th.set()    # reativa → .wait() LIBERA as threads
            print("Resuming...")


# ─────────────────────────────────────────────────────────────
#  PARTE 4 — Como adicionar uma nova thread
# ─────────────────────────────────────────────────────────────
#
#  Exemplo: você quer adicionar uma thread de "walker"
#  que navega pelos waypoints e PAUSA com CapsLock.
#
#  Passo 1 — cria a função no main.py que a thread vai executar:
#
#    def walk_loop():
#        for item in dados:
#            bot.pause_th.wait()           # pausa com CapsLock
#            if bot.event_th.is_set():     # para com ESC
#                return
#            go_flag(item["path"], 2)      # vai até o waypoint
#
#  Passo 2 — adiciona o parâmetro e a thread no __init__:
#
#    def __init__(self, run_func, walk_func):   # ← adiciona walk_func
#
#        ... (tudo que já existe) ...
#
#        self.th_walker = threading.Thread(
#            target=walk_func,   # ← executa walk_loop do main.py
#            daemon=True
#        )
#        # walk_func usa pause_th → pausa com CapsLock
#        # walk_func usa event_th → para com ESC
#
#  Passo 3 — inicia no start():
#
#    def start(self):
#        self.th_run.start()
#        self.th_supplies.start()
#        self.th_walker.start()   # ← adiciona aqui
#        print("Bot started....")
#
#  Passo 4 — cria o bot passando a nova função:
#
#    bot = ThreadController(run_func=run, walk_func=walk_loop)
#
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
#  PARTE 5 — Como criar uma segunda classe separada
# ─────────────────────────────────────────────────────────────
#
#  Quando uma funcionalidade cresce demais, você separa em
#  uma classe própria. Exemplo: WalkerController para navegação.
#
#  Arquivo: walker.py
#  ──────────────────
#
#    class WalkerController:
#
#        def __init__(self, dados, bot):
#            # dados = lista de waypoints (do info.json)
#            # bot   = o ThreadController, para acessar os eventos
#            self.dados = dados
#            self.bot   = bot         # guarda referência ao bot
#            self.index = 0           # qual waypoint estamos agora
#
#        def go_next(self):
#            # vai para o próximo waypoint da lista
#            item = self.dados[self.index]
#            # ... lógica de navegação com go_flag() ...
#            # avança o índice, volta para 0 ao chegar no fim
#            self.index = (self.index + 1) % len(self.dados)
#
#        def walk_loop(self):
#            # esta função roda em uma thread
#            while not self.bot.event_th.is_set():   # para com ESC
#                self.bot.pause_th.wait()            # pausa com CapsLock
#                self.go_next()
#                time.sleep(0.5)
#
#  No main.py:
#  ───────────
#    from walker import WalkerController
#
#    walker = WalkerController(dados=dados, bot=bot)
#
#  No ThreadController.__init__:
#  ─────────────────────────────
#    def __init__(self, run_func, walker):
#        ...
#        self.th_walker = threading.Thread(
#            target=walker.walk_loop,  # método da classe WalkerController
#            daemon=True
#        )
#
#  Diferença de chamar um método de classe vs função normal:
#    target=walk_loop         → função solta do main.py
#    target=walker.walk_loop  → método do objeto walker
#  Os dois funcionam igual para threading.Thread.
#
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
#  PARTE 6 — Visualização geral: arquivos, classes e threads
# ─────────────────────────────────────────────────────────────
#
#  Como os arquivos se relacionam hoje:
#
#  main.py
#    │  importa ThreadController de thread_bot.py
#    │  define funções de jogo: go_flag, pixel_atk, atk_monster, run
#    │  bot = ThreadController(run_func=run)
#    │  key_code → bot.start() / bot.stop() / bot.toggle_pause()
#    └──► listener.join() → trava a main thread aqui para sempre
#
#  thread_bot.py
#    │  class ThreadController
#    │    atributos: event_th, pause_th, th_run, th_supplies
#    │    métodos:   start(), stop(), toggle_pause()
#    └──► importa life_mana para usar em th_supplies
#
#  life_mana.py
#    │  supplies_loop(stop_event, interval)
#    └──► roda dentro de th_supplies
#
#
#  Threads rodando após apertar Backspace:
#
#  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
#  │   Main Thread   │  │    th_run       │  │   th_supplies   │
#  │                 │  │                 │  │                 │
#  │  pynput         │  │  run()          │  │ supplies_loop() │
#  │  Listener       │  │  atk_monster()  │  │                 │
#  │                 │  │  go_flag()      │  │  checa vida     │
#  │  escuta teclas  │  │                 │  │  e mana         │
#  │  para sempre    │  │  PAUSA c/ Caps  │  │  NÃO pausa      │
#  └─────────────────┘  └─────────────────┘  └─────────────────┘
#          │                    │                     │
#          └────────────────────┴─────────────────────┘
#                     todas param com ESC
#                     via event_th.set()
#
#
#  Se você adicionar walker e WalkerController no futuro:
#
#  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
#  │  Main    │  │ th_run   │  │th_supplies│  │  th_walker   │
#  │ Thread   │  │          │  │           │  │              │
#  │ listener │  │ ataque   │  │ cura/mana │  │ navegação    │
#  │          │  │ loot     │  │           │  │ waypoints    │
#  │          │  │ PAUSA    │  │ NÃO pausa │  │ PAUSA        │
#  └──────────┘  └──────────┘  └──────────┘  └──────────────┘
#
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
#  PARTE 7 — Diferença entre atributo e método (sua dúvida)
# ─────────────────────────────────────────────────────────────
#
#  Os dois são acessados com "bot." — por isso parecem iguais.
#  Mas são coisas diferentes:
#
#    bot.event_th          → atributo: é uma VARIÁVEL dentro do bot
#    bot.event_th.is_set() → acessa a variável e chama um método DELA
#    bot.start()           → método: é uma FUNÇÃO que o bot executa
#
#  Acessar atributos internos de fora da classe funciona,
#  mas não é a forma mais limpa. O ideal é expor métodos:
#
#    # Dentro do ThreadController:
#    def wait_if_paused(self):
#        self.pause_th.wait()       # quem chama não sabe que existe pause_th
#
#    def should_stop(self):
#        return self.event_th.is_set()  # quem chama não sabe que existe event_th
#
#  Aí no main.py fica assim:
#
#    bot.wait_if_paused()      # igual a: bot.pause_th.wait()
#    if bot.should_stop():     # igual a: if bot.event_th.is_set():
#        return
#
#  Vantagem: se você renomear "event_th" para "stop_signal",
#  só muda dentro do ThreadController — o main.py não precisa saber.
#
# ─────────────────────────────────────────────────────────────
