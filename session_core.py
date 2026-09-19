# -*- coding: utf-8 -*-
"""会话数据层 —— 读记录 / 改名 / 删除回收站 / 配置存档。

这一层完全不碰界面，纯粹的 Python。所以：
  - 换界面工具时原样搬走即可
  - 可以单独写脚本调它、测它，不用开窗口

界面层在 main.py。
"""

import colorsys
import glob
import json
import math
import re
import os
import shutil
import subprocess
import sys
import time
import traceback

from i18n import T

# 背景图要读 JPG、要平滑缩放、要压暗，这些都得靠 Pillow。
# 没装也能跑 —— 只是读不了 JPG、缩放会糙一点、没法压暗。
try:
    from PIL import Image          # 只要 Image —— ImageTk 会把 tkinter 拖进来
    HAS_PIL = True
except Exception:
    HAS_PIL = False


# ════════════════════════════════════════════════════════════════
#  配置区 —— 想改外观、尺寸、存放位置，基本都在这一段
# ════════════════════════════════════════════════════════════════

APP_TITLE = "会话簿"

HOME = os.path.expanduser("~")
# Claude Code 把每场对话存成一个 .jsonl，放在这里
PROJ_ROOT = os.path.join(HOME, ".claude", "projects")
# 删掉的对话挪到这儿（可恢复）
TRASH_DIR = os.path.join(HOME, ".claude", "trash-sessions")
TRASH_JSON = os.path.join(TRASH_DIR, "_trash.json")

# 单个文件最大 20MB，全读太慢 —— 只读头尾两段
HEAD_BYTES = 96 * 1024
TAIL_BYTES = 192 * 1024

# 窗口尺寸（按 100% 缩放写，实际会乘上这台机器的缩放系数）

# 颜色
ROW_BG = "#f5f6f8"          # 隔行浅灰，长列表更好扫
SEL_BG = "#2f6fb5"          # 选中那行的高亮
DETAIL_FG = "#3a3a3a"       # 详情栏文字
STATUS_FG = "#666"          # 右下角状态文字
CARD_BG = "#ffffff"         # 「卡片」的底色 —— 列表和按钮都在这张卡片上

# 背景图：图片铺满整窗，内容做成一张卡片浮在中间，于是图片从卡片四周露出来。
# 列表本身还是一块实心面板 —— tkinter 做不到「列表半透明透出图片」。
BG_MARGIN = 22              # 没开半透明时，卡片四周留多宽（图片从这儿露出来）
BG_DIM = 0.72               # 图片往浅色方向淡化的程度：0 = 原样，1 = 几乎全白

# 半透明用的「颜色键」：窗口里所有这个颜色的像素会变成真正的洞，
# 露出背后那个专门放图片的窗口。选一个照片里几乎不可能自然出现的颜色。
# 只在 Windows 上有效。
KEY_COLOR = "#010203"
HEAD_FG = "#2b2b2b"         # 开半透明后，表头文字的颜色

# 标题栏（顶部那条能拖动的）—— 从背景图里取色，见 title_bar_color()
#
# 结构是「色相从图里取，饱和度、明度钉死在设定档」，深浅各一套档位：
#   深色：输出恒定在亮度 0.19 一带，跟深色界面主体（0.1~0.2）是一条带上的
#   浅色：输出恒定在亮度 0.90 一带，跟浅色界面主体（0.88~1.00）是一条带上的
# 之前浅色沿用了深色的档位，结果标题栏恒定 0.19、界面主体 0.96 —— 差五倍，
# 中间没有任何过渡，浅色下就是一条突兀的黑带。
TITLE_BAR_SAT_DARK = 0.30   # 深色：色彩倾向留多少（明度低，所以不晃眼）
TITLE_BAR_VAL_DARK = 0.24
TITLE_BAR_SAT_LIGHT = 0.07  # 浅色：只让色相「露一点」。再大就抢眼了
TITLE_BAR_VAL_LIGHT = 0.94  # 落在浅色界面主体那条带上，跟 title_fallback 几乎重合
# 参与色相投票的门槛 (饱和度门槛, 明度门槛)。浅色放宽一点，让更多像素参与统计。
TITLE_BAR_GATE_DARK = (0.12, 0.12)
TITLE_BAR_GATE_LIGHT = (0.06, 0.10)
TITLE_BAR_FALLBACK = (42, 42, 48)   # 没设背景图时用的中性深灰

# 一条隐形空列，专门吃掉最右边的剩余宽度。
# 没有它的话，列宽合计小于表格宽度时右边会留一条白边，隔行底色铺不过去，很难看。
PAD_COL = "__pad"

# 列表的列： 键, 表头文字, 宽度占比, 对齐
COLUMNS = (
    ("title", "名字", 0.46, "w"),
    ("dir", "文件夹", 0.24, "w"),
    ("when", "最后活动", 0.18, "w"),
    ("msgs", "条数", 0.12, "e"),
)

# 点表头排序时，每一列按什么排
SORT_KEYS = {
    "title": lambda r: r["title"].lower(),
    "dir": lambda r: (r["cwd"] or "").lower(),
    "when": lambda r: r["mtime"],
    "msgs": lambda r: r["msgs"],
}


def _migrate_config_if_needed(new_dir):
    """把老位置的设置搬过来。

    开发时跑在**微软商店版 Python** 下，写 %APPDATA% 会被系统重定向到
    %LOCALAPPDATA%\\Packages\\PythonSoftwareFoundation.Python.3.13_*\\LocalCache\\Roaming\\
    —— 文件其实一直在那儿。而打包出来的 exe 没有包标识，写的是**真正的** %APPDATA%，
    两个位置不是一回事。

    不搬的话，从开发版换到打包版会发现设置全没了：
    背景图、配色、两个深浅模式各自的滑杆值、列宽、窗口位置、语言。

    找不到旧配置就静默跳过 —— 新用户本来就没有，不该被这事打扰。
    """
    target = os.path.join(new_dir, "ui.json")
    if os.path.exists(target):
        return                      # 新位置已经有了，不用搬
    local = os.environ.get("LOCALAPPDATA") or ""
    if not local:
        return
    pattern = os.path.join(local, "Packages", "PythonSoftwareFoundation.Python.*",
                           "LocalCache", "Roaming", "claude-session-list", "ui.json")
    try:
        matches = glob.glob(pattern)
        if not matches:
            return
        # 按修改时间倒序 —— 机器上可能装过好几个商店版 Python（3.13 / 3.14 各一份），
        # glob 的顺序没有保证，取最新那份才是用户真正在用的
        matches.sort(key=os.path.getmtime, reverse=True)
        for old in matches:
            if os.path.abspath(old).lower() == os.path.abspath(target).lower():
                continue      # 开发环境下两者指同一个文件，没什么好搬的
            shutil.copy2(old, target)
            return
    except Exception:
        pass                        # 迁移失败不影响启动，用默认值就是了


def config_dir():
    """放配置和出错日志的目录。

    特意不用脚本所在目录 —— 以后打包成单个 exe 时，
    脚本目录会指向一个退出即删的临时目录，配置就丢了。
    """
    base = os.environ.get("APPDATA") or os.path.join(HOME, ".config")
    # 目录名用纯英文：Git Bash 之类的工具处理中文路径不可靠
    d = os.path.join(base, "claude-session-list")
    try:
        os.makedirs(d, exist_ok=True)
        _migrate_config_if_needed(d)
        return d
    except Exception:
        return HOME


UI_JSON = os.path.join(config_dir(), "ui.json")       # 记住你拉出来的列宽
LOG_PATH = os.path.join(config_dir(), "error.log")    # 出错时的线索


# ════════════════════════════════════════════════════════════════
#  跟着系统走的几件事 —— 全集中在这儿
#  以后要支持 Mac / Linux，只改这一段就行
# ════════════════════════════════════════════════════════════════

IS_WINDOWS = (os.name == "nt")


def set_dpi_awareness():
    """高分屏下按真实像素画，字才不糊。只有 Windows 需要。"""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def open_terminal(cwd, command):
    """在指定目录新开一个终端窗口跑这条命令。返回 (成功?, 说明)。"""
    if not IS_WINDOWS:
        return False, T("「接着聊」目前只支持 Windows")
    try:
        wt = shutil.which("wt.exe") or shutil.which("wt")
        if wt:
            subprocess.Popen([wt, "-d", cwd, "cmd.exe", "/k", command], close_fds=True)
        else:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", "/D", cwd, "cmd.exe", "/k", command],
                close_fds=True,
            )
        return True, cwd
    except Exception as e:
        return False, str(e)


def open_folder(path):
    """用系统的文件管理器打开一个目录。

    Windows 上**显式调 explorer.exe，不走 os.startfile**。
    startfile 走的是系统「打开文件夹」的【关联动作】—— 那个关联被系统设置
    或第三方工具改过之后，点「打开目录」就可能变成开终端、开别的程序，
    甚至什么都不发生（startfile 不报错，调用方看不出来）。
    explorer.exe 是直接指名道姓，中间没有可被改道的一层。

    返回 True 只代表「命令发出去了」；资源管理器到底开没开，这里管不着。
    """
    try:
        if not path or not os.path.isdir(path):
            return False
        if IS_WINDOWS:
            subprocess.Popen(["explorer.exe", os.path.normpath(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


# ———— 标题栏上色（Windows 10/11）————
# 只改颜色，拖动 / 双击最大化 / 贴边吸附 / 最小化关闭 全是系统原生的，没动。

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def _colorref(rgb):
    """Windows 的颜色是 0x00BBGGRR —— 注意字节序是反的。"""
    r, g, b = rgb
    return (int(b) << 16) | (int(g) << 8) | int(r)
def _dwm_set(hwnd, attr, value):
    try:
        import ctypes
        from ctypes import windll
        v = ctypes.c_int(int(value))
        r = windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))
        return r == 0
    except Exception:
        return False


def title_bar_color(path, dark=False):
    """从背景图里挑一个「好看、不晃眼」的颜色给标题栏。

    **不能直接求整图平均色** —— 照片一平均就洗成一团浑浊的灰，
    红一块蓝一块的图尤其惨（红 + 蓝 = 脏紫）。而且整体偏灰的图会得到
    一个跟谁都不像的中性灰，「跟图片配色」就名存实亡了。

    真正决定「这是什么颜色」的，是图里**又鲜艳又够亮**的那些像素。
    所以：

      1. 只让饱和度和亮度都够的像素参与投票，其余（灰的、太暗的）不参与
      2. 色相用加权圆平均算 —— 色相是环形的，0° 和 359° 其实是邻居，
         直接求算术平均会算错
      3. 算出来的色相保留，但饱和度和明度都钉死在设定档上：
         饱和度有限所以不刺眼；明度固定所以图片忽明忽暗都不影响观感

    dark 决定用哪套档位 —— 深浅各一套，输出的亮度必须各自落在
    对应界面主体的那条带子上（深色 0.19 / 浅色 0.90），
    否则标题栏就跟界面割裂成两个世界。

    全灰的图没有「鲜艳像素」可投，就自然退化成中性灰（跟着档位走）。

    没装 Pillow、没设图片、或读图失败，都返回 None，外面用中性色兜底。
    """
    if not (path and HAS_PIL and os.path.exists(path)):
        return None
    try:
        im = Image.open(path).convert("RGB").resize((64, 64), Image.LANCZOS)
        px = im.load()               # 用 load() 而不是 getdata() —— 后者将来会被移除
        if dark:
            sat, val = TITLE_BAR_SAT_DARK, TITLE_BAR_VAL_DARK
            s_gate, v_gate = TITLE_BAR_GATE_DARK
        else:
            sat, val = TITLE_BAR_SAT_LIGHT, TITLE_BAR_VAL_LIGHT
            s_gate, v_gate = TITLE_BAR_GATE_LIGHT

        sx = sy = total = 0.0
        for y in range(im.height):
            for x in range(im.width):
                r, g, b = px[x, y]
                h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                # 灰扑扑的、太暗的直接弃权 —— 它们的色相没意义，只会把结果搅浑。
                # ★ 这一整段必须留在 x 循环【里面】：
                #   之前它跟 for x 平级，等于每行只在 x 跑完之后算一次，
                #   用的是那一行最后一个像素 —— 全图最多 64 个样本（每行最右一个），
                #   实际变成「只取图片最右一列的颜色」，跟注释说的完全不是一回事。
                w = max(0.0, s - s_gate) * max(0.0, v - v_gate)
                if w <= 0.0:
                    continue
                a = h * 2.0 * math.pi
                sx += w * math.cos(a)
                sy += w * math.sin(a)
                total += w
        if total <= 0.0:
            # 整张图没有鲜艳像素 —— 就是张灰图，给中性灰（明度跟着档位走）
            r2, g2, b2 = colorsys.hsv_to_rgb(0.0, 0.0, val)
        else:
            hue = (math.atan2(sy, sx) / (2.0 * math.pi)) % 1.0
            r2, g2, b2 = colorsys.hsv_to_rgb(hue, sat, val)
        return (int(round(r2 * 255)), int(round(g2 * 255)), int(round(b2 * 255)))
    except Exception:
        return None


def apply_title_bar(hwnd, rgb):
    """把标题栏、边框、文字一起染色。深浅按算出来的颜色定。"""
    if not (IS_WINDOWS and hwnd and rgb):
        return False
    r, g, b = rgb
    # 感知亮度，决定用深色模式（浅字）还是浅色模式（深字）
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    dark = 1 if lum < 0.55 else 0
    ok = _dwm_set(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, dark)
    _dwm_set(hwnd, DWMWA_CAPTION_COLOR, _colorref(rgb))
    _dwm_set(hwnd, DWMWA_BORDER_COLOR, _colorref(rgb))
    if dark:
        _dwm_set(hwnd, DWMWA_TEXT_COLOR, _colorref((232, 232, 240)))
    else:
        _dwm_set(hwnd, DWMWA_TEXT_COLOR, _colorref((26, 26, 28)))
    return ok

# 列表的列： 键, 表头文字, 宽度占比, 对齐
COLUMNS = (
    ("title", "名字", 0.46, "w"),
    ("dir", "文件夹", 0.24, "w"),
    ("when", "最后活动", 0.18, "w"),
    ("msgs", "条数", 0.12, "e"),
)

ROW_BG = "#f5f6f8"          # 隔行浅灰，长列表更好扫
SEL_BG = "#2f6fb5"
# 一条隐形空列，专门吃掉最右边的剩余宽度。
# 没有它的话，列宽合计小于表格宽度时右边会留一条白边，隔行底色铺不过去，很难看。
PAD_COL = "__pad"

# 点表头排序时，每一列按什么排
SORT_KEYS = {
    "title": lambda r: r["title"].lower(),
    "dir": lambda r: (r["cwd"] or "").lower(),
    "when": lambda r: r["mtime"],
    "msgs": lambda r: r["msgs"],
}


# ———————————————— 读记录 ————————————————

def _chunks(path):
    """把文件头和尾读回来。小文件就是整个文件。"""
    with open(path, "rb") as f:
        head = f.read(HEAD_BYTES)
        try:
            f.seek(-TAIL_BYTES, os.SEEK_END)
        except OSError:
            f.seek(0)
        tail = f.read()
    return head, tail


def _entries(chunk):
    """一段字节切成行，能解析成 JSON 的留下。切在半截的行会解析失败，跳过就好。"""
    out = []
    for raw in chunk.split(b"\n"):
        raw = raw.strip()
        if not raw.startswith(b"{"):
            continue
        try:
            out.append(json.loads(raw.decode("utf-8", "replace")))
        except Exception:
            continue
    return out


def _prompt_text(o):
    """从一条 user 记录里抠出用户真正打的那句话；抠不出来返回 None。"""
    if o.get("type") != "user" or o.get("isMeta"):
        return None
    content = (o.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(
            b.get("text") or ""
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        return None
    text = text.strip()
    # 指令展开、工具回包、系统提醒都不是用户打的字
    if not text or text.startswith("<") or "<command-name>" in text or "system-reminder" in text:
        return None
    return text


def parse_session(path, sid, proj):
    st = os.stat(path)
    head, tail = _chunks(path)

    first_prompt = summary = cwd = None
    for o in _entries(head):
        t = o.get("type")
        if t == "user" and first_prompt is None:
            first_prompt = _prompt_text(o)
        elif t == "summary" and summary is None:
            s = o.get("summary")
            if isinstance(s, str) and s.strip():
                summary = s.strip()
        if cwd is None and isinstance(o.get("cwd"), str):
            cwd = o["cwd"]

    agent_name = custom_title = ai_title = last_prompt = branch = None
    msgs = 0
    for o in _entries(tail):
        t = o.get("type")
        if t == "custom-title":
            custom_title = o.get("customTitle") or custom_title
        elif t == "ai-title":
            ai_title = o.get("aiTitle") or ai_title
        elif t == "agent-name":
            agent_name = o.get("agentName") or agent_name
        elif t == "last-prompt":
            last_prompt = o.get("lastPrompt") or last_prompt
        if isinstance(o.get("cwd"), str):
            cwd = o["cwd"]
        if o.get("gitBranch"):
            branch = o["gitBranch"]
        if t == "system" and isinstance(o.get("messageCount"), int):
            msgs = o["messageCount"]

    # 和 Claude Code 自己一样的取名优先级（后写的覆盖先写的）
    named = agent_name or custom_title or ai_title or summary or first_prompt
    title = " ".join(str(named or sid[:8]).split())
    if len(title) > 90:
        title = title[:89] + "…"

    return {
        "id": sid,
        "file": path,
        "proj": proj,
        "cwd": cwd or "",
        "title": title,
        # 一个名字都没读出来 —— 记录格式多半变了，列表里只能显示编号。
        # 拿这个当「格式对不对」的探针，见 App.reload()。
        "no_title": not named,
        "renamed": bool(custom_title),
        "last_prompt": " ".join(str(last_prompt).split())[:300] if last_prompt else "",
        "branch": branch or "",
        "msgs": msgs,
        "mtime": st.st_mtime,
        "size": st.st_size,
    }


def _pid_alive(pid):
    """这个进程还活着吗。问不出来就当它不活着 —— 宁可漏报，不要误拦。"""
    if not IS_WINDOWS:
        return False
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    except Exception:
        return False


def live_session_ids():
    """正在跑着的对话 id 集合。

    Claude Code 把每个活着的会话写在 ~/.claude/sessions/<pid>.json 里。
    迁移要改写并搬走对话文件 —— 正开着的会话这么一搞会冲突，
    所以先把它们挑出来，让用户关掉再说。

    顺手用 pid 判一下死活：那个目录会留陈旧文件，不看 pid 的话
    会拿早就退出的会话来拦人。
    """
    out = set()
    try:
        d = os.path.join(HOME, ".claude", "sessions")
        for f in os.scandir(d):
            if not f.name.endswith(".json"):
                continue
            try:
                with open(f.path, encoding="utf-8") as fh:
                    o = json.load(fh)
                if o.get("sessionId") and _pid_alive(o.get("pid", 0)):
                    out.add(o["sessionId"])
            except Exception:
                continue
    except Exception:
        pass
    return out


def project_folder_for(path):
    """算出一个目录对应的 Claude Code 项目文件夹名。

    规则是从现有数据反推出来的：**每个非 ASCII 字母数字的字符都变成一个 `-`**，
    中文也是一字一个。拿六个现有项目文件夹验过，全部吻合。

    （不是官方文档给的，是推的。所以 migrate_session 里优先复用「新路径已经
    有文件夹」的情况，实在没有才用这个算。）
    """
    return re.sub(r"[^A-Za-z0-9]", "-", path.rstrip("\\/"))


def migrate_session(rec, new_cwd):
    """把一个对话的工作区改到 new_cwd。返回 (成功?, 说明)。

    做两件事：

      1. **改写 jsonl 里【顶层】的 cwd 字段。** 只动顶层 —— 每条记录里的
         message / 工具参数里也会出现路径，那是对话的历史内容，
         改了等于篡改记录，所以一律不碰。
      2. **把文件挪到新目录对应的项目文件夹下。** Claude Code 是按文件夹
         找对话的，光改字段不挪文件，/resume 里还是老样子。

    原文件先整份备份到配置目录的 migrate_backup/ —— 动的是对话数据，
    出事得有得退。
    """
    src = rec.get("file") or ""
    old = (rec.get("cwd") or "").rstrip("\\/")
    new_cwd = (new_cwd or "").rstrip("\\/")
    if not src or not os.path.isfile(src):
        return False, T("对话文件不存在")
    if not new_cwd:
        return False, T("没指定目标目录")
    if old and os.path.normcase(old) == os.path.normcase(new_cwd):
        return False, T("工作区没变")
    if not os.path.isdir(new_cwd):
        return False, T("目标目录不存在")

    bak_dir = os.path.join(config_dir(), "migrate_backup")
    try:
        os.makedirs(bak_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(
            bak_dir, "%s-%d.jsonl" % (rec.get("id", "x"), int(time.time()))))
    except Exception as e:
        return False, T("备份失败，已中止：%s") % e

    tmp = src + ".tmp"
    changed = 0
    try:
        with open(src, "r", encoding="utf-8", errors="replace") as fi, \
             open(tmp, "w", encoding="utf-8") as fo:
            for line in fi:
                s = line.rstrip("\n")
                if not s:
                    continue
                try:
                    o = json.loads(s)
                except Exception:
                    fo.write(line)          # 解析不了的原样留着，别丢数据
                    continue
                if isinstance(o, dict) and isinstance(o.get("cwd"), str):
                    o["cwd"] = new_cwd
                    changed += 1
                    fo.write(json.dumps(o, ensure_ascii=False,
                                        separators=(",", ":")) + "\n")
                else:
                    fo.write(line)
    except Exception as e:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False, T("改写失败，原文件没动：%s") % e

    dst_dir = os.path.join(PROJ_ROOT, project_folder_for(new_cwd))
    dst = os.path.join(dst_dir, os.path.basename(src))
    try:
        os.makedirs(dst_dir, exist_ok=True)
        if os.path.normcase(dst) == os.path.normcase(src):
            os.replace(tmp, src)
        else:
            if os.path.exists(dst):
                os.remove(tmp)
                return False, T("目标文件夹里已经有同 ID 的对话了")
            os.replace(tmp, dst)
            os.remove(src)
            # 老文件夹空了就顺手收掉，别留一地空目录
            try:
                if not os.listdir(os.path.dirname(src)):
                    os.rmdir(os.path.dirname(src))
            except Exception:
                pass
    except Exception as e:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False, T("移动文件失败：%s") % e

    return True, T("已改 %d 处记录，文件移到 %s") % (changed, project_folder_for(new_cwd))


def load_sessions():
    """扫所有项目文件夹，返回按最后活动时间倒序的列表。"""
    out = []
    if not os.path.isdir(PROJ_ROOT):
        return out
    for proj in os.scandir(PROJ_ROOT):
        if not proj.is_dir():
            continue
        for f in os.scandir(proj.path):
            if not f.is_file() or not f.name.endswith(".jsonl"):
                continue
            try:
                out.append(parse_session(f.path, f.name[:-6], proj.name))
            except Exception:
                continue
    out.sort(key=lambda r: r["mtime"], reverse=True)
    return out


# ———————————————— 显示用的格式化 ————————————————

def pretty_dir(p):
    """把绝对路径缩成 ~ 开头的短路径。"""
    if not p:
        return ""
    p = p.rstrip("\\/")
    if p.lower().startswith(HOME.lower()):
        rest = p[len(HOME):].lstrip("\\/")
        return "~" + (os.sep + rest if rest else "")
    return p


def short_dir(p):
    """列表里那一列用：只留最后两段。"""
    d = pretty_dir(p)
    if not d:
        return "?"
    parts = [x for x in d.replace("/", "\\").split("\\") if x]
    if len(parts) <= 2:
        return d
    return "…\\" + "\\".join(parts[-2:])


def rel_time(ts):
    d = time.time() - ts
    if d < 60:
        return T("刚刚")
    if d < 3600:
        return T("%d 分钟前") % int(d // 60)
    if d < 86400:
        return T("%d 小时前") % int(d // 3600)
    if d < 86400 * 2:
        return T("昨天 ") + time.strftime("%H:%M", time.localtime(ts))
    if d < 86400 * 7:
        return T("%d 天前") % int(d // 86400)
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


# ———————————————— 干活的三个动作 ————————————————

def resume_session(rec):
    """在原来那个文件夹里，新开一个终端窗口接着聊。"""
    cwd = rec["cwd"] if rec["cwd"] and os.path.isdir(rec["cwd"]) else HOME
    return open_terminal(cwd, "claude --resume " + rec["id"])


def rename_session(rec, new_title):
    """往记录文件尾巴上追加一行 custom-title —— Claude Code 认这个，后写的覆盖先写的。"""
    line = json.dumps(
        {"type": "custom-title", "customTitle": new_title, "sessionId": rec["id"]},
        ensure_ascii=False,
    ).encode("utf-8")
    with open(rec["file"], "r+b") as f:
        f.seek(0, os.SEEK_END)
        if f.tell() > 0:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                f.seek(0, os.SEEK_END)
                f.write(b"\n")
        f.seek(0, os.SEEK_END)
        f.write(line + b"\n")


def _load_manifest():
    try:
        with open(TRASH_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_manifest(m):
    os.makedirs(TRASH_DIR, exist_ok=True)
    tmp = TRASH_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TRASH_JSON)


def soft_delete(rec):
    """移到回收站：文件挪走，所以官方的 /resume 里也就看不见了。可恢复。"""
    os.makedirs(TRASH_DIR, exist_ok=True)
    dst = os.path.join(TRASH_DIR, rec["id"] + ".jsonl")
    if os.path.exists(dst):
        dst = os.path.join(TRASH_DIR, "%s-%d.jsonl" % (rec["id"], int(time.time())))
    shutil.move(rec["file"], dst)
    m = _load_manifest()
    m[rec["id"]] = {
        "id": rec["id"],
        "title": rec["title"],
        "cwd": rec["cwd"],
        "proj": rec["proj"],
        "orig_file": rec["file"],
        "trash_file": dst,
        "deleted_at": time.time(),
        "mtime": rec["mtime"],
        "size": rec["size"],
    }
    _save_manifest(m)


def trash_entries():
    """回收站里的东西，按删除时间倒序。"""
    m = _load_manifest()
    items = list(m.values())
    for it in items:
        if not os.path.exists(it.get("trash_file", "")):
            it["_missing"] = True
    items.sort(key=lambda r: r.get("deleted_at", 0), reverse=True)
    return items


def restore_entry(item):
    m = _load_manifest()
    orig = item["orig_file"]
    src = item.get("trash_file")
    if not src or not os.path.exists(src):
        return False, T('回收站中找不到该文件')
    os.makedirs(os.path.dirname(orig), exist_ok=True)
    if os.path.exists(orig):
        return False, T('原位置已存在同名文件，未覆盖')
    shutil.move(src, orig)
    m.pop(item["id"], None)
    _save_manifest(m)
    return True, orig


def purge_entry(item):
    src = item.get("trash_file")
    if src and os.path.exists(src):
        os.remove(src)
    m = _load_manifest()
    m.pop(item["id"], None)
    _save_manifest(m)


# ———————————————— 记住界面设置 ————————————————
# 列宽存的是「占比」不是像素：换台机器、换个缩放、窗口拉多大，比例都对得上。

def read_ui():
    """读界面设置。文件坏了或没有，都当空字典 —— 绝不能因为读设置失败就开不了窗。"""
    try:
        with open(UI_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def write_ui(**patch):
    """改其中几项，其余保留 —— 别把别的设置覆盖掉。"""
    d = read_ui()
    d.update(patch)
    try:
        tmp = UI_JSON + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, UI_JSON)
    except Exception:
        pass


# 深浅两套各自存一份的界面设置。只按【深浅】分，不按珠光/暖纸那种配色分 ——
# 配色是同一套深浅下的变体，该共用；深浅才是「两种不同的观感」。
MODE_KEYS = ("panel_alpha", "bg_dim", "soft_pct", "contrast", "alt_rows")


def read_mode_ui(mode):
    """读某一套（"light" / "dark"）的界面设置。

    老配置里这些键是平铺在最外层的，没有分套 —— 那种情况就把它当成
    两套共同的初值（两边都拿同一份），迁上来视觉上不会有任何突变。
    """
    d = read_ui()
    bucket = d.get(mode)
    if isinstance(bucket, dict):
        return bucket
    return {k: d[k] for k in MODE_KEYS if k in d}


def write_mode_ui(mode, **patch):
    """只改这一套里的几项，另一套和全局项一律不碰。"""
    d = read_ui()
    other = "dark" if mode == "light" else "light"
    seed = {k: d[k] for k in MODE_KEYS if k in d}           # 老的平铺值
    # 第一次写就把两套一起建出来，都以老的平铺值起头 ——
    # 否则「还没动过的那套」会一直回头去读平铺值，越读越旧。
    for key in (mode, other):
        if not isinstance(d.get(key), dict):
            d[key] = dict(seed)
    d[mode].update(patch)
    try:
        tmp = UI_JSON + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, UI_JSON)
    except Exception:
        pass


def load_width_ratios():
    """上次拉好的列宽占比；没有或不对就返回 None，用默认比例。"""
    ws = read_ui().get("widths")
    if isinstance(ws, list) and len(ws) == len(COLUMNS):
        if all(isinstance(x, (int, float)) and x > 0 for x in ws):
            s = float(sum(ws))
            if s > 0:
                return [x / s for x in ws]
    return None


def save_width_ratios(ratios):
    write_ui(widths=[round(x, 4) for x in ratios])


