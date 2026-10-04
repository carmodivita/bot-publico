# =============================================================
#  biblioteca.py — Consulta a biblioteca de monstros, magias e suprimentos
# =============================================================
#  Lê os JSON de biblioteca/ (gerados por tools/baixar_biblioteca.py,
#  a partir da TibiaWiki BR — Tibia atual). Base de reconhecimento: a aba
#  Ajustes usa as magias e poções; monstros ficam para recursos futuros
#  (prioridade de alvo por EXP/HP, estimar EXP/hora...).
#
#  Exemplos:
#    import biblioteca
#    biblioteca.monstro("rotworm")["hp"]            → 65
#    biblioteca.buscar("magias", "exura ico")
#    biblioteca.buscar("suprimentos", tipo="runa")
# =============================================================

import json
import os
import unicodedata

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biblioteca")
ARQUIVOS = {
    "monstros": "monstros.json",
    "magias": "magias.json",
    "suprimentos": "pocoes_runas.json",
}
_cache = {}


def _norm(texto):
    """minúsculo e sem acento, para a busca achar 'pocao' em 'poção'."""
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return texto.lower().strip()


def carregar(tipo):
    """Lista de registros de 'monstros', 'magias' ou 'suprimentos' ([] se não baixado)."""
    if tipo not in _cache:
        caminho = os.path.join(BASE, ARQUIVOS[tipo])
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                _cache[tipo] = json.load(f)["itens"]
        else:
            _cache[tipo] = []
    return _cache[tipo]


def info(tipo):
    """Metadados do arquivo (fonte, data, total) ou None."""
    caminho = os.path.join(BASE, ARQUIVOS[tipo])
    if not os.path.exists(caminho):
        return None
    with open(caminho, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return {k: doc[k] for k in ("fonte", "baixado_em", "total")}


def buscar(tipo, texto="", **filtros):
    """Registros cujo nome (ou palavras mágicas) contém 'texto'.
    filtros extras comparam campos exatos, ex.: tipo="runa", boss=False."""
    t = _norm(texto)
    out = []
    for r in carregar(tipo):
        if any(r.get(k) != v for k, v in filtros.items()):
            continue
        if t and t not in _norm(r.get("nome")) and t not in _norm(r.get("palavras")):
            continue
        out.append(r)
    return out


def monstro(nome):
    """Registro do monstro pelo nome exato (sem diferenciar maiúsculas/acentos) ou None."""
    n = _norm(nome)
    return next((r for r in carregar("monstros") if _norm(r["nome"]) == n), None)


def recarregar():
    _cache.clear()
