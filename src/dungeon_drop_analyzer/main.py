"""Ponto de entrada da aplicação."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import dungeon_drop_analyzer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="DungeonDropAnalyzer",
        description="Dungeon Drop Analyzer: registro e análise estatística de drops de masmorras.",
    )
    parser.add_argument("--version", action="store_true", help="mostra a versão e sai")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="executa a autoverificação em um diretório temporário e sai",
    )
    parser.add_argument(
        "--output", metavar="ARQUIVO", help="arquivo JSON do resultado da autoverificação"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args, _ = build_parser().parse_known_args(argv)
    if args.version:
        print(f"Dungeon Drop Analyzer {dungeon_drop_analyzer.__version__}")
        return 0
    if args.self_check:
        from dungeon_drop_analyzer.selfcheck import run_self_check

        return run_self_check(args.output)
    from dungeon_drop_analyzer.ui.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
