# SessionLedger（会话簿）打包后瘦身 —— 砍掉 PySide6 里用不到的模块。
#
# 用法（在项目根目录、打包完成之后）：
#     powershell -ExecutionPolicy Bypass -File slim.ps1
#
# ★★★ 删错了是【静默失败】★★★
# 打包不会报错、程序照样启动，要等用户点到那个功能才发现。
# 所以：**一次只删一类，每类删完跑一遍程序**，稳了再删下一类。
# 底下按 A / B / C 分好了，想更稳就把 $only 改成 "A"、"B"、"C" 一个一个来。
#
# 删之前先整份拷一份 dist\SessionLedger\ 当备份。

param(
    [string]$only = "all"      # all / A / B / C
)

$root = Join-Path $PSScriptRoot "dist\SessionLedger\_internal\PySide6"
if (-not (Test-Path $root)) {
    Write-Host "找不到 $root" -ForegroundColor Red
    Write-Host "请先在项目根目录跑完 pyinstaller，确认产出在 dist\SessionLedger\ 下。"
    exit 1
}

function Nuke($paths) {
    foreach ($p in $paths) {
        $full = Join-Path $root $p
        if (Test-Path $full) {
            Remove-Item $full -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  删 $p"
        }
    }
}

$do = { param($c) $only -eq "all" -or $only -eq $c }

if (& $do "A") {
    Write-Host "[A] Qt DLL —— 用不到的模块" -ForegroundColor Cyan
    # 说明：本程序只用 QtCore / QtGui / QtWidgets。
    # 下面每一个都注明「它管的功能本程序有没有」。
    Nuke @(
        "Qt6WebEngineCore.dll", "Qt6WebEngineQuick.dll", "QtWebEngineProcess.exe",  # 内嵌浏览器：无
        "Qt6Qml.dll", "Qt6Quick.dll", "Qt6Quick3D.dll",                             # QML：无（用的是 QSS + Widgets）
        "Qt6QuickWidgets.dll", "Qt6QuickControls2.dll",
        "Qt6Pdf.dll",                                                               # PDF 预览：无
        "Qt6Multimedia.dll",                                                        # 音视频：无
        "Qt6Charts.dll", "Qt6DataVisualization.dll",                                # 图表：无（用 QTableView）
        "Qt6Sql.dll",                                                               # 数据库：无（数据存 json）
        "Qt6Test.dll",                                                              # 测试模块：发布版不用
        "Qt6Bluetooth.dll", "Qt6Nfc.dll", "Qt6Positioning.dll", "Qt6Location.dll",  # 蓝牙/NFC/GPS/串口：无
        "Qt6Sensors.dll", "Qt6SerialPort.dll", "Qt6SerialBus.dll",
        "Qt6Designer.dll", "Qt6Help.dll", "Qt6UiTools.dll",                         # 界面全代码写，没有 .ui 文件
        "Qt6TextToSpeech.dll", "Qt6WebSockets.dll",                                 # 无
        "Qt6Network.dll", "Qt6Http.dll",                                            # 不联网
        "Qt6OpenGL.dll", "Qt6OpenGLWidgets.dll",                                    # 没有自定义 OpenGL 渲染
        "Qt6PrintSupport.dll",                                                      # 不打印
        "Qt6Concurrent.dll", "Qt6DBus.dll",                                         # 没用
        "Qt6Xml.dll", "Qt6StateMachine.dll", "Qt6Scxml.dll",
        "Qt6RemoteObjects.dll", "Qt6Script.dll", "Qt6ScriptTools.dll",
        "Qt6SpatialAudio.dll",
        "Qt6Svg.dll"                                                                # 本程序不提供 SVG 背景图
    )
    # qsvg 插件依赖 Qt6Svg，一起删（要么都留要么都删，别一半一半）
    $qsvg = Join-Path $root "plugins\imageformats\qsvg.dll"
    if (Test-Path $qsvg) { Remove-Item $qsvg -Force; Write-Host "  删 plugins\imageformats\qsvg.dll" }

    # translations：只留中文那一份。
    # ★ 千万不能整目录删 —— Qt 内置控件的按钮文字（QMessageBox 的「是/否」、
    #   QInputDialog 的「确定/取消」）就靠它。删了中文界面里会蹦出英文按钮。
    $tr = Join-Path $root "translations"
    if (Test-Path $tr) {
        Get-ChildItem "$tr\*.qm" |
            Where-Object { $_.Name -ne "qtbase_zh_CN.qm" } |
            ForEach-Object { Remove-Item $_.FullName -Force }
        Write-Host "  translations 只留 qtbase_zh_CN.qm"
    }
}

if (& $do "B") {
    Write-Host "[B] Qt plugins —— 用不到的" -ForegroundColor Cyan
    # 注意：iconengines 和 imageformats 不在此列，它们是【保留】的。
    Nuke @(
        "plugins\sqldrivers",        # 无数据库
        "plugins\multimedia",        # 无音视频
        "plugins\bearer",            # Qt5 遗留的网络承载，Qt6 已废弃
        "plugins\canbus",            # 无 CAN 总线
        "plugins\designer",          # 不用 Qt Designer
        "plugins\platformthemes",    # 不用平台原生主题（程序里 setStyle("Fusion")）
        "plugins\printsupport",      # 不打印
        "plugins\qmltooling",        # 不用 QML
        "plugins\sceneparsers",      # 不用 Qt3D
        "plugins\virtualkeyboard",   # 不用虚拟键盘
        "plugins\styles"             # Fusion 是编译在 QtWidgets 里的内置样式，不靠插件
    )
}

if (& $do "C") {
    Write-Host "[C] 其他" -ForegroundColor Cyan
    Nuke @(
        "resources",                 # WebEngine 的资源，WebEngine 已删
        "qml",                       # QML 运行时资源
        "typesystems",               # QML 类型系统
        "include", "lib", "scripts"  # 开发用头文件/脚本，运行时不需要
    )
}

Write-Host ""
Write-Host "保留清单（删完必须还在）：" -ForegroundColor Yellow
$must = @(
    "plugins\platforms\qwindows.dll",     # 没它窗口打不开
    "plugins\imageformats\qjpeg.dll",     # .jpg 背景图
    "plugins\imageformats\qgif.dll",      # .gif 背景图
    "plugins\imageformats\qwebp.dll",     # .webp 背景图
    "plugins\imageformats\qico.dll",
    "translations\qtbase_zh_CN.qm"        # 中文按钮
)
$bad = 0
foreach ($m in $must) {
    if (Test-Path (Join-Path $root $m)) { Write-Host "  OK   $m" -ForegroundColor Green }
    else { Write-Host "  没了 $m  ← 出事" -ForegroundColor Red; $bad++ }
}

Write-Host ""
if ($bad -gt 0) {
    Write-Host "有 $bad 个必须保留的文件不见了，**先把备份拷回来**，再检查上面的删除列表。" -ForegroundColor Red
} else {
    Write-Host "保留项都在。现在去跑 dist\SessionLedger\SessionLedger.exe，逐条对验证清单：" -ForegroundColor Yellow
}
@"

  [ ] 选一张 .jpg  / .gif  / .webp  / .png  / .bmp 当背景图 -> 都能显示
  [ ] 触发一次删除确认框 -> 按钮是「是(Y)」「否(N)」，不是 Yes/No
  [ ] 触发一次改名框     -> 按钮是「确定」「取消」，不是 OK/Cancel
  [ ] 切到 English -> 界面全英文，弹窗按钮变 Yes/No/OK/Cancel
  [ ] 窗口能开，没有黑框一闪
  [ ] 双击一行能开终端；改名 / 删除 / 回收站 / 恢复 都能用
  [ ] 关掉再开，设置都还在
  [ ] 任一弹窗的标题栏颜色跟主窗口一致
"@ | Write-Host
