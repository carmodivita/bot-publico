# =============================================================
#  tools/baixar_biblioteca.py — Baixa monstros, magias, poções e runas
# =============================================================
#  Fonte: TibiaWiki BR (https://www.tibiawiki.com.br), pela API oficial
#  do MediaWiki (sem raspar HTML). Gera arquivos JSON em biblioteca/.
#
#  Uso (na pasta do projeto):
#    python tools/baixar_biblioteca.py
#
#  Leva ~2 minutos: os pedidos são feitos em lotes de 50 páginas com
#  pausa entre eles, para não sobrecarregar o site. Rode de novo quando
#  quiser atualizar (sai um update do Tibia, por exemplo).
# =============================================================

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://www.tibiawiki.com.br/api.php"
UA = "Huntix-biblioteca/1.0 (projeto pessoal; uso local)"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "biblioteca")
PAUSA = 1.0  # segundos entre pedidos

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


# ─────────────────────────────────────────────────────────────
#  API
# ─────────────────────────────────────────────────────────────
def api(**params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = API + "?" + urllib.parse.urlencode(params)
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if tentativa == 3:
                raise
            print(f"  erro ({e}), tentando de novo…")
            time.sleep(3 * (tentativa + 1))
        finally:
            time.sleep(PAUSA)


def listar(**params):
    """Percorre uma listagem paginada (embeddedin / categorymembers) e devolve os títulos."""
    lista_key = params["list"]
    titulos, cont = [], {}
    while True:
        d = api(action="query", **params, **cont)
        titulos += [x["title"] for x in d["query"][lista_key]]
        if "continue" not in d:
            return titulos
        cont = d["continue"]


def conteudos(titulos):
    """Wikitext de cada página, em lotes de 50. Devolve {titulo: texto}."""
    out = {}
    for i in range(0, len(titulos), 50):
        lote = titulos[i:i + 50]
        d = api(action="query", prop="revisions", rvprop="content", rvslots="main",
                titles="|".join(lote))
        for p in d["query"]["pages"]:
            if "revisions" in p:
                out[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
        print(f"  {min(i + 50, len(titulos))}/{len(titulos)}")
    return out


# ─────────────────────────────────────────────────────────────
#  Parser do wikitext
# ─────────────────────────────────────────────────────────────
def infobox(texto, nome):
    """Campos "| chave = valor" do primeiro {{Infobox_<nome> ...}} da página."""
    i = texto.find("{{Infobox_" + nome)
    if i < 0:
        return None
    # acha o fechamento do template contando {{ }}
    nivel, j = 0, i
    while j < len(texto) - 1:
        par = texto[j:j + 2]
        if par == "{{":
            nivel += 1
            j += 2
            continue
        if par == "}}":
            nivel -= 1
            j += 2
            if nivel == 0:
                break
            continue
        j += 1
    corpo = texto[i:j]
    campos = {}
    for m in re.finditer(r"^\|\s*([\w]+)\s*=(.*?)(?=^\||\Z)", corpo, re.M | re.S):
        campos[m.group(1).strip()] = m.group(2).strip().rstrip("}").strip()
    return campos


def limpar(v):
    """Tira a marcação da wiki: [[A|B]] → B, [[A]] → A, {{...}}, <tags>, '''negrito'''."""
    if not v:
        return ""
    v = re.sub(r"<!--.*?-->", "", v, flags=re.S)
    v = re.sub(r"<br\s*/?>", "; ", v)
    v = re.sub(r"<[^>]+>", "", v)
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = v.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", v).strip(" ;,")


def numero(v):
    v = limpar(v).replace(".", "").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", v)
    if not m:
        return None
    n = float(m.group())
    return int(n) if n.is_integer() else n


def lista(v):
    v = limpar(v)
    return [x.strip() for x in re.split(r",|;| e ", v) if x.strip()] if v else []


# ─────────────────────────────────────────────────────────────
#  Monstros
# ─────────────────────────────────────────────────────────────
def monstros():
    print("Monstros: listando páginas…")
    titulos = listar(list="embeddedin", eititle="Predefinição:Infobox_Criatura", einamespace=0, eilimit=500)
    print(f"  {len(titulos)} páginas")
    out = []
    for titulo, texto in conteudos(titulos).items():
        c = infobox(texto, "Criatura")
        if not c or not c.get("hp"):
            continue
        fraquezas = {}
        for el in ("physical", "earth", "fire", "death", "energy", "holy", "ice"):
            mod = numero(c.get(f"{el}DmgMod", ""))
            if mod is not None:
                fraquezas[el] = mod
        out.append({
            "nome": limpar(c.get("name")) or titulo,
            "hp": numero(c.get("hp")),
            "exp": numero(c.get("exp")),
            "boss": limpar(c.get("isboss")).lower() == "sim",
            "classe": limpar(c.get("creatureclass")),
            "velocidade": numero(c.get("speed")),
            "dano_max": numero(c.get("maxdmg")),
            "dificuldade": limpar(c.get("dificuldade")),
            "invocavel_mana": numero(c.get("summon")),
            "convencivel_mana": numero(c.get("convince")),
            "dano_recebido_pct": fraquezas,       # 100 = normal, >100 = fraco, <100 = resistente
            "imunidades": lista(c.get("immunities")),
            "comportamento": limpar(c.get("behavior")),
            "loot": {k: limpar(c.get(f"loot{k}")) for k in ("comum", "incomum", "semiraro", "raro", "muitoraro")
                     if limpar(c.get(f"loot{k}"))},
            "versao": limpar(c.get("implemented")),
            "removido": limpar(c.get("removed")),
            "wiki": "https://www.tibiawiki.com.br/wiki/" + urllib.parse.quote(titulo.replace(" ", "_")),
        })
    return sorted(out, key=lambda m: m["nome"].lower())


# ─────────────────────────────────────────────────────────────
#  Magias
# ─────────────────────────────────────────────────────────────
def magias():
    print("Magias: listando páginas…")
    titulos = listar(list="embeddedin", eititle="Predefinição:Infobox_Spell", einamespace=0, eilimit=500)
    print(f"  {len(titulos)} páginas")
    out = []
    for titulo, texto in conteudos(titulos).items():
        c = infobox(texto, "Spell")
        if not c or not c.get("words"):
            continue
        out.append({
            "nome": limpar(c.get("name")) or titulo,
            "palavras": limpar(c.get("words")),
            "tipo": limpar(c.get("subclass")),
            "elemento": limpar(c.get("damagetype")),
            "mana": numero(c.get("mana")),
            "level": numero(c.get("expLvl")),
            "premium": limpar(c.get("premium")).lower() == "sim",
            "vocacoes": lista(c.get("voc")),
            "cooldown_s": numero(c.get("cooldownproprio")),
            "cooldown_grupo_s": numero(c.get("cooldowngrupo")),
            "efeito": limpar(c.get("effect")),
            "versao": limpar(c.get("implemented")),
            "wiki": "https://www.tibiawiki.com.br/wiki/" + urllib.parse.quote(titulo.replace(" ", "_")),
        })
    return sorted(out, key=lambda m: m["nome"].lower())


# ─────────────────────────────────────────────────────────────
#  Poções, fluidos e runas
# ─────────────────────────────────────────────────────────────
def suprimentos():
    print("Poções, fluidos e runas: listando páginas…")
    liquidos = listar(list="categorymembers", cmtitle="Categoria:Líquidos", cmnamespace=0, cmlimit=500)
    pocoes = [t for t in liquidos if "Potion" in t or t in ("Manafluid", "Lifefluid")]
    runas = listar(list="categorymembers", cmtitle="Categoria:Runas", cmnamespace=0, cmlimit=500)
    print(f"  {len(pocoes)} poções/fluidos, {len(runas)} runas")
    out = []
    textos = conteudos(pocoes + runas)
    for titulo, texto in textos.items():
        # runas usam {{Infobox_Runas}}; poções e fluidos, {{Infobox_Item}}
        c = infobox(texto, "Runas") or infobox(texto, "Item") or {}
        if not c:
            continue
        tipo = "runa" if titulo in runas else "fluido" if "fluid" in titulo.lower() else "poção"
        out.append({
            "nome": limpar(c.get("name")) or titulo,
            "tipo": tipo,
            "efeito": limpar(c.get("attrib") or c.get("effect")),
            "palavras": limpar(c.get("words")),
            "level": numero(c.get("levelrequired") or c.get("expLvl")),
            "magic_level": numero(c.get("mlrequired")),
            "quem_faz": lista(c.get("makevoc")),
            "mana_para_fazer": numero(c.get("makemana")),
            "peso": numero(c.get("weight")),
            "preco_npc": numero(c.get("npcprice")),
            "versao": limpar(c.get("implemented")),
            "wiki": "https://www.tibiawiki.com.br/wiki/" + urllib.parse.quote(titulo.replace(" ", "_")),
        })
    return sorted(out, key=lambda m: (m["tipo"], m["nome"].lower()))


# ─────────────────────────────────────────────────────────────
def salvar(nome, dados):
    os.makedirs(OUT, exist_ok=True)
    doc = {
        "fonte": "TibiaWiki BR — https://www.tibiawiki.com.br (conteúdo da comunidade, CC BY-SA)",
        "baixado_em": time.strftime("%Y-%m-%d"),
        "total": len(dados),
        "itens": dados,
    }
    with open(os.path.join(OUT, nome), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"→ biblioteca/{nome}: {len(dados)} itens\n")


if __name__ == "__main__":
    salvar("monstros.json", monstros())
    salvar("magias.json", magias())
    salvar("pocoes_runas.json", suprimentos())
    print("Pronto.")
