"""检查界面文字有没有漏翻 —— 打包前跑一遍。

为什么需要它：i18n 的设计是「中文原文当键，查不到就回落中文」。
这个设计的好处是漏翻不会把界面搞坏，**坏处是站在中文用户这边看不出来** ——
你看到的还是中文，完全察觉不到英文用户那边会蹦出一句中文。

所以把这件事做成一个能跑的检查，而不是靠人眼。

用法：
    python check_i18n.py          # 有问题时退出码 1，能直接卡住打包流程

检查三件事：
    1. 源码里的界面字符串，是不是都在 i18n.EN 里有对应条目
    2. EN 表里有没有「源码里根本不存在」的死条目（改文案时忘了同步）
    3. EN 的译文里有没有残留中文（多半是复制了键没改值）
"""

import ast
import re
import sys

import i18n

CJK = re.compile(r"[一-鿿]")
SRC_FILES = ("main.py", "session_core.py")

# 故意不翻译的东西，列在这儿（不然每次跑都会报）
IGNORE = {
    "中文",              # 语言下拉里那个选项：语言名一律显示原文
}

# 样式表整块跳过：里面是给开发看的注释，不是界面文字
SKIP_PREFIX = "\nQTableView {{"


def docstring_nodes(tree):
    """文档字符串的节点 id 集合 —— 那是给开发看的，不用翻。"""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def source_strings():
    """源码里所有「该翻译」的字符串，连带它们的位置。"""
    found = {}
    for f in SRC_FILES:
        src = open(f, encoding="utf-8").read()
        tree = ast.parse(src)
        docs = docstring_nodes(tree)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and CJK.search(node.value) and id(node) not in docs):
                found.setdefault(node.value, []).append("%s:%d" % (f, node.lineno))
    return found


def main():
    strings = source_strings()
    problems = []

    # 1. 漏翻
    for text, where in sorted(strings.items()):
        if text in i18n.EN or text in IGNORE or text.startswith(SKIP_PREFIX):
            continue
        problems.append(("漏翻", where[0], text))

    # 2. 死条目（EN 里有，源码里没有 —— 改文案时忘了同步）
    for key in i18n.EN:
        if key not in strings:
            problems.append(("死条目", "i18n.py", key))

    # 3. 译文里残留中文
    for key, val in i18n.EN.items():
        if CJK.search(val):
            problems.append(("译文含中文", "i18n.py", "%s → %s" % (key, val)))

    total = len(strings)
    covered = sum(1 for k in strings if k in i18n.EN)
    print("源码界面字符串 %d 条，EN 表 %d 条，覆盖 %d 条"
          % (total, len(i18n.EN), covered))

    if not problems:
        print("全部通过。")
        return 0

    print("\n发现 %d 处问题：\n" % len(problems))
    for kind, where, text in problems:
        one = text.replace("\n", "\\n")
        print("  [%s] %-16s %s" % (kind, where, one[:70]))
    print("\n修法：漏翻 → 往 i18n.EN 加一条（键 = 源码里的中文原文，一字不差）；"
          "\n      死条目 → 改 i18n.EN 里的键，或从表里删掉；"
          "\n      译文含中文 → 那条忘了写英文。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
