# -*- coding: utf-8 -*-
"""会话簿（SessionLedger）—— 界面层。

数据层在 session_core.py：读记录、改名、删除、配置存档，完全不碰界面。

半透明是 Qt 的原生能力：列表、搜索框、按钮都设成 rgba 半透明色，
Qt 在合成时把它们和底下的背景图混起来 —— 不需要额外开窗口、不需要颜色键、
不需要同步，也就没有「追不上」的僵硬感。

界面支持中英双语和七套配色主题：主题见下面的 THEMES，文案见 i18n.py。
"""

import os
import sys
import time
import traceback

from PySide6.QtCore import (
    QAbstractTableModel, QByteArray, QEvent, QLibraryInfo, QLocale, QModelIndex,
    QObject, QRect, QSortFilterProxyModel, QTranslator, Qt, QTimer,
)
from PySide6.QtGui import (
    QColor, QIcon, QKeySequence, QPainter, QPalette, QPen, QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QAbstractScrollArea, QApplication, QButtonGroup, QCheckBox,
    QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMenu, QMessageBox, QPushButton, QRadioButton, QSlider, QStyledItemDelegate,
    QTableView, QVBoxLayout, QWidget,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_core as core            # noqa: E402
import i18n                            # noqa: E402
from i18n import T                     # noqa: E402

# 设置对话框里所有控件和标签的统一行高。
# 全都钉成同一个数，标签和控件才能靠「各自的框一样高 + 内部居中」对齐；
# 参差不齐的话，怎么调都会有几像素的错位。
FIELD_H = 30

SORT_ROLE = Qt.UserRole + 1
SORTER_COL = 2                          # 「最后活动」那一列，默认按它排

# 新建对话时，给这一次会话单独建一个子目录，并让 Claude 把产出都放进那儿。
#
# 为什么是「每次一个」而不是「大家共用一个」：共用一个的话，所有会话的产出
# 还是堆在一起，只是从工作区根目录挪到了那个子目录里 —— 混乱没解决，只换了地方。
# 每次一个才真的分得开。
#
# 为什么用提示词而不是 hook 改写路径：hook 只能改 Write/Edit 的 file_path，
# AI 用 shell 命令写文件就绕过去了，而且写 hook 的成本高得多。
# 提示词不是硬保证，但足够简单、够用。
#
# 提示词**必须全 ASCII**：它要穿过 cmd.exe 才到得了 claude，
# 中文在那一层可能被终端代码页搞乱。子目录名用时间戳，天然是 ASCII。
SESSION_DIR_PROMPT = "Put every file you create in this session under the %s/ subfolder."

# ———————————————— 配色 ————————————————
# 每个控件都要显式写 color：Qt 会跟着系统主题走，你这台是深色主题，
# 不写的话文字默认是白的，配上我们自己刷的浅背景就成了白字配白底 —— 字直接看不见。
# 所以每套配色都写全，再按当前深浅挑一套。
#
# 每套都必须齐三样东西，apply_theme 靠它们做判断，不再靠主题名去猜：
#   "dark"          —— 这套是深是浅
#   "text_presets"  —— 这套的正文色三档（柔和/标准/高对比）
#   "panel_a"       —— 同时是「默认值」和「其余层 alpha 的缩放基准」
#
# 文字对比：只动正文色，别的都不碰。
# 纯黑压纯白约 18.5:1，会有光渗毛刺（Halation）—— 这是「刺眼」里除纯白之外的另一个来源。
TEXT_PRESETS = {
    "soft": (58, 63, 71),
    "normal": (44, 48, 56),
    "high": (36, 40, 47),
}
# 偏暖的那几套，正文也得跟着暖 —— 套上面那组冷灰会把色温调白
TEXT_PRESETS_WARM = {
    "soft": (62, 57, 49),
    "normal": (48, 44, 38),
    "high": (40, 36, 30),
}
TEXT_PRESETS_ROSE = {
    "soft": (64, 52, 58),
    "normal": (52, 42, 46),
    "high": (44, 34, 38),
}

LIGHT = {
    "name": "珠光",
    "dark": False,
    "text_presets": TEXT_PRESETS,
    # 浅色刺眼的主因不是对比度，是【大面积纯白】：2560 这类高分屏上
    # 整片 255 一起发光，就是「手电筒效应」。所以底色和遮罩都压在 255 以下。
    "base": (222, 226, 234),        # 窗口底色：柔和冷灰。
                                    # 深这一档是给【没设背景图】用的 —— 有图时它被图盖住，
                                    # 无图时它就是衬托面板的「桌面」。太浅的话所有面板会挤在
                                    # 同一个亮度带里，整窗糊成一片（实测过：236 时各层只差 10 级）。
    "wash": (246, 247, 250),        # 淡化遮罩：珠光白。往【白】里淡是对的
                                    # （往灰里淡会把图片洗成灰调 = 发闷，那才是「糊」的来源），
                                    # 但白不该是纯白 —— 纯白会把图片亮部全推到 255。
    "wash_max": 0.85,               # 淡化滑杆上限：永远留 15% 背景漫反射
    "soft": (244, 245, 247),        # 背景图的固定柔化层：滑杆拉到 0 时也生效，
    "soft_a": 0.16,                 # 免得高对比的图直接冲上来
    "text": (44, 48, 56),           # 深炭灰。纯黑压纯白约 18.5:1，会有光渗毛刺；
    "dim": (108, 114, 124),         # 这个约 11:1，够清楚又不扎
    "window": (244, 246, 249),      # 弹窗底色
    # 层次全靠不同的灰度撑，不能白叠白：
    #   背景：底图往珠光白淡化   列表：丝绸白   表头：冷灰   详情/状态栏：浅灰   隔行：淡灰
    "panel": (252, 253, 255),
    "panel_a": 150,
    "head": (204, 208, 217),        # 表头必须比窗口底【更暗】才成一条看得见的横带。
                                    # 夹在窗口底和面板中间的话，两头都挨得近，等于没有。
    "head_a": 200,
    "strip": (232, 235, 242),
    "strip_a": 175,
    "alt": (218, 221, 229),         # 隔行：跟面板白拉开 34 级。只差十几级的话，
                                    # 那点差再乘上不透明度就只剩几个色阶，肉眼看不见。
    "alt_a": 150,                   # 必须和 panel_a 一致：隔行只靠明度差区分，
                                    # 不能再靠「多叠一层」（见 TableRowDelegate）
    "hover_a": 195,
    "press_rgb": (224, 230, 242),
    "ctrl": (250, 252, 255),        # 按钮、输入框的底色（以前写死在 build_qss 里）
    "ctrl_a": 170,
    "line": (0, 0, 0),
    "line_a": 28,                   # 1px 微边框：给界面一个暗部锚点，视线有落点
    "row_line_a": 14,               # 行与行之间的分隔线
    "sel": "rgba(96, 132, 172, 130)",     # 选中：柔和的蓝，不再是扎眼的饱和蓝
    "sel_solid": (150, 172, 196),         # 同上，给调色板用（QColor 不认 rgba 写法）
    "sel_text": "#1a1d22",
    "handle": (140, 146, 156),      # 滚动条滑块：中灰，不要白
    "sb_trough": (0, 0, 0), "sb_trough_a": 16,      # 滚动条轨道：极淡的灰
    "sb_handle": (0, 0, 0), "sb_handle_a": 70,      # 滚动条滑块：中灰
    "disabled": (150, 153, 158),
    "placeholder": (132, 136, 142),
    # 没设背景图时，标题栏用这个色。必须跟 base 走 —— 它是窗口的一部分。
    # 之前固定在 (244,246,249)，是给旧的浅底配的；base 压到 222 之后
    # 它还留在原处，就比窗口亮出一大截，无背景时特别割裂。
    # 现在取 base 往上抬 10 级：写成一模一样会「太融」，看不出哪条是标题栏。
    "title_fallback": (232, 236, 244),
}
DARK = {
    "name": "午夜",
    "dark": True,
    "base": (22, 24, 28),
    "text": (232, 234, 238),
    "dim": (158, 162, 170),
    "window": (28, 30, 35),
    # 关键：深色下要用【黑】去压暗图片，不能用白 ——
    # 用白提亮的话，浅色字正好顶在图片本来就亮的区域上，直接看不清
    "panel": (0, 0, 0),
    "panel_a": 105,                 # 比之前轻 —— 让图片透出来更多，跟四周接近些
    "head": (0, 0, 0),
    "head_a": 130,
    "strip": (0, 0, 0),
    "strip_a": 105,
    "alt": (255, 255, 255),         # 深色下隔行往白里提一点
    "alt_a": 22,
    "hover_a": 70,
    "press_rgb": (60, 68, 82),
    "ctrl": (255, 255, 255),        # 同浅色：白微透，只是现在能跟着主题改了
    "ctrl_a": 60,
    "line": (255, 255, 255),
    "line_a": 34,
    "sel": "rgba(92, 130, 174, 150)",     # 选中：柔和的蓝
    "sel_solid": (78, 104, 134),
    "sel_text": "#eef0f4",
    "handle": (210, 214, 220),
    "sb_trough": (255, 255, 255), "sb_trough_a": 18,
    "sb_handle": (255, 255, 255), "sb_handle_a": 88,
    "disabled": (110, 114, 120),
    "placeholder": (128, 132, 140),
    "title_fallback": (42, 42, 48),
    # 深色也要有这几个键 —— 少了 Backdrop 会取默认值，两层主题行为就不一致了
    "wash_max": 0.85,
    "soft": (18, 20, 24),           # 深色下柔化层往【黑】里压，不能往白
    "soft_a": 0.10,
    "row_line_a": 20,
}

# 暖纸浅色（色温 5800K）：同一套浅色，只是整体偏暖。
# 冷白在夜里看久了会觉得「冷硬」，暖纸是把底和字一起往黄里挪，不是加滤镜。
LIGHT_WARM = dict(LIGHT, **{
    "name": "暖纸",
    "text_presets": TEXT_PRESETS_WARM,
    "base": (234, 229, 219),        # 同珠光：深一档，无背景图时才有层次
    "wash": (248, 247, 243),
    "soft": (246, 244, 238),
    "text": (48, 44, 38),
    "dim": (118, 112, 104),
    "window": (245, 243, 239),
    "panel": (254, 253, 250),
    "head": (214, 209, 199),        # 同珠光：压到窗口底下面成一条横带
    "strip": (240, 237, 231),
    "alt": (222, 217, 206),         # 暖色隔行，与面板差 32 级
    "ctrl": (254, 253, 250),
    "press_rgb": (232, 228, 220),
    "line": (60, 50, 40),
    "sel": "rgba(160, 138, 110, 120)",
    "sel_solid": (175, 155, 130),
    "sel_text": "#221e1a",
    "handle": (150, 142, 130),
    "sb_handle_a": 65,
    "disabled": (155, 150, 142),
    "placeholder": (140, 135, 128),
    "title_fallback": (244, 239, 229),   # 同珠光：base 往上抬 10 级
})

# 雾灰：真中性灰，不带冷蓝偏
LIGHT_MIST = dict(LIGHT, **{
    "name": "雾灰",
    # 显式声明不用共享预设：它自己那套正文色比珠光深，套珠光的会被盖掉
    "text_presets": None,
    "base": (218, 218, 222),
    "wash": (244, 244, 246),
    "soft": (242, 242, 245),
    "text": (36, 41, 47),
    "dim": (100, 106, 114),
    "window": (240, 240, 243),
    "panel": (250, 250, 252),
    "head": (200, 200, 205),        # 同样压到 base 下面
    "strip": (228, 228, 232),
    "alt": (206, 206, 211),
    "ctrl": (248, 248, 250),
    "press_rgb": (218, 218, 224),
    "line": (0, 0, 0), "line_a": 32, "row_line_a": 16,
    "sel": "rgba(90, 110, 140, 130)",
    "sel_solid": (140, 158, 184),
    "sel_text": "#1c1f24",
    "disabled": (146, 150, 156),
    "placeholder": (128, 132, 138),
    "title_fallback": (228, 228, 232),
})

# 晨曦：极轻的玫瑰暖调
LIGHT_DAWN = dict(LIGHT, **{
    "name": "晨曦",
    "text_presets": TEXT_PRESETS_ROSE,
    "base": (234, 226, 228),
    "wash": (249, 246, 247),
    "soft": (247, 243, 244),
    "text": (52, 42, 46),
    "dim": (118, 106, 112),
    "window": (246, 241, 242),
    "panel": (254, 251, 252),
    "head": (214, 204, 208),        # 同样压到 base 下面
    "strip": (240, 233, 236),
    "alt": (224, 214, 218),
    "ctrl": (254, 251, 252),
    "press_rgb": (236, 224, 228),
    "line": (56, 40, 44), "line_a": 28, "row_line_a": 14,
    "sel": "rgba(170, 120, 140, 120)",
    "sel_solid": (188, 150, 168),
    "sel_text": "#241a1e",
    "disabled": (156, 148, 152),
    "placeholder": (140, 130, 136),
    "title_fallback": (244, 236, 238),
})

# 极夜：近纯黑，OLED 友好。面板压得很透，让背景图最大化透出来
DARK_POLAR = dict(DARK, **{
    "name": "极夜",
    "base": (8, 8, 10),
    "window": (14, 14, 17),
    "panel": (0, 0, 0), "panel_a": 60,
    "head": (0, 0, 0), "head_a": 90,
    "strip": (0, 0, 0), "strip_a": 70,
    "alt": (255, 255, 255), "alt_a": 16,
    "line": (255, 255, 255), "line_a": 26,   # 别降到 0：纯黑下没边框，面板会跟窗口融一起
    "soft": (0, 0, 0), "soft_a": 0.06,
    "title_fallback": (20, 20, 24),
})

# 熔岩：暖褐底，低蓝光
DARK_MAGMA = dict(DARK, **{
    "name": "熔岩",
    "base": (34, 28, 24),
    "text": (236, 226, 214),
    "dim": (170, 156, 140),
    "window": (40, 33, 28),
    "alt": (255, 240, 220), "alt_a": 24,     # 隔行用暖白提亮
    "press_rgb": (76, 60, 48),
    "ctrl": (255, 240, 220), "ctrl_a": 60,
    "line": (255, 220, 180), "line_a": 30,
    "sel": "rgba(190, 140, 90, 150)",
    "sel_solid": (160, 110, 70),
    "sel_text": "#f5e9d8",
    "handle": (220, 200, 176),
    "sb_trough": (255, 220, 180), "sb_trough_a": 18,
    "sb_handle": (255, 220, 180), "sb_handle_a": 80,
    "soft": (28, 22, 18), "soft_a": 0.10,
    "title_fallback": (50, 40, 32),
})

# 注册表。键就是存进配置的那个值 —— 以后加配色只需要在这里加一行，
# apply_theme 一个判断都不用改（深浅和正文色都写在各自字典里了）。
THEMES = {
    "pearl":    LIGHT,
    "warm":     LIGHT_WARM,
    "mist":     LIGHT_MIST,
    "dawn":     LIGHT_DAWN,
    "midnight": DARK,
    "polar":    DARK_POLAR,
    "magma":    DARK_MAGMA,
}
LIGHT_KEYS = ("pearl", "warm", "mist", "dawn")
DARK_KEYS = ("midnight", "polar", "magma")
DEFAULT_LIGHT = "pearl"
DEFAULT_DARK = "midnight"

THEME = dict(LIGHT)                 # 当前生效的那套（apply_theme 会改写它）


QSS_TMPL = """
QTableView {{
    color: {text};
    background-color: rgba({panel}, {panel_a});
    alternate-background-color: rgba({alt}, {alt_a});
    border: none;
    outline: none;
    font-size: 10pt;
    selection-background-color: {sel};
    selection-color: {sel_text};
}}
/* 主列表：底色不在这里画，改由 TableRowDelegate 逐行画。
   视口自己铺一层的话，隔行那层会【叠在它上面】而不是替代它，
   结果隔行比普通行更实、更白（量过：面板 alpha 160 时
   普通行 160 = 正好一层，隔行 191 = 两层）。
   只圈 #sessions，回收站那个小表格不受影响。 */
QTableView#sessions {{
    background-color: transparent;
    alternate-background-color: transparent;
}}
/* 关键：表头控件自身要透明。
   不写这条的话，section 的半透明色是叠在表头自己的不透明底上，
   结果就是一条死板的纯色带，图片完全透不出来。 */
QHeaderView {{
    background: transparent;
}}
QHeaderView::section {{
    color: {text};
    background-color: rgba({head}, {head_a});
    border: none;
    border-right: 1px solid {line};
    border-bottom: 1px solid {line};
    padding: 7px 8px;
    font-weight: bold;
}}
QLineEdit {{
    color: {text};
    background-color: rgba({ctrl}, {ctrl_a});
    border: 1px solid {line};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {sel};
    selection-color: {sel_text};
}}
/* 下拉：外观跟按钮一个路子。不写的话深色下弹出列表会是系统默认的白底黑字，
   跟整个界面不是一个世界。 */
QComboBox {{
    color: {text};
    background-color: rgba({ctrl}, {ctrl_a});
    border: 1px solid {line};
    border-radius: 6px;
    padding: 5px 10px;
}}
QComboBox:hover {{ background-color: rgba({ctrl}, {hover_a}); }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    color: {text};
    background-color: {window};
    border: 1px solid {line};
    selection-background-color: {sel};
    selection-color: {sel_text};
    outline: none;
}}
QPushButton {{
    color: {text};
    background-color: rgba({ctrl}, {ctrl_a});
    border: 1px solid {line};
    border-radius: 6px;
    padding: 6px 16px;
}}
QPushButton:hover   {{ background-color: rgba({ctrl}, {hover_a}); }}
QPushButton:pressed {{ background-color: {press}; }}
QPushButton:disabled {{ color: {disabled}; }}
QLabel {{ color: {text}; background: transparent; }}
/* 设置对话框的层次靠四样东西撑：
   #section 组标题（比正文大半档、加粗）、#hint 说明（压暗）、
   #divider 组间分割线、[muted=true] 不适用的数值。
   没有它们的话，一屏控件全是同样粗细同样颜色的字，看着就是一坨。 */
QLabel#section {{ color: {text}; font-size: 10.5pt; font-weight: bold; }}
QLabel#hint {{ color: {dim}; }}
/* 分割线用 background 画（控件本身 setFixedHeight(1)），不用 QFrame 自带的
   边框形状 —— 两个一起上会画成两像素。 */
QFrame#divider {{ background-color: rgba({line_rgb}, {line_a}); border: none; }}
QLabel[muted="true"] {{ color: {disabled}; }}
/* 详情栏和状态栏直接压在图片上会看不清，也垫一层和列表同色的底 */
QLabel#strip {{
    background-color: rgba({strip}, {strip_a});
    border: 1px solid {line};      /* 同样是个暗部锚点，不然后它跟背景糊在一起 */
    border-radius: 6px;
    padding: 6px 10px;
}}
/* 单选框和勾选框这里【故意什么都不写】。
   只要 QSS 里有规则指向它们，Qt 就用自己的样式渲染器接管整个控件，
   那时候控件的调色板就不起作用了 —— 而我们要靠调色板来控制
   「白底 + 深色标记」的颜色（见 fix_indicator_palette）。 */

QDialog {{ color: {text}; background-color: {window}; }}
QMessageBox {{ color: {text}; background-color: {window}; }}
QToolTip {{ color: {text}; background-color: {window}; border: 1px solid {line}; }}
/* 滚动条：轨道和滑块都用半透明色，跟着主题走。
   （注：之前撤销这套样式是误判 —— 当时拖起来不顺，真凶是横向滚动单位
   用了「按列」而不是「按像素」，跟样式无关。真凶修掉之后，样式可以加回来。）
   不写的话 Qt 自绘的轨道在浅色下会是死黑一条，很突兀。 */
QScrollBar:vertical {{
    background: rgba({sb_trough}, {sb_trough_a}); width: 13px; margin: 0;
}}
QScrollBar:horizontal {{
    background: rgba({sb_trough}, {sb_trough_a}); height: 13px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba({sb_handle}, {sb_handle_a});
    border-radius: 5px; min-height: 36px; margin: 3px;
}}
QScrollBar::handle:horizontal {{
    background: rgba({sb_handle}, {sb_handle_a});
    border-radius: 5px; min-width: 36px; margin: 3px;
}}
QScrollBar::handle:hover {{ background: rgba({sb_handle}, 200); }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
/* 滑杆不套自定义样式了 —— 自定义那个大滑块配亮蓝填充跟整体风格很违和。
   交给 Qt 自己画（Fusion 风格），中性、也最顺滑。 */
"""


def build_qss():
    t = THEME
    rgb = lambda k: "%d, %d, %d" % t[k]               # noqa: E731
    return QSS_TMPL.format(
        text="rgb(%s)" % rgb("text"),
        dim=rgb("dim"),
        window="rgb(%s)" % rgb("window"),
        panel=rgb("panel"), ctrl=rgb("ctrl"),       # 不再写死纯白，跟着主题走
        alt=rgb("alt"), alt_a=t["alt_a"],
        panel_a=t["panel_a"], ctrl_a=t["ctrl_a"], hover_a=t["hover_a"],
        head=rgb("head"), head_a=t["head_a"],
        strip=rgb("strip"), strip_a=t["strip_a"],
        sb_trough=rgb("sb_trough"), sb_trough_a=t["sb_trough_a"],
        sb_handle=rgb("sb_handle"), sb_handle_a=t["sb_handle_a"],
        line="rgba(%d, %d, %d, %d)" % (t["line"][0], t["line"][1], t["line"][2], t["line_a"]),
        line_rgb=rgb("line"), line_a=t["line_a"],
        press="rgb(%d, %d, %d)" % t["press_rgb"], handle="rgb(%s)" % rgb("handle"),
        sel=t["sel"], sel_text=t["sel_text"], disabled="rgb(%s)" % rgb("disabled"),
    )


def build_palette(dark=False):
    """锁一套调色板，弹窗（确认框、改名框、文件选择）才不会跟着系统变成另一种色调。

    dark 必须由调用方明说，不能拿 panel_a 猜 —— panel_a 现在是用户能拖的滑杆，
    猜法两头都会错：浅色拖到 100 以下被判成深色，深色默认 105 又被判成浅色，
    整块底色调色板直接反过来。（用户把面板拖到 76 时，浅色就吃过这个亏。）
    """
    t = THEME
    p = QPalette()
    p.setColor(QPalette.Window, QColor(*t["window"]))
    p.setColor(QPalette.WindowText, QColor(*t["text"]))
    p.setColor(QPalette.Base, QColor(38, 40, 46) if dark else QColor(255, 255, 255))
    p.setColor(QPalette.AlternateBase, QColor(*t["window"]))
    p.setColor(QPalette.Text, QColor(*t["text"]))
    p.setColor(QPalette.Button, QColor(*t["window"]))
    p.setColor(QPalette.ButtonText, QColor(*t["text"]))
    p.setColor(QPalette.ToolTipBase, QColor(*t["window"]))
    p.setColor(QPalette.ToolTipText, QColor(*t["text"]))
    p.setColor(QPalette.Highlight, QColor(*t["sel_solid"]))
    p.setColor(QPalette.HighlightedText, QColor(t["sel_text"]))
    p.setColor(QPalette.PlaceholderText, QColor(*t["placeholder"]))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(*t["disabled"]))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(*t["disabled"]))
    return p


_qt_tr = None                       # 当前装着的 Qt 自带翻译（切语言时要摘掉）


def default_lang():
    """头一次打开时按系统语言定：系统不是中文就用英文。

    默认值**不能写死中文**。这个工具是要发给别人用的，
    一个外国人第一眼看到的会是中文界面，而**切语言的那个按钮本身也是中文的**
    （「设置」）—— 他连入口都找不到，等于卡死。

    只在配置里没有 lang 时用（也就是第一次运行）；之后记住用户自己选的。
    """
    try:
        return "zh" if QLocale.system().name().lower().startswith("zh") else "en"
    except Exception:
        return "zh"


def install_qt_translator(app, lang):
    """让 Qt **自带**控件的文字也跟着界面语言走。

    管的是标准按钮那种 —— QMessageBox 的 Yes/No、QInputDialog 的 OK/Cancel。
    这些字不是我们的代码写的，是 Qt 内建的，不装翻译文件的话，
    中文界面里一弹确认框就是「Yes / No」，正文中文、按钮英文，很割裂。

    翻译文件是 PySide6 自带的（qtbase_zh_CN.qm），不用另外下载。
    英文不用装 —— 那是 Qt 的内置默认语言。
    """
    global _qt_tr
    if _qt_tr is not None:
        app.removeTranslator(_qt_tr)
        _qt_tr = None
    if lang != "zh":
        return
    tr = QTranslator(app)
    try:
        path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    except Exception:
        path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if tr.load("qtbase_zh_CN", path):
        app.installTranslator(tr)
        _qt_tr = tr


class TitleBarTinter(QObject):
    """给每个新冒出来的窗口自动染标题栏。

    以前只在「设置」和「回收站」的 showEvent 里各调一次，
    消息框、改名框那些就漏了 —— 它们的标题栏停在系统默认色上，
    深色主题下只是微差，**浅色主题下就是明晃晃的一条黑带**。

    挂成全局事件过滤器：谁的 Show 事件都过一遍，就不存在漏网的窗口了。
    """

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Show:
            try:
                if obj.isWindow() and isinstance(obj, (QMainWindow, QDialog)):
                    win = getattr(QApplication.instance(), "_win", None)
                    if win is not None:
                        win.tint_window(obj)
            except Exception:
                pass
        return False


def themed_title_bar(widget, src):
    """给弹窗也染上标题栏颜色，跟主窗口保持一致。

    只对主窗口调过 DWM 的话，弹窗（设置、回收站、改名框）会留一条系统默认色的标题栏，
    在深色界面里非常突兀。
    """
    try:
        rgb = core.title_bar_color(getattr(src, "bg_image", ""),
                                   dark=bool(THEME.get("dark"))) or THEME["title_fallback"]
        core.apply_title_bar(int(widget.winId()), rgb)
    except Exception:
        pass


def system_is_dark(app):
    """问系统现在是深色还是浅色。Qt 6.5+ 有现成接口，老版本靠窗口色明暗猜。"""
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return app.palette().color(QPalette.Window).lightness() < 128


def resolve_dark(app, pref):
    """pref 是 auto / light / dark。"""
    if pref == "dark":
        return True
    if pref == "light":
        return False
    return system_is_dark(app)


def fix_indicator_palette(widget):
    """单选框 / 勾选框：白底 + 深色标记，两套主题下都一样。

    为什么需要：Qt 在深色主题下会把选中标记画成【白色】，
    而那个圈/框本身也是白的 —— 白点落在白圈里，等于看不见。
    （实测过：标记颜色由 QPalette::Text 决定，底由 QPalette::Base 决定。）
    所以这两个值直接钉成浅色主题那套：白底、深字。
    标签文字的颜色由 QSS 的 color 管，不受这里影响。
    """
    pal = widget.palette()
    for grp in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        pal.setColor(grp, QPalette.Base, QColor(255, 255, 255))     # 圈/框：白
        pal.setColor(grp, QPalette.Text, QColor(*LIGHT["text"]))    # 点/勾：深
        # 标签文字另算 —— 深色主题下得是浅色，不然字看不见
        label = QColor(*THEME["text"])
        pal.setColor(grp, QPalette.WindowText, label)
        pal.setColor(grp, QPalette.ButtonText, label)
    widget.setPalette(pal)


def apply_theme(app, style=DEFAULT_LIGHT, panel_a=None, contrast="normal", soft_pct=None,
                full=True, has_image=True):
    """style 是配色键（THEMES 里那个），panel_a 是「面板不透明度」滑杆，
    contrast 是文字对比，soft_pct 是背景柔化百分比。

    深浅由配色自己声明（字典里的 "dark"），不靠外面传、也不靠主题名去猜 ——
    之前用 `theme_key.startswith("dark")` 判断，可那三个深色键一个都不以 dark 开头，
    那个条件永远为假。

    各层按【同比例】缩放 —— 表头比列表实、隔行比列表透，这些相对关系不会被打乱。
    panel_a 传 None 就用配色自带的那套默认值。

    full=False：只重算 THEME 再让该重画的控件重画。拖滑杆时走这条 ——
    它几毫秒就完事。真正的重活是下面那次 setStyleSheet：它会让【整棵控件树】
    重新解析样式、重新 polish，每动一格来一次，手感就是一顿一顿的。
    所以样式表合并到松手之后再做（见 _schedule_dim_apply）。
    """
    base_t = THEMES.get(style) or LIGHT
    dark = bool(base_t.get("dark"))
    THEME.clear()
    THEME.update(base_t)
    if not dark:
        # 深色不参与文字预设 —— 深色下正文本来就该是浅色。
        # 预设也写在配色字典里：以后加一套配色只要填个字，这里一行都不用改。
        presets = base_t.get("text_presets")
        if presets:
            THEME["text"] = presets.get(contrast, presets["normal"])
        else:
            # 没写明三档的配色，就把它自己的正文色当「标准」，另两档按亮度推。
            # 不这么兜的话，字典里辛苦写的 text 会被默认预设盖掉、白写。
            r, g, b = base_t["text"]
            shift = {"soft": 14, "normal": 0, "high": -8}.get(contrast, 0)
            THEME["text"] = tuple(min(255, max(0, c + shift)) for c in (r, g, b))
    if soft_pct is not None:
        # 背景图的固定柔化层，0 就是彻底关掉，让原图直接上来
        THEME["soft_a"] = max(0.0, min(0.30, float(soft_pct) / 100.0))
    # 面板不透明度管的是「背景透出来多少」。没设背景图时透出来的是个纯色底，
    # 调低它只会把面板也拽向那个底色 —— 层次全没了，而且没有好处。
    # 所以没图时直接不套用，用主题自带的值。（有图无图各自记住，切回去就恢复。）
    if panel_a is not None and has_image:
        a = max(0, min(255, int(panel_a)))
        k = a / float(max(1, base_t["panel_a"]))
        for key in ("head_a", "strip_a", "alt_a"):
            THEME[key] = max(0, min(255, int(round(base_t[key] * k))))
        THEME["panel_a"] = a
    if not full:
        # update() 只是标脏等下一帧重画，不碰样式、不碰调色板 —— 便宜。
        for w in app.allWidgets():
            w.update()
        return

    app.setPalette(build_palette(dark))
    app.setStyleSheet(build_qss())
    # 主题一切换，已经开着的窗口里的单选框/勾选框也要跟着钉回白底深标记
    for w in app.allWidgets():
        if isinstance(w, (QRadioButton, QCheckBox)):
            fix_indicator_palette(w)
        elif isinstance(w, QAbstractScrollArea):
            # 行底色是 delegate 画的，改主题/拖滑杆后不主动重画的话会留着旧色
            w.viewport().update()



# ———————————————— 底图 ————————————————

class Backdrop(QWidget):
    """把图片按窗口大小裁切铺满，再盖一层浅色 —— 界面就「浮」在它上面。

    字号、列宽这些全部交给 Qt，这里只管画背景。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.wash = core.BG_DIM
        self._cached = None
        self._cached_size = None

    def set_image(self, path):
        if path and os.path.exists(path):
            pm = QPixmap(path)
            self.pixmap = None if pm.isNull() else pm
        else:
            self.pixmap = None
        self._cached = None
        self._cached_size = None
        self.update()

    def set_wash(self, v):
        # 削峰：不管滑杆给到多少，都留一份背景漫反射，不让图被彻底洗平
        cap = THEME.get("wash_max", 0.85)
        self.wash = max(0.0, min(cap, float(v)))
        self.update()

    def _cover(self):
        """按「铺满、多出来的裁掉」缩放。尺寸没变就用上次的结果，别每帧重算。"""
        if not self.pixmap or self.pixmap.isNull():
            return None
        size = self.size()
        if self._cached is not None and self._cached_size == size:
            return self._cached
        pm = self.pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._cached, self._cached_size = pm, size
        return pm

    def paintEvent(self, _ev):
        # 没图时填「底」，有图时往「淡化色」里淡 —— 这两个是【不同的颜色】：
        #   底   = 浅灰（衬托白色面板）／深灰
        #   淡化 = 珠光白（浅色）／近黑（深色）
        # 之前浅色把「淡化」也往浅灰里洗，图片被洗成灰调，看着就是发闷的「糊」。
        base = QColor(*THEME["base"])
        wash_to = QColor(*THEME.get("wash", THEME["base"]))
        soft = QColor(*THEME.get("soft", THEME["base"]))
        soft_a = THEME.get("soft_a", 0.0)
        cap = THEME.get("wash_max", 0.85)

        p = QPainter(self)
        p.fillRect(self.rect(), base)
        pm = self._cover()
        if pm is None:
            return
        p.drawPixmap(-(pm.width() - self.width()) // 2,
                     -(pm.height() - self.height()) // 2, pm)

        # 1) 固定柔化层：滑杆在 0 时也生效，免得一张高对比的图直接冲上来
        if soft_a > 0:
            c = QColor(soft)
            c.setAlphaF(soft_a)
            p.fillRect(self.rect(), c)

        # 2) 用户的淡化层。这里【不能】直接用 self.wash 当 alpha：
        #    滑杆前中段的变化会被压缩掉，拖起来像只有高段有反应。
        #    先归一化再用 0.7 次幂（指数 < 1 放大低中段），最后乘回上限。
        #    （0.25 的位置：线性 0.25，用 1.8 次幂反而压到 0.08，那是反的。）
        if self.wash > 0 and cap > 0:
            norm = min(1.0, self.wash / cap)
            c = QColor(wash_to)
            c.setAlphaF((norm ** 0.7) * cap)
            p.fillRect(self.rect(), c)


# ———————————————— 数据模型 ————————————————

class SessionModel(QAbstractTableModel):
    HEADERS = ("名字", "文件夹", "最后活动", "条数")

    def __init__(self, pad=False):
        super().__init__()
        self.rows = []
        # 多出来的这一列是隐形的，专门吃掉表格右边的剩余宽度。
        # 有了它，你手动拖出来的四列宽度才能原样留住 ——
        # 不用把剩余宽度硬塞给某一列（那样一重开就把你拖的冲掉了）。
        self.pad = pad

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.HEADERS) + (1 if self.pad else 0)

    def sort(self, column, order=Qt.AscendingOrder):
        """按某一列排序。

        回收站那个表格直接拿这个模型排 —— 主表格走的是代理（SessionFilter），
        点表头调的是【代理】的 sort()，压根不经过这里。所以两边互不干扰。
        """
        keys = (lambda r: r["title"].lower(),
                lambda r: (r["cwd"] or "").lower(),
                lambda r: r["mtime"],
                lambda r: r["msgs"])
        if not (0 <= column < len(keys)):
            return
        self.layoutAboutToBeChanged.emit()
        try:
            self.rows.sort(key=keys[column], reverse=(order == Qt.DescendingOrder))
        except Exception:
            pass
        self.layoutChanged.emit()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal:
            return None
        if section >= len(self.HEADERS):
            return None                       # 隐形列：没有表头文字
        if role == Qt.DisplayRole:
            return T(self.HEADERS[section])
        if role == Qt.TextAlignmentRole:
            # 表头要贴着数据（文字左对齐、条数右对齐）——
            # Qt 默认是居中，宽列上会飘到中间去
            side = Qt.AlignRight if section == 3 else Qt.AlignLeft
            return int(side | Qt.AlignVCenter)
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.rows)):
            return None
        r = self.rows[index.row()]
        col = index.column()
        if col >= len(self.HEADERS):
            return None                       # 隐形列：不显示任何东西
        if role == Qt.DisplayRole:
            if col == 0:
                return ("✎ " if r["renamed"] else "") + r["title"]
            if col == 1:
                return core.short_dir(r["cwd"])
            if col == 2:
                if "_when_text" in r:        # 回收站要显示绝对日期，不是「几小时前」
                    return r["_when_text"]
                return core.rel_time(r["mtime"])
            return str(r["msgs"]) if r["msgs"] else "—"
        if role == SORT_ROLE:
            # 排序按原始值，不是按显示出来的文字 —— 否则「9 小时前」会排在「10 小时前」后面
            if col == 0:
                return r["title"].lower()
            if col == 1:
                return (r["cwd"] or "").lower()
            if col == 2:
                return r["mtime"]
            return r["msgs"]
        if role == Qt.ToolTipRole:
            bits = [r["title"]]
            if r["last_prompt"]:
                bits.append(T("最后问：") + r["last_prompt"])
            bits.append(T("目录 ") + (core.pretty_dir(r["cwd"]) or "?"))
            return "\n".join(bits)
        if role == Qt.TextAlignmentRole and col == 3:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None


class SessionFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.setSortRole(SORT_ROLE)
        self.key = ""

    def set_key(self, k):
        self.key = (k or "").strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if not self.key:
            return True
        src = self.sourceModel()
        if not (0 <= row < len(src.rows)):
            return False
        r = src.rows[row]
        return (self.key in r["title"].lower()
                or self.key in (r["cwd"] or "").lower()
                or self.key in (r["last_prompt"] or "").lower())


class TableRowDelegate(QStyledItemDelegate):
    """逐行铺底色 —— 每行【只铺一层】。

    为什么不用 QSS 的 background-color / alternate-background-color：
    Qt 是先铺视口的 background，再把 alternate-background 盖上去，
    隔行因此变成「panel 叠 alt」两层，比普通行更实更白。
    实测（洋红底探针）：面板 alpha 160 时普通行 160、隔行 191，
    而单层应该是 160。这里每行只 fillRect 一次，两种行才是同一个透法，
    只靠 RGB 明暗区分。整行一起随「面板不透明度」滑杆变，不会有半行不动。
    """

    def paint(self, painter, opt, index):
        view = opt.widget
        alt_on = bool(view and view.alternatingRowColors())
        if alt_on and index.row() % 2 and THEME.get("alt"):
            c = QColor(*THEME["alt"])
            c.setAlpha(THEME["alt_a"])
        else:
            c = QColor(*THEME["panel"])
            c.setAlpha(THEME["panel_a"])
        painter.fillRect(opt.rect, c)

        # 行分隔线。浅色下界面全是亮度接近的灰，缺暗部锚点就会「发蒙」；
        # 一条极淡的线足够给视线一个落点，又不至于变成表格线。
        # 颜色跟着主题的 line 走：浅色是黑、深色是白，不然深色下这条等于没画。
        row_line_a = THEME.get("row_line_a", 0)
        if row_line_a:
            painter.setPen(QPen(QColor(*THEME["line"], row_line_a)))
            painter.drawLine(opt.rect.bottomLeft(), opt.rect.bottomRight())

        super().paint(painter, opt, index)      # 文字、选中高亮照旧由 Qt 画


class SessionTable(QTableView):
    """主列表。除了让 delegate 逐行铺底，还得补上【最后一行下面那片空白】。

    QSS 把视口背景设成透明后，delegate 只管行内的矩形，
    行下面到窗口底之间那块就没人铺了 —— 会直接露出没垫过面板的原图，
    跟上面的行不是一个底色，很扎眼。
    """

    def paintEvent(self, ev):
        vp = self.viewport()
        model = self.model()
        n = model.rowCount() if model else 0
        used = self.rowViewportPosition(n - 1) + self.rowHeight(n - 1) if n else 0
        if used < vp.height():
            c = QColor(*THEME["panel"])
            c.setAlpha(THEME["panel_a"])
            p = QPainter(vp)
            p.fillRect(QRect(0, used, vp.width(), vp.height() - used), c)
            p.end()
        super().paintEvent(ev)


# ———————————————— 回收站 ————————————————

class TrashDialog(QDialog):
    def __init__(self, parent, on_change):
        super().__init__(parent)
        self.on_change = on_change
        self.items = []
        self.setWindowTitle(T("回收站 —— 已删除的对话"))
        self.resize(820, 480)

        lay = QVBoxLayout(self)
        tip = QLabel(T('这些对话已从列表中移除，在官方 /resume 中也无法看到。\n彻底删除的文件无法恢复。'))
        lay.addWidget(tip)

        self.table = QTableView()
        # pad=True：多出一列是【隐形】的，专门吃掉表格右边的剩余宽度。
        # 有它撑着，三列才能全部设成 Interactive（手动可拖）——
        # 之前靠把第 0 列设成 Stretch 去填满，而 **Stretch 列是拖不动的**：
        # 一松手就被重新拉伸回去，看着就是「拖着有问题」。
        self.model = SessionModel(pad=True)
        # 只有三列是真的。原来这里有第四项 ""，那列没有表头却会渲染出「—」，
        # 因为 pad 该由 SessionModel 的隐形列来当，不是拿一个空表头凑。
        self.model.HEADERS = (T("名字"), T("原文件夹"), T("删除时间"))
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 跟主列表一致：按像素滚，否则横向拖动条会一顿一顿的
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 340)
        self.table.setColumnWidth(1, 260)
        self.table.setColumnWidth(2, 150)
        self.table.verticalHeader().setVisible(False)
        self._slack_busy = False
        self._last_vp_w = None
        # 点表头排序。默认按「删除时间」倒序 —— 刚删的排最上面，
        # 跟回收站该有的顺序一致。
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(2, Qt.DescendingOrder)

        lay.addWidget(self.table)

        # 右键菜单。跟下面那排按钮同一批动作 —— 主表格有，这里也得有，
        # 不然从主列表点进来的人会以为这儿不能右键。
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)

        bar = QHBoxLayout()
        for text, fn in ((T("恢复"), self.do_restore), (T("彻底删除"), self.do_purge),
                         (T("清空回收站"), self.do_empty)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addStretch(1)
        close = QPushButton(T("关闭"))
        close.clicked.connect(self.accept)
        bar.addWidget(close)
        lay.addLayout(bar)

        self.reload()

    def showEvent(self, ev):
        super().showEvent(ev)
        themed_title_bar(self, self.parent())    # 标题栏跟主窗口一个色

    def _fill_slack(self):
        """把宽度的富余补给「名字」列 —— 表格始终正好铺满，不剩空也不溢出。

        跟主列表同一套（那边踩过的坑这儿一样会踩）：
          1. 只在视口【宽度】真的变了时才重算 —— 列宽一超视口就冒出横向滚动条，
             滚动条一出现视口【高度】变了、又触发一次 resize，跟着算就会来回抖。
          2. 延到下一轮事件循环再算（见 resizeEvent）—— 当场算布局还没更新，
             viewport().width() 拿到的是旧值。
        """
        if self._slack_busy:
            return
        vp = self.table.viewport().width()
        if vp < 20 or vp == self._last_vp_w:
            return
        self._last_vp_w = vp
        hh = self.table.horizontalHeader()
        used = sum(hh.sectionSize(i) for i in range(hh.count()))
        slack = vp - used - 2
        if slack == 0:
            return
        self._slack_busy = True
        try:
            hh.resizeSection(0, max(120, hh.sectionSize(0) + slack))
        finally:
            self._slack_busy = False

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        QTimer.singleShot(0, self._fill_slack)

    def reload(self):
        self.items = core.trash_entries()
        rows = []
        import time
        for it in self.items:
            rows.append({
                "title": (it.get("title") or it["id"][:8]) + (T("   （文件已不存在）") if it.get("_missing") else ""),
                "cwd": it.get("cwd") or "",
                "mtime": it.get("deleted_at", 0),
                "msgs": 0, "renamed": False, "last_prompt": "",
                "_raw": it,
            })
        self.model.set_rows(rows)
        for r in rows:
            r["_when_text"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["mtime"]))
        if self.on_change:
            self.on_change()

    def _picked(self):
        out = []
        for idx in self.table.selectionModel().selectedRows(0):
            if 0 <= idx.row() < len(self.model.rows):
                out.append(self.model.rows[idx.row()]["_raw"])
        return out

    def _menu(self, pos):
        """回收站的右键菜单。点空白处不动选中项，点行上则先选中那一行。"""
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            idx = self.table.indexAt(pos)
            if idx.isValid():
                self.table.selectRow(idx.row())
        if not self.table.selectionModel().selectedRows():
            return
        menu = QMenu(self)
        menu.addAction(T("恢复"), self.do_restore)
        menu.addAction(T("彻底删除"), self.do_purge)
        menu.addSeparator()          # 清空是整盘操作，跟上面两条不是一回事
        menu.addAction(T("清空回收站"), self.do_empty)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def do_restore(self):
        sel = self._picked()
        if not sel:
            QMessageBox.information(self, T("提示"), T("请先选择一项"))
            return
        bad = []
        for it in sel:
            ok, info = core.restore_entry(it)
            if not ok:
                bad.append(info)
        self.reload()
        if bad:
            QMessageBox.warning(self, T("部分对话未能恢复"), "\n".join(bad))

    def do_purge(self):
        sel = self._picked()
        if not sel:
            QMessageBox.information(self, T("提示"), T("请先选择一项"))
            return
        if QMessageBox.question(
                self, T("彻底删除"),
                T('这 %d 个对话的文件将被永久删除，无法恢复。\n确定继续吗？') % len(sel)) != QMessageBox.Yes:
            return
        for it in sel:
            core.purge_entry(it)
        self.reload()

    def do_empty(self):
        if not self.items:
            QMessageBox.information(self, T("提示"), T("回收站为空"))
            return
        if QMessageBox.question(
                self, T("清空回收站"),
                T('其中 %d 个对话的文件将被永久删除，无法恢复。\n确定继续吗？') % len(self.items)) != QMessageBox.Yes:
            return
        for it in list(self.items):
            core.purge_entry(it)
        self.reload()


# ———————————————— 背景设置 ————————————————

class LookDialog(QDialog):
    """设置：语言 / 主题 / 文字对比 / 面板透明度 / 背景图。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.win = parent
        self.setWindowTitle(T("设置"))
        self.setMinimumWidth(560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(0)

        # 表单里那些「控件名」标签先收起来，三组都建完之后统一列宽 ——
        # QFormLayout 是【每个表单各自】按自己的标签算列宽的，
        # 不统一的话「面板不透明度」那根滑杆会比「淡化」晚开始一截，跨组看就不齐了。
        self._labels = []

        outer.addWidget(self._section_header(T("常规")))
        outer.addLayout(self._build_general())
        outer.addSpacing(18)

        outer.addWidget(self._section_header(T("外观")))
        outer.addLayout(self._build_appearance())
        outer.addSpacing(18)

        outer.addWidget(self._section_header(T("背景图")))
        outer.addLayout(self._build_background())

        outer.addStretch(1)
        outer.addSpacing(14)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        b_close = QPushButton(T("关闭"))
        b_close.setMinimumHeight(FIELD_H)
        b_close.clicked.connect(self.accept)
        bottom.addWidget(b_close)
        outer.addLayout(bottom)

        fm = self.fontMetrics()
        w = max((fm.horizontalAdvance(lb.text()) for lb in self._labels), default=0)
        for lb in self._labels:
            lb.setMinimumWidth(w)

        # 三根滑杆要等长，数值标签就得一样宽 —— 而且必须【定死】不能只给最小值：
        # 英文里「almost fully transparent 0%」比「semi-transparent 59%」长一大截，
        # 用最小宽度的话，拖到低段标签一撑，滑杆当场缩短 —— 手感就是「越拖越短」。
        # 所以先量出所有可能出现的文字里最宽的那个，三个标签一起按它定宽。
        samples = [T("关闭"), T("暂不适用")]
        for _word in ("几乎全透明", "很透明", "半透明", "偏实", "接近实心"):
            samples.append("%s 100%%" % T(_word))
        val_w = max(fm.horizontalAdvance(x) for x in samples) + 6
        for lb in (self.panel_hint, self.dim_hint, self.soft_hint):
            lb.setFixedWidth(val_w)

    # ———————————————— 排版零件 ————————————————
    # 横排是这次排版的骨架：标签在 QFormLayout 的左列、控件在右列，
    # 标签列宽度**由 Qt 按当前语言里最长的标签自动算** —— 不写死。
    # （写死过一次 128px，英文的「Default workspace」实测要 204px，会被裁掉。）

    def _section_header(self, text):
        """组标题 + 贴着它的一条细分割线。"""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        lb = QLabel(text)
        lb.setObjectName("section")
        v.addWidget(lb)
        rule = QFrame()
        rule.setObjectName("divider")
        rule.setFixedHeight(1)          # 靠 QSS 的 background 画，不用 QFrame 自带的边框
        v.addWidget(rule)
        return w

    def _label(self, text):
        """控件名标签。收集起来是为了建完之后统一列宽（见 __init__）。

        **必须定高 30 并在内部垂直居中**：整行的对齐是「顶部对齐」，
        而标签的框正好跟控件一样高（30），两边各自居中 —— 文字就跟输入框对齐了。
        不这么做的话，QFormLayout 会拿【整行】（控件 + 下方说明）的高度去居中标签，
        说明在下面，标签就被顶到上面去了。
        """
        lb = QLabel(text)
        lb.setFixedHeight(FIELD_H)
        lb.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._labels.append(lb)
        return lb

    def _form(self):
        f = QFormLayout()
        f.setContentsMargins(0, 8, 0, 0)
        f.setHorizontalSpacing(12)
        f.setVerticalSpacing(6)
        f.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        f.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        return f

    @staticmethod
    def _hint(text):
        lb = QLabel(text)
        lb.setObjectName("hint")
        lb.setWordWrap(True)
        return lb

    def _field(self, widget, hint=None):
        """一个字段：控件 +（可选）它自己的说明。说明对齐字段列，不跟正文抢。"""
        w = QWidget()
        box = QVBoxLayout(w)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        box.addWidget(widget)
        if hint:
            box.addWidget(self._hint(hint))
        return w

    def _row(self, parts, hint=None):
        """一个字段里横排多个控件。

        parts 里：
          int            → 加一份拉伸空白（放末尾用）
          (控件, 份数)    → 让**这个控件**吃掉多余宽度
          控件            → 按自身大小放

        注意别把「让控件撑开」写成「控件后面加空白」—— 那样撑开的是空白，
        滑杆还是短短一根。这个错我照抄方案时犯过一次。
        """
        w = QWidget()
        box = QVBoxLayout(w)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for p in parts:
            if isinstance(p, int):
                row.addStretch(p)
            elif isinstance(p, tuple):
                row.addWidget(p[0], p[1])
            else:
                row.addWidget(p)
        box.addLayout(row)
        if hint:
            box.addWidget(self._hint(hint))
        return w

    # ———————————————— 三组 ————————————————

    def _build_general(self):
        f = self._form()

        # 语言 —— 它一变主窗口整体重建，这个对话框自己也会关掉
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumHeight(FIELD_H)
        self.lang_combo.addItem("中文", "zh")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCurrentIndex(1 if self.win.lang == "en" else 0)
        self.lang_combo.currentIndexChanged.connect(
            lambda i: self.win.set_lang(self.lang_combo.itemData(i)))
        f.addRow(self._label(T("语言")), self._field(self.lang_combo))

        # 默认工作区
        self.ws_edit = QLineEdit(self.win.workspace or "")
        self.ws_edit.setMinimumHeight(FIELD_H)
        self.ws_edit.setPlaceholderText(T("尚未设置 —— 点击右侧「选择…」，或直接粘贴路径"))
        self.ws_edit.editingFinished.connect(self._on_workspace_edited)
        b_ws = QPushButton(T("选择…"))
        b_ws.setMinimumHeight(FIELD_H)
        b_ws.clicked.connect(self._pick_workspace)
        f.addRow(self._label(T("默认工作区")), self._row([(self.ws_edit, 1), b_ws]))

        # 每次对话使用独立子目录 —— 复选框放字段列，跟上面的控件左边缘对齐
        self.sdir_box = QCheckBox(T("每次对话使用独立子目录"))
        self.sdir_box.setChecked(bool(self.win.per_session_dir))
        self.sdir_box.toggled.connect(self.win.set_per_session_dir)
        fix_indicator_palette(self.sdir_box)
        f.addRow("", self.sdir_box)
        return f

    def _build_appearance(self):
        f = self._form()

        # 主题 —— 深浅 + 该深浅下的配色，一个下拉装完。
        # 标签是「前缀 + 配色名」两个键拼的，别写死成整串
        # （写死的话英文查不到，八项会全变中文）
        self._combo_items = [("auto", None, T("跟随系统"))]
        for k in LIGHT_KEYS:
            self._combo_items.append(("light", k, T("浅色 · ") + T(THEMES[k]["name"])))
        for k in DARK_KEYS:
            self._combo_items.append(("dark", k, T("深色 · ") + T(THEMES[k]["name"])))
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumHeight(FIELD_H)
        for _, _, label in self._combo_items:
            self.theme_combo.addItem(label)
        self.theme_combo.setCurrentIndex(self._combo_index())
        self.theme_combo.currentIndexChanged.connect(self._pick_theme)
        f.addRow(self._label(T("主题")), self._field(self.theme_combo))

        # 文字对比 —— 必须自建 QButtonGroup：Qt 是按【父控件】自动分组的，
        # 不建组的话它会跟别的单选框并成一组互斥
        self._contrast_btns = {}
        self._contrast_group = QButtonGroup(self)
        crow = QWidget()
        crow.setMinimumHeight(FIELD_H)
        cr = QHBoxLayout(crow)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.setSpacing(20)
        for key, label in (("soft", T("柔和")), ("normal", T("标准")), ("high", T("高对比"))):
            b = QRadioButton(label)
            b.setChecked(self.win.contrast == key)
            b.toggled.connect(lambda on, k=key: on and self.win.set_contrast(k))
            fix_indicator_palette(b)
            cr.addWidget(b)
            self._contrast_group.addButton(b)
            self._contrast_btns[key] = b
        cr.addStretch(1)
        f.addRow(self._label(T("文字对比")), self._field(crow))

        # 面板不透明度
        default_a = THEMES[self.win._style_key()[0]]["panel_a"]
        cur_a = self.win.panel_alpha if self.win.panel_alpha is not None else default_a
        has_img = bool(self.win.bg_image)
        self.panel_slider = QSlider(Qt.Horizontal)
        self.panel_slider.setMinimumHeight(FIELD_H)
        self.panel_slider.setRange(0, 255)
        self.panel_slider.setValue(cur_a if has_img else default_a)
        self.panel_slider.setEnabled(has_img)
        self.panel_slider.valueChanged.connect(self._on_panel_alpha)
        self.panel_hint = QLabel("")
        self.panel_hint.setObjectName("hint")
        self.panel_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f.addRow(self._label(T("面板不透明度")), self._row([(self.panel_slider, 1), self.panel_hint]))
        self._refresh_panel_hint()

        # 隔行
        self.alt_box = QCheckBox(T("隔行深浅交替"))
        self.alt_box.setChecked(bool(self.win.alt_rows))
        self.alt_box.toggled.connect(self.win.set_alt_rows)
        fix_indicator_palette(self.alt_box)
        f.addRow("", self._field(self.alt_box))
        return f

    def _build_background(self):
        f = self._form()

        # 当前图片 —— 路径可能很长，让它换行，并且能选中复制
        self.cur = QLabel(self.win.bg_image or T("（当前未设置背景）"))
        self.cur.setObjectName("hint")
        self.cur.setWordWrap(True)
        self.cur.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow(self._label(T("当前图片")), self._field(self.cur))

        # 淡化 —— 上限跟着 wash_max 走，跟削峰值、跟存盘夹取必须是同一个数
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimumHeight(FIELD_H)
        self.slider.setRange(0, int(round(THEME.get("wash_max", 0.85) * 100)))
        self.slider.setValue(int(round(self.win.bg_dim * 100)))
        self.slider.valueChanged.connect(self._on_bg_dim)
        self.dim_hint = QLabel("")
        self.dim_hint.setObjectName("hint")
        self.dim_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f.addRow(self._label(T("淡化")), self._row([(self.slider, 1), self.dim_hint]))
        self._refresh_dim_hint()

        # 柔化 —— 跟「淡化」是两件事：那个是主动洗白，这个是防止高对比的图
        # 在淡化拉到 0 时直接冲上来。所以两根滑杆。
        self.soft_slider = QSlider(Qt.Horizontal)
        self.soft_slider.setMinimumHeight(FIELD_H)
        self.soft_slider.setRange(0, 30)
        # 没调过（None）就用当前主题的默认值，免得滑杆停在一个跟画面对不上的位置
        self.soft_slider.setValue(
            int(self.win.soft_pct) if self.win.soft_pct is not None
            else int(round(THEME.get("soft_a", 0.16) * 100)))
        self.soft_slider.valueChanged.connect(self._on_soft_pct)
        self.soft_hint = QLabel("")
        self.soft_hint.setObjectName("hint")
        self.soft_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f.addRow(self._label(T("柔化")), self._row([(self.soft_slider, 1), self.soft_hint]))
        self._refresh_soft_hint()

        # 操作按钮
        b1 = QPushButton(T("选择图片…"))
        b1.setMinimumHeight(FIELD_H)
        b1.clicked.connect(self.pick)
        b2 = QPushButton(T("移除背景"))
        b2.setMinimumHeight(FIELD_H)
        b2.clicked.connect(self.clear)
        f.addRow("", self._row([b1, b2, 1]))
        return f

    # ———————————————— 回调 ————————————————

    def _on_workspace_edited(self):
        self.win.set_workspace(self.ws_edit.text().strip())

    def _on_panel_alpha(self, v):
        self.win.set_panel_alpha(v)
        self._refresh_panel_hint()

    def _on_bg_dim(self, v):
        self.win.set_bg_dim(v / 100.0)
        self._refresh_dim_hint()

    def _on_soft_pct(self, v):
        self.win.set_soft_pct(v)
        self._refresh_soft_hint()

    # ———————————————— 数值标签 ————————————————
    # 五个档次的词随数值变，不写死。宽度靠 setMinimumWidth + 右对齐解决，
    # 右边形成一条竖直基准线。

    def _refresh_panel_hint(self):
        v = self.panel_slider.value()
        has_img = bool(self.win.bg_image)
        if not has_img:
            # 没背景图时这根滑杆本来就不生效（apply_theme 走另一条分支），
            # 那就别让数值看起来像是有意义的
            self.panel_hint.setText(T("暂不适用"))
            self.panel_hint.setProperty("muted", True)
        else:
            word = (T("几乎全透明") if v <= 30 else T("很透明") if v <= 90 else
                    T("半透明") if v <= 160 else T("偏实") if v <= 220 else
                    T("接近实心"))
            self.panel_hint.setText("%s %d%%" % (word, round(v / 255 * 100)))
            self.panel_hint.setProperty("muted", False)
        # 属性选择器要手动重刷才会生效
        self.panel_hint.style().unpolish(self.panel_hint)
        self.panel_hint.style().polish(self.panel_hint)

    def _refresh_dim_hint(self):
        v = self.slider.value()
        self.dim_hint.setText(T("关闭") if v == 0 else "%d%%" % v)

    def _refresh_soft_hint(self):
        v = self.soft_slider.value()
        self.soft_hint.setText(T("关闭") if v == 0 else "%d%%" % v)

    def _theme_meta(self):
        """当前选中项解码成 (pref, style)。"""
        return self._combo_items[self.theme_combo.currentIndex()][:2]

    def _combo_index(self):
        """按主窗口现在的状态，反查下拉该停在哪个选项上。"""
        p = self.win
        for i, (pref, style, _) in enumerate(self._combo_items):
            if pref == "auto" and p.theme_pref == "auto":
                return i
            if pref == "light" and p.theme_pref == "light" and p.style_light == style:
                return i
            if pref == "dark" and p.theme_pref == "dark" and p.style_dark == style:
                return i
        return 0

    def _pick_theme(self, idx):
        pref, style = self._combo_items[idx][:2]
        self.win.set_theme(pref, style)
        # 深浅一变，这一套滑杆/勾选就得换成另一套的值 —— 两套是独立的
        self._reload_mode_values()

    def _reload_mode_values(self):
        """按主窗口当前那套的值，把这几个控件重新摆一遍。"""
        p = self.win
        default_a = THEMES[p._style_key()[0]]["panel_a"]
        cur_a = p.panel_alpha if p.panel_alpha is not None else default_a
        self.panel_slider.setValue(cur_a if p.bg_image else default_a)
        self.slider.setValue(int(round(p.bg_dim * 100)))
        self.soft_slider.setValue(
            int(p.soft_pct) if p.soft_pct is not None
            else int(round(THEME.get("soft_a", 0.16) * 100)))
        self.alt_box.setChecked(bool(p.alt_rows))
        for k, b in self._contrast_btns.items():
            b.setChecked(p.contrast == k)
        # 滑杆位置变了，旁边的数值标签和「适不适用」也得跟着重算
        self._refresh_panel_hint()
        self._refresh_dim_hint()
        self._refresh_soft_hint()

    def showEvent(self, ev):
        super().showEvent(ev)
        themed_title_bar(self, self.win)      # 标题栏跟主窗口一个色

    def _pick_workspace(self):
        start = self.win.workspace if os.path.isdir(self.win.workspace or "") else ""
        p = QFileDialog.getExistingDirectory(self, T("选择默认工作区"), start)
        if not p:
            return
        self.ws_edit.setText(p)
        self.win.set_workspace(p)

    def pick(self):
        p, _ = QFileDialog.getOpenFileName(
            self, T("选择背景图"), "",
            T("图片 (*.jpg *.jpeg *.png *.gif *.bmp *.webp);;所有文件 (*)"))
        if not p:
            return
        self.win.set_background(p)
        self.cur.setText(p)
        # 有了背景图，面板不透明度这根滑杆才生效 —— 启用状态和数值都得重算
        self.panel_slider.setEnabled(True)
        self._refresh_panel_hint()

    def clear(self):
        self.win.set_background("")
        self.cur.setText(T("（当前未设置背景）"))
        self.panel_slider.setEnabled(False)
        self._refresh_panel_hint()


# ———————————————— 主窗口 ————————————————

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ★ 语言必须【第一个】定下来：文字都是在构造时一句句写进控件里的，
        #   晚一步设，先建好的那几个控件就会停在旧语言上（窗口标题中过这个招）。
        ui = core.read_ui()
        self.lang = ui.get("lang") or default_lang()     # zh / en
        i18n.set_lang(self.lang)

        self.setWindowTitle(T(core.APP_TITLE))
        self.resize(1220, 800)

        # 上次的窗口大小和位置（saveGeometry 连最大化状态一起记着）。
        # 没有存档就交给 main() 去居中。
        self._geo_restored = False
        ws = ui.get("win_state")
        if ws:
            try:
                self._geo_restored = self.restoreGeometry(QByteArray.fromBase64(ws.encode()))
            except Exception:
                self._geo_restored = False
        self.bg_image = ui.get("bg_image") or ""
        # 默认工作区：「新建对话」在这个目录里开新会话。
        # 没设过的话留空 —— 点按钮时再提示去设置，不擅自猜一个目录。
        self.workspace = ui.get("workspace") or ""
        # 新建对话时，每次单独建一个子目录放产出。默认开。
        self.per_session_dir = ui.get("per_session_dir", True)
        self.sessions = []
        self.format_suspect = False
        self._warned_format = False
        self._warned_no_claude = False       # 首次运行引导只弹一次
        self._header_timer = None
        self._trash_win = None
        self.theme_pref = ui.get("theme") or "auto"      # auto / light / dark
        # 配色键：浅色和深色各记一个 —— 浅色选了雾灰、深色选了熔岩，两边都记得
        # （老配置里的 warm 布尔值换算过来）
        legacy = "warm" if ui.get("warm") else DEFAULT_LIGHT
        self.style_light = ui.get("style_light") or legacy
        self.style_dark = ui.get("style_dark") or DEFAULT_DARK
        self._app = QApplication.instance()
        # 深浅两套界面设置各自独立存储（见 core.read_mode_ui）：
        # 面板不透明度 / 淡化 / 柔化 / 文字对比 / 隔行，这几项按【当前那一套】读，
        # 切深浅时整套换掉。只分深浅，不按珠光/暖纸那种配色分 ——
        # 配色是同一深浅下的变体，该共用；深浅才是两种不同的观感。
        self.mode = "dark" if resolve_dark(self._app, self.theme_pref) else "light"
        self._load_mode()
        self._slack_busy = False         # 补列宽时防止自己触发自己
        self._last_vp_w = None           # 上次补列宽时的视口宽度
        self._dim_timer = None           # 淡化滑杆的延迟合并

        self.backdrop = Backdrop()
        self.backdrop.set_wash(self.bg_dim)
        self.backdrop.set_image(self.bg_image)
        self.setCentralWidget(self.backdrop)

        lay = QVBoxLayout(self.backdrop)
        lay.setContentsMargins(22, 16, 22, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel(T("搜索")))
        self.search = QLineEdit()
        self.search.setPlaceholderText(T("搜索名字 / 文件夹 / 最后提问…（Ctrl+F）"))
        self.search.setClearButtonEnabled(True)
        top.addWidget(self.search, 1)
        b_refresh = QPushButton(T("刷新"))
        b_refresh.clicked.connect(self.reload)
        top.addWidget(b_refresh)
        lay.addLayout(top)

        self.model = SessionModel(pad=True)
        self.proxy = SessionFilter()
        self.proxy.setSourceModel(self.model)
        self.search.textChanged.connect(lambda t: (self.proxy.set_key(t),
                                                   self._refresh_status()))

        self.table = SessionTable()
        self.table.setObjectName("sessions")      # 给 QSS 圈定用：只有主列表铺透明底
        self.table.setItemDelegate(TableRowDelegate(self.table))
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setAlternatingRowColors(bool(self.alt_rows))   # 在「设置」里可关
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.doubleClicked.connect(self._on_double)
        self.table.selectionModel().selectionChanged.connect(lambda *_: self._on_selection())

        # 右键菜单。跟底部那排按钮是同一批动作 —— 鼠标已经在某一行上了，
        # 不用再跑到窗口底部去点。
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_menu)

        # 横向改成【按像素】滚动。
        # Qt 默认是按「列」滚（ScrollPerItem）：滚一格跳一整列、拖滑块会一格一格吸附，
        # 手感就是一跳一跳的。列那么宽，跳一格就是几百像素。
        # 纵向保持按「行」滚 —— 那个刚好合手，而且能对齐行。
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        # Qt 每次重排都会自己把步长算回去（算出来 170 多），滚一格跳太远。
        # 挂在 rangeChanged 上，它改一次我就钉回 50 像素。
        self.table.horizontalScrollBar().rangeChanged.connect(self._tune_hbar)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setSectionsMovable(True)
        hh.sectionResized.connect(lambda *_: self._schedule_save_header())
        restored = False
        st = ui.get("header_state")
        if st:
            try:
                restored = hh.restoreState(QByteArray.fromBase64(st.encode()))
            except Exception:
                restored = False
        if not restored:
            for i, w in enumerate((520, 300, 170, 90)):
                self.table.setColumnWidth(i, w)
        # 剩余宽度全给最后那条隐形列 —— 你拖的四列一个像素都不用动。
        # 必须在 restoreState 之后再设，否则会被存档里的列宽模式覆盖掉。
        hh.setStretchLastSection(True)
        lay.addWidget(self.table, 1)

        self.detail = QLabel("")
        self.detail.setObjectName("strip")
        self.detail.setWordWrap(True)
        lay.addWidget(self.detail)

        bar = QHBoxLayout()
        # 「新建对话」不依赖选中哪一行，用它的是「我要开个新活」——
        # 跟右边的行操作不是一回事，所以单独隔开。
        self.new_btn = QPushButton(T("新建对话"))
        self.new_btn.clicked.connect(self.do_new_session)
        self._refresh_new_btn()
        bar.addWidget(self.new_btn)
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        bar.addWidget(sep)
        for text, fn in ((T("接着聊"), self.do_resume), (T("改名"), self.do_rename),
                         (T("删除"), self.do_delete), (T("复制命令"), self.do_copy),
                         (T("打开目录"), self.do_open_folder),
                         (T("迁移工作区"), self.do_migrate)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addStretch(1)
        b_bg = QPushButton(T("设置"))
        b_bg.clicked.connect(lambda: LookDialog(self).exec())
        bar.addWidget(b_bg)
        self.trash_btn = QPushButton(T("回收站"))
        self.trash_btn.clicked.connect(self.open_trash)
        bar.addWidget(self.trash_btn)
        lay.addLayout(bar)

        self.status = QLabel("")
        self.status.setObjectName("strip")
        self.status.setAlignment(Qt.AlignRight)
        lay.addWidget(self.status)

        # Delete / F2 / 回车 绑在表格上（WidgetShortcut）：
        # 焦点在搜索框里时按 Delete 删的是文字，不会误删对话
        for keys, fn in (("Delete", self.do_delete), ("F2", self.do_rename),
                         ("Return", self.do_resume)):
            sc = QShortcut(QKeySequence(keys), self.table)
            sc.setContext(Qt.WidgetShortcut)
            sc.activated.connect(fn)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.search.setFocus())
        QShortcut(QKeySequence("Escape"), self, activated=lambda: self.search.clear())
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self.do_copy)

        self.reload()
        self.table.sortByColumn(SORTER_COL, Qt.DescendingOrder)

    # —— 数据 ——
    def reload(self):
        self.status.setText(T("正在读取记录…"))
        QApplication.processEvents()
        try:
            self.sessions = core.load_sessions()
        except Exception:
            self.sessions = []
            QMessageBox.critical(self, T("读取记录出错"), traceback.format_exc())
        self.model.set_rows(self.sessions)
        self._check_format()
        self._refresh_status()
        self._on_selection()

    def _check_format(self):
        blind = sum(1 for r in self.sessions if r.get("no_title"))
        self.format_suspect = bool(
            self.sessions and blind >= 3 and blind * 2 >= len(self.sessions))
        if self._warned_format or not self.format_suspect:
            return
        self._warned_format = True
        QMessageBox.warning(
            self, T("无法读取对话名称"),
            T('%d 个对话无法读取标题（占多数），列表中仅显示编号。\n\n通常是因为 Claude Code 更改了记录文件格式，本工具需要相应更新。\n\n这些对话本身未受影响：文件内容未被修改，只是无法显示标题。') % blind)

    def _refresh_status(self):
        total_mb = sum(r["size"] for r in self.sessions) / 1048576.0
        n = len(self.model.rows)
        extra = (T("  ·  筛出 %d 个") % n) if n != len(self.sessions) else ""
        if self.format_suspect:
            extra += T("  ·  %d 个无法读取标题") % sum(
                1 for r in self.sessions if r.get("no_title"))
        try:
            n_trash = len(core.trash_entries())
        except Exception:
            n_trash = 0
        self.trash_btn.setText(T("回收站 (%d)") % n_trash if n_trash else T("回收站"))
        self.status.setText(T("共 %d 个对话 · %.0f MB%s") % (len(self.sessions), total_mb, extra))

    def selected(self):
        out = []
        for idx in self.table.selectionModel().selectedRows(0):
            src = self.proxy.mapToSource(idx)
            if 0 <= src.row() < len(self.model.rows):
                out.append(self.model.rows[src.row()])
        return out

    def _on_selection(self):
        rows = self.selected()
        if not rows:
            self.detail.setText(T('双击行：接着聊\u3000·\u3000F2：改名\u3000·\u3000Delete：删除\u3000·\u3000Ctrl / Shift 点击：多选\u3000·\u3000点击表头：排序'))
        elif len(rows) > 1:
            self.detail.setText(T("已选中 %d 个对话。「删除」将一次全部移入回收站（会先询问），「复制命令」每行输出一条。") % len(rows))
        else:
            r = rows[0]
            head = (T("最后问： ") + r["last_prompt"] + "\n") if r["last_prompt"] else ""
            self.detail.setText(head + "　".join(filter(None, [
                T("目录 ") + (core.pretty_dir(r["cwd"]) or "?"),
                (T("分支 ") + r["branch"]) if r["branch"] else "",
                T("改过名") if r["renamed"] else "",
                r["id"][:8],
            ])))

    def _tune_hbar(self, *_):
        """横向滚轮步长钉成 50 像素 —— Qt 每次重排都会自己算回去，所以挂在这儿。"""
        bar = self.table.horizontalScrollBar()
        if bar.singleStep() != 50:
            bar.setSingleStep(50)

    def _fill_slack(self):
        """把宽度的富余（或不足）补给「名字」列 —— 表格始终正好铺满，不剩空也不溢出。

        两条保护，都是踩坑踩出来的：

        1. **只在视口「宽度」真的变了时才重算。**
           列宽一超出视口就冒出横向滚动条，滚动条一出现，视口【高度】变了、
           又触发一次 resize；要是这里跟着算，就会「缩回 → 滚动条消失 → 又撑开」来回抖 ——
           表现就是横向滚动条拖起来一顿一顿的。横向滚动条只改高度，所以这条能挡住它。
        2. **延到下一轮事件循环再算**（见 resizeEvent）。
           当场算的话布局还没更新，viewport().width() 拿到的是旧值。
        """
        if self._slack_busy:
            return
        vp = self.table.viewport().width()
        if vp < 20 or vp == self._last_vp_w:
            return
        self._last_vp_w = vp
        hh = self.table.horizontalHeader()
        used = sum(hh.sectionSize(i) for i in range(hh.count()))
        slack = vp - used - 2
        if slack == 0:
            return
        self._slack_busy = True
        try:
            hh.resizeSection(0, max(120, hh.sectionSize(0) + slack))
        finally:
            self._slack_busy = False

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # 延到下一轮事件循环再算：resizeEvent 当场算的话布局还没更新，
        # viewport().width() 拿到的是旧值，算出来的余量是错的
        QTimer.singleShot(0, self._fill_slack)

    def _on_double(self, index):
        src = self.proxy.mapToSource(index)
        if 0 <= src.row() < len(self.model.rows):
            self.do_resume(self.model.rows[src.row()])

    def _table_menu(self, pos):
        """右键菜单。点空白处不动选中项，点行上则先选中那一行。"""
        if not self.selected():
            idx = self.table.indexAt(pos)
            if idx.isValid():
                self.table.selectRow(idx.row())
        if not self.selected():
            return
        menu = QMenu(self)
        for text, fn in ((T("接着聊"), self.do_resume), (T("改名"), self.do_rename),
                         (T("复制命令"), self.do_copy),
                         (T("打开目录"), self.do_open_folder)):
            menu.addAction(text, fn)
        menu.addSeparator()          # 下面两条是破坏性的，隔开
        for text, fn in ((T("迁移工作区"), self.do_migrate),
                         (T("删除"), self.do_delete)):
            menu.addAction(text, fn)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # —— 动作 ——
    def do_resume(self, rec=None, *_):
        if self.search.hasFocus():
            return
        rows = self.selected()
        rec = rec or (rows[0] if rows else None)
        if not rec:
            QMessageBox.information(self, T("提示"), T("请先选择一个对话"))
            return
        ok, info = core.resume_session(rec)
        if ok:
            self.status.setText(T("已在新窗口打开（目录 %s）") % core.pretty_dir(info))
        else:
            QMessageBox.critical(self, T("无法打开"), info)

    def do_copy(self):
        rows = self.selected()
        if not rows:
            return
        QApplication.clipboard().setText(
            "\n".join("claude --resume " + r["id"] for r in rows))
        if len(rows) > 1:
            self.status.setText(T("已复制 %d 条命令（每行一条）") % len(rows))
        else:
            self.status.setText(T("已复制：claude --resume ") + rows[0]["id"])

    def do_new_session(self):
        """在默认工作区开一个新的 Claude Code 对话。

        做综合性活儿（整理文件、写 skill）时，多数时候不是要「接着聊」某个旧对话，
        而是要在一个固定目录开个新的 —— 这个按钮就是给那种场景的。
        """
        ws = (self.workspace or "").strip()
        if not ws:
            QMessageBox.information(
                self, T("尚未设置默认工作区"),
                T('请在「设置」中选择一个目录。'))
            return
        if not os.path.isdir(ws):
            QMessageBox.warning(
                self, T("目录不存在"),
                T('找不到默认工作区：\n\n%s\n\n请在「设置」中重新选择。') % ws)
            return
        sub = self._make_session_dir(ws) if self.per_session_dir else ""
        if sub:
            # 提示词必须【全 ASCII 且不带引号】—— 它要穿过 cmd.exe，
            # 中文可能被终端代码页搞乱，引号会被 cmd 的解析吃掉
            cmd = 'claude "%s"' % (SESSION_DIR_PROMPT % sub)
        else:
            cmd = "claude"
        ok, info = core.open_terminal(ws, cmd)
        if ok:
            # 把目录显示出来 —— 用户反馈过「有时候不知道为什么不在桌面」，
            # 那就每次开完都明说一句开在哪儿了
            if sub:
                self.status.setText(T("已在新窗口新建对话（目录 %s，产出目录 %s/）") % (ws, sub))
            else:
                self.status.setText(T("已在新窗口新建对话（目录 %s）") % ws)
        else:
            QMessageBox.critical(self, T("无法打开"), info)

    def _make_session_dir(self, ws):
        """给这一次会话在工作区下建一个独立子目录，返回目录名（不含工作区路径）。

        名字用时间戳：**纯 ASCII**（要穿过 cmd），而且按名字排序就是按时间排。

        为什么是「建出来」而不是「让 Claude 自己建」：建出来名字才保证唯一，
        同一分钟内开两个会话时能自动错开（-2、-3）。
        """
        base = time.strftime("%Y-%m-%d_%H%M")
        for suffix in ("", "-2", "-3", "-4", "-5"):
            name = base + suffix
            path = os.path.join(ws, name)
            if os.path.exists(path):
                continue
            try:
                os.makedirs(path)
            except Exception:
                # 建不出来也让流程走下去 —— 提示词照样把名字告诉 Claude，
                # 它自己会建。总比因为一个目录名把「新建对话」整个卡住好。
                pass
            return name
        return ""

    def do_open_folder(self):
        """用资源管理器打开选中对话的工作目录。"""
        rows = self.selected()
        if not rows:
            QMessageBox.information(self, T("提示"), T("请先选择一个对话"))
            return
        cwd = rows[0]["cwd"]
        if not (cwd and os.path.isdir(cwd)):
            QMessageBox.warning(
                self, T("目录不存在"),
                T('找不到此对话的目录：\n\n%s') % (cwd or T("（无记录）")))
            return
        # 先开，开成功了再报「已打开」。原顺序是反的 ——
        # open_folder 失败时状态栏照样说「已在新窗口打开」，那是在骗人。
        if not core.open_folder(cwd):
            QMessageBox.warning(self, T("无法打开"),
                                T('打不开这个目录：\n\n%s') % cwd)
            return
        if len(rows) > 1:
            self.status.setText(T("已选择 %d 个，打开第一个的目录：%s") % (len(rows), cwd))
        else:
            self.status.setText(T("已在新窗口打开（目录 %s）") % cwd)

    def do_migrate(self):
        """把选中对话的工作区改到别的目录。

        这是个动【对话数据本身】的操作（改写文件内容 + 挪文件位置），
        所以每一步都留退路：先备份、失败不动原文件、开着的不让迁。
        """
        rows = self.selected()
        if not rows:
            QMessageBox.information(self, T("提示"), T("请先选择一个对话"))
            return

        live = core.live_session_ids()
        busy = [r for r in rows if r["id"] in live]
        if busy:
            QMessageBox.warning(
                self, T("有对话正在使用中"),
                T("以下对话正在使用中，请先关闭再迁移：\n\n%s")
                % "\n".join("· " + r["title"] for r in busy[:8]))
            return

        start = rows[0]["cwd"] if os.path.isdir(rows[0]["cwd"] or "") else self.workspace
        target = QFileDialog.getExistingDirectory(self, T("选择新的工作区"), start or "")
        if not target:
            return
        target = target.rstrip("\\/")

        def norm(p):
            return os.path.normcase((p or "").rstrip("\\/"))

        todo = [r for r in rows if norm(r["cwd"]) != norm(target)]
        if not todo:
            QMessageBox.information(self, T("提示"), T("所选对话已在此工作区中"))
            return

        names = "\n".join("· " + r["title"] for r in todo[:8])
        if len(todo) > 8:
            names += T("\n… 还有 %d 个") % (len(todo) - 8)
        if QMessageBox.question(
                self, T("迁移工作区"),
                T("将以下 %d 个对话的工作区改为：\n\n%s\n\n%s\n\n"
                  "将改写对话文件中记录的路径，并把文件移至新目录对应的项目文件夹。\n"
                  "原文件会先完整备份到配置目录的 migrate_backup/ 下。") % (len(todo), target, names)
        ) != QMessageBox.Yes:
            return

        done, fails = 0, []
        for r in todo:
            ok, info = core.migrate_session(r, target)
            if ok:
                done += 1
            else:
                fails.append("%s：%s" % (r["title"], info))

        self.reload()
        if fails:
            QMessageBox.warning(self, T("部分对话迁移失败"), "\n".join(fails[:10]))
            self.status.setText(T("迁移完成 %d 个，失败 %d 个") % (done, len(fails)))
        elif done:
            self.status.setText(T("已迁移 %d 个对话到 %s") % (done, target))
        else:
            self.status.setText(T("没有对话被迁移"))

    def do_rename(self):
        rows = self.selected()
        if not rows:
            QMessageBox.information(self, T("提示"), T("请先选择一个对话"))
            return
        r = rows[0]
        new, ok = QInputDialog.getText(self, T("改名"), T("新名字："), text=r["title"])
        if not ok:
            return
        new = new.strip()
        if not new:
            QMessageBox.information(self, T("提示"), T("名字不能为空"))
            return
        try:
            core.rename_session(r, new)
        except Exception as e:
            QMessageBox.critical(self, T("改名失败"), str(e))
            return
        r["title"] = new
        r["renamed"] = True
        r["mtime"] = os.stat(r["file"]).st_mtime
        self.model.layoutChanged.emit()
        self._on_selection()
        self.status.setText(T("已重命名 —— 官方 /resume 中也会显示新名称"))

    def do_delete(self):
        rows = self.selected()
        if not rows:
            QMessageBox.information(self, T("提示"), T("请先选择一个对话"))
            return
        if len(rows) == 1:
            msg = (T('将这个对话移入回收站？\n\n%s\n\n（在官方 /resume 中也将不可见；如需撤销，可在回收站中恢复）') % rows[0]["title"])
        else:
            listing = "\n".join("· " + r["title"] for r in rows[:8])
            if len(rows) > 8:
                listing += T("\n… 还有 %d 个") % (len(rows) - 8)
            msg = (T('将这 %d 个对话移入回收站？\n\n%s\n\n（在官方 /resume 中也将不可见；如需撤销，可在回收站中恢复）') % (len(rows), listing))
        if QMessageBox.question(self, T("删除"), msg) != QMessageBox.Yes:
            return
        done, failed, gone = 0, [], set()
        for r in rows:
            try:
                core.soft_delete(r)
                gone.add(r["id"])
                done += 1
            except Exception as e:
                failed.append("%s：%s" % (r["title"], e))
        self.sessions = [x for x in self.sessions if x["id"] not in gone]
        self.model.set_rows(self.sessions)
        self._on_selection()
        self._refresh_status()
        if failed:
            QMessageBox.warning(self, T("有 %d 个未能删除") % len(failed), "\n".join(failed))
        self.status.setText(T("已将 %d 个对话移入回收站") % done if done > 1 else T("已移入回收站"))

    def open_trash(self):
        if self._trash_win is None:
            self._trash_win = TrashDialog(self, on_change=self._refresh_status)
        self._trash_win.reload()
        self._trash_win.show()
        self._trash_win.raise_()

    # —— 主题 ——
    def set_theme(self, pref, style=None):
        """pref: auto / light / dark；style 是配色键（THEMES 里那个）。

        主题那个下拉给的是 (pref, style) 一整对，所以点一下就是完整状态。
        style 只写进它对应的那一侧 —— 选浅色的配色不会把深色的也改掉。
        """
        self.theme_pref = pref
        if pref == "dark":
            self.style_dark = style or self.style_dark
        elif pref == "light":
            self.style_light = style or self.style_light
        core.write_ui(theme=pref, style_light=self.style_light,
                      style_dark=self.style_dark)
        self._apply_theme_now()

    def set_lang(self, code):
        """换语言。

        文字是构造时一句句写进控件里的，Qt 没有「全部重新翻译一遍」的现成通道，
        要挨个控件重设一遍既啰嗦又容易漏。所以直接**把整个窗口重建一个** ——
        重建后所有文字自然都是新语言的，一条都不会漏。
        代价是「设置」对话框会跟着关掉（它是旧窗口的孩子）。
        """
        if code == self.lang:
            return
        self.lang = code
        i18n.set_lang(code)
        install_qt_translator(self._app, code)      # Qt 自带控件的按钮文字也得跟着换
        core.write_ui(lang=code)
        QTimer.singleShot(0, self._rebuild)     # 让当前这次信号先走完再动窗口

    def _rebuild(self):
        app = self._app
        geo = self.saveGeometry()
        new = MainWindow()
        new.restoreGeometry(geo)                # 位置/大小/最大化状态原样接过去
        new.show()
        if app is not None:
            app._win = new                      # 挂住引用，否则新窗口会被回收
        self.close()
        self.deleteLater()

    def _style_key(self, dark=None):
        """这一帧该用哪套配色。深浅由 theme_pref 定（可能是跟随系统）。"""
        if dark is None:
            dark = resolve_dark(self._app, self.theme_pref)
        return (self.style_dark if dark else self.style_light), dark

    # —— 深浅两套界面设置 ——
    def _load_mode(self):
        """把当前这一套（浅或深）的设置读进内存。"""
        m = core.read_mode_ui(self.mode)
        self.panel_alpha = m.get("panel_alpha")     # None = 用主题默认
        cap = (DARK if self.mode == "dark" else LIGHT)["wash_max"]
        try:
            # 旧配置里可能存着超过上限的值，不夹一下滑杆会和画面对不上
            self.bg_dim = min(cap, max(0.0, float(m.get("bg_dim", core.BG_DIM))))
        except Exception:
            self.bg_dim = core.BG_DIM
        self.soft_pct = m.get("soft_pct")           # None = 用主题默认
        self.contrast = m.get("contrast") or "normal"
        self.alt_rows = bool(m.get("alt_rows", True))

    def _save_mode(self):
        """把这套的当前值写回它自己那一桶，另一桶不动。"""
        core.write_mode_ui(self.mode, panel_alpha=self.panel_alpha, bg_dim=self.bg_dim,
                           soft_pct=self.soft_pct, contrast=self.contrast,
                           alt_rows=self.alt_rows)

    def _sync_mode_widgets(self):
        """切了模式之后，把新那套的值同步到控件上。"""
        self.backdrop.set_wash(self.bg_dim)
        self.table.setAlternatingRowColors(self.alt_rows)

    def _switch_mode(self, mode):
        """深浅一变就整套换：先把旧的存回去，再把新的读出来。返回是否真的换了。"""
        if mode == self.mode:
            return False
        self._save_mode()
        self.mode = mode
        self._load_mode()
        return True

    def _apply_theme_core(self, full):
        if self._app is None:
            return
        dark = resolve_dark(self._app, self.theme_pref)
        if self._switch_mode("dark" if dark else "light"):
            self._sync_mode_widgets()
        style, dark = self._style_key(dark)
        apply_theme(self._app, style, self.panel_alpha,
                    contrast=self.contrast, soft_pct=self.soft_pct,
                    full=full, has_image=bool(self.bg_image))
        self.backdrop.update()

    def _apply_theme_now(self):
        """完整应用：重算 THEME + 调色板 + 样式表 + 标题栏。主题切换走这条。"""
        self._apply_theme_core(True)
        self._apply_titlebar()

    def _apply_theme_fast(self):
        """拖滑杆用：只重算 THEME 并重画。样式表那步留给 _apply_dim_now。"""
        self._apply_theme_core(False)

    def set_alt_rows(self, on):
        """隔行深浅交替，开关随时切、会记住。"""
        self.alt_rows = bool(on)
        self._save_mode()
        self.table.setAlternatingRowColors(self.alt_rows)

    def on_system_scheme_changed(self):
        """系统主题变了 —— 只有选了「跟随系统」才跟着动。"""
        if self.theme_pref == "auto":
            self._apply_theme_now()

    # —— 背景 ——
    def set_workspace(self, path):
        """设默认工作区。「新建对话」就在这儿开新会话。"""
        self.workspace = (path or "").strip()
        core.write_ui(workspace=self.workspace)
        self._refresh_new_btn()

    def set_per_session_dir(self, on):
        """开关：新建对话时要不要给它单独建一个子目录放产出。"""
        self.per_session_dir = bool(on)
        core.write_ui(per_session_dir=self.per_session_dir)
        self._refresh_new_btn()

    def _refresh_new_btn(self):
        """按钮上带出当前工作区 —— 免得每次点之前都不知道会开到哪去。"""
        try:
            ws = self.workspace or ""
            if ws:
                # 按钮上只放【最后一级目录名】—— 放完整路径的话这一个按钮就 374px，
                # 加上旁边七个按钮正好把整条压到零余量，路径稍长就截断。
                # 完整路径在悬停提示里，开完状态栏也会说一遍。
                short = os.path.basename(ws.rstrip("\\/")) or ws
                if len(short) > 10:
                    short = short[:10] + "…"       # 再长的目录名会把整条按钮栏挤爆
                tip = T("在 %s 中新建一个 Claude Code 对话") % ws
                if self.per_session_dir:
                    tip += "\n" + T("并为它建立一个独立的产出子目录（以时间戳命名）")
                self.new_btn.setToolTip(tip)
                self.new_btn.setText(T("新建对话") + "  ·  " + short)
            else:
                self.new_btn.setToolTip(T("尚未设置默认工作区 —— 请在「设置」中选择"))
                self.new_btn.setText(T("新建对话"))
        except Exception:
            pass

    def set_background(self, path):
        self.bg_image = path or ""
        core.write_ui(bg_image=self.bg_image)
        self.backdrop.set_image(self.bg_image)
        # 有图/无图会走 apply_theme 的不同分支（无图时不套面板不透明度），
        # 所以加图和去图都必须重新应用一次主题，不然层次还是上一套的
        self._apply_theme_now()
        self._apply_titlebar()

    def set_bg_dim(self, v):
        # 上限跟滑杆、跟 set_wash 用同一个 wash_max，三处不许各写各的
        cap = THEME.get("wash_max", 0.85)
        self.bg_dim = max(0.0, min(cap, round(float(v), 3)))
        # 拖动时只重绘 —— 这一步最便宜，画面能跟手。
        # 写配置、重建样式表都是重活，合并到停手之后再做（见 _apply_dim_now）。
        self.backdrop.set_wash(self.bg_dim)
        self._schedule_dim_apply()

    def _schedule_dim_apply(self):
        if self._dim_timer is None:
            self._dim_timer = QTimer(self)
            self._dim_timer.setSingleShot(True)
            self._dim_timer.setInterval(90)
            self._dim_timer.timeout.connect(self._apply_dim_now)
        self._dim_timer.start()

    def _apply_dim_now(self):
        """滑杆停手后统一做一次：写盘 + 刷样式表。"""
        self._save_mode()
        self._apply_theme_now()

    def set_panel_alpha(self, v):
        """面板不透明度：0 = 全透（只剩背景图），255 = 全实心。各层按比例一起变。"""
        self.panel_alpha = max(0, min(255, int(v)))
        self._apply_theme_fast()         # 跟手：只重画，不重建样式表
        self._schedule_dim_apply()       # 写盘 + 重建样式表，合并到停手之后

    def set_contrast(self, key):
        """文字对比：只动正文色，别的一概不碰。"""
        if key not in TEXT_PRESETS:
            return
        self.contrast = key
        self._save_mode()
        self._apply_theme_now()

    def set_soft_pct(self, v):
        """背景柔化：压在背景图上的固定柔化层，0 = 关掉让原图直接上来。

        它和「淡化」是两件事 —— 淡化是用户主动洗白，这个是防止一张高对比的图
        在淡化拉到 0 时直接冲上来。所以它得能单独关。
        """
        self.soft_pct = max(0, min(30, int(v)))
        self._apply_theme_fast()         # 跟手：只重画，不重建样式表
        self._schedule_dim_apply()       # 写盘 + 重建样式表，合并到停手之后

    def _apply_titlebar(self):
        """标题栏颜色：有背景图就跟着图片走，没有就用当前主题的固定色。

        之前不管什么主题都固定用深色 —— 浅色模式下窗口是亮的、标题栏却发黑，很割裂。
        """
        self.tint_window(self)
        # 已经开着的弹窗也一起刷一遍（新冒出来的由 TitleBarTinter 负责）
        for w in QApplication.topLevelWidgets():
            if w is self or not w.isVisible():
                continue
            if isinstance(w, (QMainWindow, QDialog)):
                self.tint_window(w)

    def tint_window(self, w):
        """给任意一个窗口染标题栏。主窗口、弹窗、消息框都走这一条。"""
        try:
            rgb = core.title_bar_color(self.bg_image,
                                       dark=bool(THEME.get("dark"))) or THEME["title_fallback"]
            core.apply_title_bar(int(w.winId()), rgb)
        except Exception:
            pass

    # —— 列宽存档 / 收尾 ——
    def _save_header(self):
        try:
            state = bytes(self.table.horizontalHeader().saveState().toBase64()).decode()
            core.write_ui(header_state=state)
        except Exception:
            pass

    def _schedule_save_header(self):
        if self._header_timer is not None:
            self.killTimer(self._header_timer)
        self._header_timer = self.startTimer(700)

    def timerEvent(self, ev):
        if self._header_timer is not None:
            self.killTimer(self._header_timer)
            self._header_timer = None
        self._save_header()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._apply_titlebar()
        # 首次运行引导挂在这儿，不挂在 reload() 里 —— reload() 在 __init__ 阶段
        # 就会被调到，那会儿窗口还没显示，对着空气弹模态框很别扭。
        QTimer.singleShot(0, self._check_claude_code)

    def _check_claude_code(self):
        """没装 Claude Code 时说清楚为什么列表是空的。

        别人机器上最可能缺的就是它。一个空列表配不上任何解释 ——
        用户只会以为程序坏了，而不是「我少装了一个东西」。
        """
        if self._warned_no_claude:
            return
        if os.path.isdir(core.PROJ_ROOT):
            return
        self._warned_no_claude = True
        QMessageBox.information(
            self, T("未找到对话记录"),
            T('未找到 Claude Code 的对话记录。\n\n本程序读取的是 Claude Code 存储在本机的对话，\n因此需要先安装 Claude Code 并至少使用过一次。\n\n安装方法：npm install -g @anthropic-ai/claude-code\n或参考 https://claude.ai/code'))

    def closeEvent(self, ev):
        self._save_header()
        try:
            geo = bytes(self.saveGeometry().toBase64()).decode()
        except Exception:
            geo = None
        # 滑杆那几项平时靠 90ms 防抖写盘，关窗口前要是正好没落地就丢了，这里补一刀
        self._save_mode()
        core.write_ui(bg_image=self.bg_image, win_state=geo, lang=self.lang,
                      style_light=self.style_light, style_dark=self.style_dark)
        super().closeEvent(ev)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(T(core.APP_TITLE))
    app.setStyle("Fusion")            # 统一观感，QSS 的行为也更好预测

    # 窗口左上角 / 任务栏的图标。打包后 exe 自己也带图标，但源码直接跑时
    # 只有这个文件能指望；两种情形路径不同，所以先看 _MEIPASS。
    _base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    _icon = os.path.join(_base, "assets", "icon.png")
    if os.path.exists(_icon):
        app.setWindowIcon(QIcon(_icon))

    ui = core.read_ui()
    i18n.set_lang(ui.get("lang") or default_lang())
    install_qt_translator(app, i18n.get_lang())
    # 新冒出来的窗口一律自动染标题栏（消息框、改名框这些以前是漏的）。
    # 过滤器得挂住，不能被回收 —— 挂成 app 的属性。
    app._tinter = TitleBarTinter(app)
    app.installEventFilter(app._tinter)

    pref = ui.get("theme") or "auto"
    dark = resolve_dark(app, pref)
    style = (ui.get("style_dark") or DEFAULT_DARK) if dark else (
        ui.get("style_light") or ("warm" if ui.get("warm") else DEFAULT_LIGHT))
    mode = "dark" if dark else "light"
    mode_ui = core.read_mode_ui(mode)
    apply_theme(app, style, mode_ui.get("panel_alpha"),
                contrast=mode_ui.get("contrast") or "normal",
                soft_pct=mode_ui.get("soft_pct"),
                has_image=bool(ui.get("bg_image")))
    win = MainWindow()
    # 挂住主窗口的引用：换语言时整个窗口会被重建掉，
    # 只靠局部变量的话旧的被回收、新的没人持有可能跟着没
    app._win = win

    # 系统主题一变就跟着切（只在选了「跟随系统」时生效）。
    # 注意是查 app._win 而不是闭包里的 win —— 换语言后窗口会换人，闭包会指到死对象上。
    try:
        app.styleHints().colorSchemeChanged.connect(
            lambda *_: app._win and app._win.on_system_scheme_changed())
    except Exception:
        pass

    # 有上次的窗口存档就用存档（尺寸、位置、最大化状态都在里面）；
    # 第一次打开才居中 —— 跟之前那版一致，不然位置随机。
    if not getattr(win, "_geo_restored", False):
        scr = app.primaryScreen().availableGeometry()
        w = min(win.width(), scr.width() - 80)
        h = min(win.height(), scr.height() - 80)
        win.resize(w, h)
        win.move(scr.x() + (scr.width() - w) // 2,
                 scr.y() + max(0, (scr.height() - h) // 3))

    win.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        try:
            with open(core.LOG_PATH, "a", encoding="utf-8") as f:
                f.write(time.strftime("\n===== %Y-%m-%d %H:%M:%S =====\n"))
                f.write(traceback.format_exc())
        except Exception:
            pass
        # 打包后没有控制台。原来这里直接 raise，用户看到的是
        # 「窗口凭空消失、什么都没留下」—— 必须弹个窗把日志路径告诉他。
        try:
            from PySide6.QtWidgets import QMessageBox
            _app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                T("会话簿 —— 出错了"),
                T('程序遇到错误，详情已记录到日志。\n\n日志位置：\n%s\n\n如果反复出现，请将日志文件发送给开发者。') % core.LOG_PATH,
            )
        except Exception:
            pass
        sys.exit(1)
