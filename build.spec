# -*- mode: python ; coding: utf-8 -*-
"""SessionLedger（会话簿）PyInstaller 打包配置。

用法（在项目根目录、激活打包用的 venv 之后）：
    pyinstaller --clean --noconfirm build.spec

产出：dist\\SessionLedger\\SessionLedger.exe（整个 dist\\SessionLedger\\ 文件夹是自包含的，拷走就能跑）

本文件是 UTF-8，中文路径靠这个。PyInstaller 会自己认。
"""

import os

# SPECPATH 就是本文件所在目录，**不要再 dirname** —— 多一层会指到项目外面去，
# Analysis 就找不到源码了。
ROOT = os.path.abspath(SPECPATH)

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    # 整个 assets 目录都进包 —— 源码直接跑时读的是同目录下的 assets/，
    # 打包后那目录在 _internal 里，靠这条送进去（main() 里按 _MEIPASS 找）
    datas=[(os.path.join(ROOT, "assets"), "assets")],
    hiddenimports=[
        # 主程序是 sys.path.insert 之后再 import 的，打包器不一定顺着找到，
        # 显式收进来稳妥
        "session_core",
        "i18n",           # 中英对照表，两个文件都 import 它
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ── Qt：本程序只用 QtCore / QtGui / QtWidgets ──
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
        "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DAnimation",
        "PySide6.Qt3DExtras", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
        "PySide6.QtLocation", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
        "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner",
        "PySide6.QtHelp", "PySide6.QtUiTools", "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets", "PySide6.QtSvg", "PySide6.QtSvgWidgets",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtNetwork", "PySide6.QtHttp",
        "PySide6.QtConcurrent", "PySide6.QtPrintSupport",
        "PySide6.QtDBus", "PySide6.QtXml", "PySide6.QtStateMachine",
        "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSpatialAudio",
        "PySide6.QtTextToSpeech", "PySide6.QtRemoteObjects",
        "PySide6.QtScript", "PySide6.QtScriptTools", "PySide6.QtWebSockets",
        # ── Python 层的大件，本程序一个都不用 ──
        "numpy", "scipy", "pandas", "matplotlib", "IPython",
        "torch", "torchaudio", "torchvision", "onnxruntime", "tensorflow",
        "fastapi", "uvicorn", "pydantic",
        # ── 标准库里用不到的 ──
        "tkinter", "unittest", "pydoc", "doctest",
        "email", "http", "xmlrpc", "ftplib", "smtplib",
        "PyQt5", "PyQt6", "PySide2",
    ],
    noarchive=False,
    optimize=1,                 # 去掉 assert 和 docstring，小一点
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # onedir：运行时不用解压，启动快，也不容易被杀软误报
    name="SessionLedger",       # exe 名。中文名只出现在窗口标题里（见 core.APP_TITLE）
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX 压缩会触发杀软启发式扫描，关掉
    console=False,              # 必须，否则会弹一个黑框
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "icon.ico"),
    version=os.path.join(ROOT, "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SessionLedger",
)
