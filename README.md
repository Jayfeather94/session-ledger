# SessionLedger 会话簿

An unofficial desktop browser for [Claude Code](https://claude.ai/code) sessions
on Windows. PySide6 / Qt6.

Claude Code stores every conversation as a `.jsonl` file under
`~/.claude/projects/`, one folder per working directory. Its built-in `/resume`
only lists the conversations belonging to the project you are currently in.
SessionLedger lists **all of them at once**, across every project, and lets you
do the housekeeping the CLI has no commands for.

## Features

- **One table for every session** on the machine — search by name / folder /
  last prompt, sort by any column, drag columns to resize
- **Resume** — double-click a row to continue that conversation in a terminal
- **Rename** — the new title shows up in Claude Code's own `/resume` too
- **Delete with a trash** — removed from the list and from `/resume`, but the
  file is kept until you empty the trash
- **Move workspace** — rewrite a conversation's recorded directory and move the
  file into that project's folder (originals are backed up first)
- **New Session** — start a conversation in a default workspace, optionally in a
  timestamped subfolder so each session's output lands in its own directory
- **7 themes** (4 light / 3 dark), background image with fade and soften
- **Chinese / English** UI, switchable at runtime
- **Portable** — no registry keys, no service, no installer; delete the folder
  to uninstall

## Requirements

- Windows 10 / 11
- [Claude Code](https://claude.ai/code) — `npm install -g @anthropic-ai/claude-code`
- Optional: Windows Terminal, for a nicer resume window

## Install

Download the zip, extract it anywhere, run `SessionLedger.exe`. See `README.txt`
inside the folder for the full user guide (Chinese and English).

## Where your settings live

```
%APPDATA%\claude-session-list\ui.json
```

Deleting the program folder does not delete this file.

## Build from source

Use an **official** Python 3.13 from python.org. The Microsoft Store build does
not work with PyInstaller — its `python.exe` is a zero-byte shim and the real
interpreter sits in a protected directory PyInstaller cannot read.

```bat
python -m venv venv
venv\Scripts\pip install PySide6==6.11.2 Pillow==12.3.0 pyinstaller
venv\Scripts\python check_i18n.py
venv\Scripts\python -m PyInstaller --clean --noconfirm build.spec
```

Output lands in `dist\SessionLedger\`. `打包.bat` runs these same steps; edit the
`VENV` path at the top of it first.

`check_i18n.py` is not optional: the string table falls back to Chinese on a
miss, so a forgotten translation is invisible to a Chinese user and only shows
up as Chinese text in the English UI. The script exits non-zero on any miss.

## Project layout

| Path | What it is |
|---|---|
| `main.py` | UI layer (PySide6 / Qt6) — the entry point |
| `session_core.py` | Data layer — finds, parses and rewrites the session files |
| `i18n.py` | Chinese ↔ English string table |
| `check_i18n.py` | Pre-build check for missing translations |
| `build.spec` | PyInstaller config (onedir, no UPX, windowed) |
| `build.bat` | One-click build |
| `slim.ps1` | Optional trimming of the PyInstaller output |
| `version_info.txt` | EXE file properties (product name, version) |
| `assets/icon.ico` | App icon, embedded in the EXE (256 → 16 px) |
| `README.txt` | End-user guide, shipped inside the zip |

## How this differs from `/resume`

| | `/resume` | SessionLedger |
|---|---|---|
| Scope | the current project only | every project |
| Search | by prompt text | by name, folder and last prompt |
| Sorting | recency | any column |
| Rename | yes | yes (writes through to `/resume`) |
| Delete | no | trash, restorable |
| Move a session to another folder | no | yes |

## License

The project's own code is released under the MIT License.

Third-party components bundled with the built program:

- [PySide6](https://www.qt.io/qt-for-python) — LGPL v3
- [Pillow](https://python-pillow.org/) — MIT-CMU / HPND

---

## 中文

**会话簿** 是一个 Windows 上的 Claude Code 会话浏览器，用 PySide6 / Qt6 写的。

Claude Code 把每次对话存成 `~/.claude/projects/` 下的一个 `.jsonl` 文件，按工作
目录分文件夹。官方的 `/resume` 只能看到**当前项目**的对话，这个工具把**所有项目**
的对话汇到一张表里，另外补上了命令行没有的那些整理功能。

**功能**

- 全机所有对话一张表：按名字 / 文件夹 / 最后提问搜索，按任意列排序，列宽可拖
- 双击一行，在终端里接着这个对话聊
- 改名 —— 新名字在 Claude Code 自己的 `/resume` 里也会显示
- 删除带回收站：先从列表和 `/resume` 里拿走，文件留着，确认没问题再彻底删
- 迁移工作区：改写对话里记录的目录并把文件搬到对应项目文件夹（原文件先备份）
- 新建对话：在默认工作区里开新对话，可以顺便按时间戳建一个独立产出子目录
- 7 套主题（4 浅 3 深）、背景图淡化柔化、中英文界面、免安装便携版

**使用说明**见同目录的 `README.txt`（中英双语）。

**设置文件**在 `%APPDATA%\claude-session-list\ui.json`，删程序不会删它。

**署名与许可**：本项目自己的代码用 MIT 许可；打包进去的第三方组件是
PySide6（LGPL v3）和 Pillow（MIT-CMU / HPND）。
