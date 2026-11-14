"""Ponto de entrada da aplicação."""

from __future__ import annotations


def main() -> int:
    from dungeon_drop_analyzer.ui.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
