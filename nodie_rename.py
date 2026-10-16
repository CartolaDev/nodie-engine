#!/usr/bin/env python3
"""Nodie: troca "Godot" por "Nodie" só em textos escolhidos da interface.

Uso (na raiz do fork):
    python3 nodie_rename.py --dry   # só mostra o que mudaria
    python3 nodie_rename.py         # aplica

O que faz:
  1. version.py: name = "Godot Engine" -> "Nodie Engine" (short_name NÃO muda).
  2. Nos arquivos .cpp da lista abaixo, troca "Godot" por "Nodie" apenas dentro
     de chamadas TTR()/TTRC() cujo texto bate com uma das frases escolhidas.
  3. Nos arquivos editor/translations/editor/pt*.po, troca "Godot" por "Nodie"
     (no msgid E no msgstr) só das entradas cujo msgid era exatamente um dos
     textos alterados no passo 2, para a tradução continuar casando.

Não mexe em: LICENSE, COPYRIGHT, AUTHORS, tela Sobre, créditos, "Godot Physics",
"Godot 2/3/4", links e documentação online.
"""
import glob
import re
import sys

DRY = "--dry" in sys.argv

# Arquivos .cpp onde procurar.
CPP_FILES = [
    "editor/docks/editor_dock_manager.cpp",
    "editor/run/game_view_plugin.cpp",
    "editor/script/script_editor_plugin.cpp",
    "editor/editor_node.cpp",
    "editor/project_manager/project_manager.cpp",
    "editor/run/editor_run_bar.cpp",
]

# Só textos que contêm uma destas frases são alterados.
PHRASES = [
    "%s - Godot Engine",
    "this version of Godot",
    "Godot uses single precision",
    "this build of Godot",
    "About Godot",
    "modified outside Godot",
    "Godot crashed when opening",
    "Godot opened the project in Recovery Mode",
]

# "Godot" como palavra (inclusive logo depois de \n), mas sem pegar "Godot 3/4" (versões reais).
GODOT = re.compile(r"(?:(?<=\\n)|(?<![A-Za-z0-9_]))Godot(?![A-Za-z0-9_])(?!\s*\d)")
CALL = re.compile(r"TTR[A-Z]*\(")
LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
WS = re.compile(r"\s*")


def scan_call(text, start):
    """Lê os literais de string consecutivos logo depois de TTR( ."""
    i = start
    parts, spans = [], []
    while True:
        j = WS.match(text, i).end()
        m = LIT.match(text, j)
        if not m:
            break
        parts.append(m.group(1))
        spans.append((m.start(1), m.end(1)))
        i = m.end()
    return "".join(parts), spans


def process_cpp(path, originals):
    try:
        text = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"[aviso] {path} não existe, pulei")
        return 0
    edits = []  # (start, end, new_text)
    for m in CALL.finditer(text):
        joined, spans = scan_call(text, m.end())
        if not joined or not any(p in joined for p in PHRASES):
            continue
        if not GODOT.search(joined):
            continue
        originals.add(joined)
        for (a, b) in spans:
            piece = text[a:b]
            new = GODOT.sub("Nodie", piece)
            if new != piece:
                edits.append((a, b, new))
    for a, b, new in sorted(edits, reverse=True):
        text = text[:a] + new + text[b:]
    if edits and not DRY:
        open(path, "w", encoding="utf-8").write(text)
    print(f"{path}: {len(edits)} trecho(s) alterado(s)")
    return len(edits)


def po_joined(lines, key):
    """Junta as linhas entre aspas de msgid/msgstr de uma entrada."""
    out, on = [], False
    for ln in lines:
        if ln.startswith(key + " "):
            on = True
            out.append(re.match(r'\w+\s+"(.*)"\s*$', ln).group(1))
        elif on and ln.startswith('"'):
            out.append(ln.strip()[1:-1])
        elif on:
            break
    return "".join(out)


def process_po(path, originals):
    text = open(path, encoding="utf-8").read()
    blocks = re.split(r"\n\n+", text)
    changed = 0
    found = set()
    for idx, blk in enumerate(blocks):
        lines = blk.split("\n")
        if not any(ln.startswith("msgid ") for ln in lines):
            continue
        mid = po_joined(lines, "msgid")
        if mid in originals:
            new_lines = []
            for ln in lines:
                if ln.startswith("#"):
                    new_lines.append(ln)
                else:
                    new_lines.append(GODOT.sub("Nodie", ln))
            blocks[idx] = "\n".join(new_lines)
            changed += 1
            found.add(mid)
    if changed and not DRY:
        open(path, "w", encoding="utf-8").write("\n\n".join(blocks))
    print(f"{path}: {changed} entrada(s) alterada(s)")
    return found


def main():
    if DRY:
        print("== MODO TESTE (nada será gravado) ==")

    # 1. version.py
    try:
        v = open("version.py", encoding="utf-8").read()
        if 'name = "Godot Engine"' in v:
            if not DRY:
                v = v.replace('name = "Godot Engine"', 'name = "Nodie Engine"', 1)
                open("version.py", "w", encoding="utf-8").write(v)
            print('version.py: name -> "Nodie Engine"')
        else:
            print("version.py: nada a trocar (já alterado?)")
    except FileNotFoundError:
        print("[erro] rode na raiz do fork (version.py não encontrado)")
        return

    # 2. .cpp
    originals = set()
    for f in CPP_FILES:
        process_cpp(f, originals)
    print(f"\n{len(originals)} texto(s) de interface alterado(s) no código.")

    # 3. traduções
    all_found = set()
    for po in sorted(glob.glob("editor/translations/editor/pt*.po")):
        all_found |= process_po(po, originals)
    missing = originals - all_found
    if missing:
        print("\nSem tradução em português (aparecem em inglês, tudo bem):")
        for s in sorted(missing):
            print("  -", s[:90])

    print("\nPronto. Recompile para ver as mudanças.")


if __name__ == "__main__":
    main()
