#!/usr/bin/env bash
# Cria a venv (.venv) e instala o projeto em modo editável com dependências de desenvolvimento.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || python -m venv .venv
PY=.venv/Scripts/python.exe
[ -x "$PY" ] || PY=.venv/bin/python
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -e ".[dev]"
echo "Pronto."
