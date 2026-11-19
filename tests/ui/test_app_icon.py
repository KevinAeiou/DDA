"""Ícone do aplicativo: arquivos distribuídos e formato do .ico."""

import struct

from dungeon_drop_analyzer.ui.app_icon import ICON_SIZES, RESOURCES_DIR, load_app_icon


def test_pngs_e_ico_existem():
    for size in ICON_SIZES:
        assert (RESOURCES_DIR / f"icon-{size}.png").is_file()
    assert (RESOURCES_DIR / "icon.ico").is_file()


def test_ico_tem_varios_tamanhos_com_png_embutido():
    data = (RESOURCES_DIR / "icon.ico").read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data)
    assert (reserved, kind) == (0, 1) and count >= 6
    tamanhos = set()
    for index in range(count):
        width, _, _, _, _, bits, length, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * index
        )
        tamanhos.add(width or 256)
        assert data[offset : offset + 8] == b"\x89PNG\r\n\x1a\n" and length > 0 and bits == 32
    assert {16, 32, 256} <= tamanhos


def test_icone_da_janela_carrega(qapp):
    assert not load_app_icon().isNull()
