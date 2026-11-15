from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
source = root / "src"
migrations = source / "dungeon_drop_analyzer" / "migrations"

hidden_imports = collect_submodules("alembic") + [
    "sqlalchemy.dialects.sqlite",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
    "openpyxl.cell._writer",
]

excluded_modules = [
    "tkinter",
    "statsmodels",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.Qt3DCore",
    "PySide6.QtMultimedia",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
]

analysis = Analysis(
    [str(root / "scripts" / "pyinstaller_entry.py")],
    pathex=[str(source)],
    hiddenimports=hidden_imports,
    excludes=excluded_modules,
    noarchive=False,
)
analysis.datas += Tree(
    str(migrations),
    prefix="dungeon_drop_analyzer/migrations",
    excludes=["__pycache__", "*.pyc"],
)

archive = PYZ(analysis.pure)

executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="DungeonDropAnalyzer",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)

COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="DungeonDropAnalyzer",
)
