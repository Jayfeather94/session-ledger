会话簿 SessionLedger — 使用说明 / Read Me
==================================================


────────────────── 中文 ──────────────────


这是什么
--------
一个查看和管理 Claude Code 对话记录的小工具。

它读的是 Claude Code 存在你自己电脑上的对话文件，
列成一个表格，可以搜索、排序、改名、删除、一键接着聊。


运行前需要
----------
1. Claude Code（必需）

   这个程序本身不含任何对话内容，它只是把 Claude Code 存的对话
   读出来给你看。所以没装 Claude Code 的话，打开会是一个空列表，
   程序会提示你。

   装法：
       npm install -g @anthropic-ai/claude-code

   或者参考：https://claude.ai/code

2. Windows Terminal（可选）

   有的话，「接着聊」会在 Windows Terminal 里打开，体验更好。
   没有就退回用系统自带的 cmd，功能一样。


怎么用
------
双击「SessionLedger.exe」就行。

  搜索框       按名字 / 文件夹 / 最后提问筛选
  双击某一行   在终端里接着这个对话聊
  F2           改名
  Delete       删除（会先问你）
  Ctrl / Shift 点   多选，可以一次删一批
  点表头       按那一列排序
  右键？       没有右键菜单，功能都在下面的按钮上

「设置」里能调：
  语言         中文 / English
  主题         跟随系统 / 4 套浅色 / 3 套深色
  文字对比     柔和 / 标准 / 高对比
  面板不透明度 界面透出背景图的程度
  隔行深浅交替
  背景图       选一张图铺在窗口背后

「新建对话」会在你设的默认工作区里开一个新对话。开了「每次对话使用
独立子目录」的话，还会在那个工作区下按时间戳建一个子目录，让 Claude
把这次的产出都放在里面。


删掉的对话去哪了
----------------
不会真删。点「删除」只是把它从列表和 Claude Code 的 /resume 里拿走，
放进程序的「回收站」。

  回收站 → 恢复          放回去
  回收站 → 彻底删除      文件真的删掉，捞不回来
  回收站 → 清空回收站    把里面所有都真删掉

清理不用的对话时，建议先用「删除」，过几天确认没问题再「彻底删除」。


设置存在哪
----------
  %APPDATA%\claude-session-list\ui.json

  想看这个文件夹：按 Win+R，把 %APPDATA%\claude-session-list 粘进去回车。

  **删掉程序不会删这个文件** —— 重装回来设置还在。


怎么卸载
--------
直接删掉整个程序文件夹就行。这程序不写注册表、不装服务、不留后台。

想彻底清干净，再把上面那个设置目录也删掉。


出错了怎么办
------------
程序崩了会弹一个窗口，告诉你日志在哪：

  %APPDATA%\claude-session-list\error.log

把那个文件发给开发者就能查。

窗口根本没出现、也没有弹窗的话，也去上面那个目录看看有没有 error.log。


常见问题
--------
Q: 列表是空的？
A: 要么没装 Claude Code，要么装了还没用过。先用 Claude Code 聊一次再看。

Q: 列表里很多条只显示一串编号（比如 0830fde6），没有名字？
A: 那些对话还没有标题 —— Claude Code 只给聊过几句的对话生成标题。
   不影响使用，双击照样能进去聊。

Q: 双击一行，终端开了但报错说找不到 claude 命令？
A: Claude Code 的命令行工具没在 PATH 里。

Q: 换电脑了，对话能带走吗？
A: 对话存在 %USERPROFILE%\.claude\projects\ 下，拷过去就行。
   界面的设置存在上面说的 ui.json 里。


许可
----
本程序使用 PySide6（LGPL v3）和 Pillow（MIT/HPND）。


────────────────── English ──────────────────


What this is
------------
A small viewer and manager for your Claude Code conversation history.

It reads the conversation files Claude Code stores on your own machine and
lists them in a table you can search, sort, rename, delete, and resume from.


Before you run it
-----------------
1. Claude Code (required)

   This program contains no conversation data of its own; it only reads what
   Claude Code already stored. Without Claude Code installed you will get an
   empty list and a note telling you so.

   Install:
       npm install -g @anthropic-ai/claude-code

   See also: https://claude.ai/code

2. Windows Terminal (optional)

   If present, "Resume" opens the conversation there. Otherwise it falls back
   to the built-in console; either way works.


How to use it
-------------
Double-click "SessionLedger.exe".

  Search box      filter by name / folder / last prompt
  Double-click    resume that conversation in a terminal
  F2              rename
  Delete          delete (asks first)
  Ctrl / Shift    multi-select, delete a batch at once
  Click header    sort by that column
  Right-click?    there is no context menu; everything is on the buttons below

What you can change in "Settings":
  Language        中文 / English
  Theme           follow system / 4 light / 3 dark
  Text contrast   soft / standard / high
  Panel opacity   how much of the background image shows through
  Alternating rows
  Background image

"New Session" starts a conversation in the default workspace you configured.
With "Separate subfolder per session" enabled it also creates a timestamped
subfolder there and asks Claude to put everything from that session inside it.


Where deleted conversations go
------------------------------
Nothing is really deleted. "Delete" only removes a conversation from the list
and from Claude Code's /resume, and moves it into this program's trash.

  Trash → Restore            put it back
  Trash → Delete permanently the file is erased for good
  Trash → Empty the trash    erase everything inside

When cleaning up, delete first and only empty the trash a few days later,
once you are sure.


Where the settings live
-----------------------
  %APPDATA%\claude-session-list\ui.json

  To open that folder: press Win+R, paste %APPDATA%\claude-session-list, Enter.

  **Deleting the program does not delete this file** — your settings survive a
  reinstall.


How to uninstall
----------------
Delete the program folder. This program writes no registry keys, installs no
service, and leaves nothing running.

For a completely clean removal, delete the settings folder above as well.


If something goes wrong
-----------------------
If the program crashes it shows a window telling you where the log is:

  %APPDATA%\claude-session-list\error.log

Send that file to the developer.

If no window appeared at all and no dialog showed up, look for error.log in
that folder anyway.


Troubleshooting
---------------
Q: The list is empty.
A: Either Claude Code is not installed, or it has never been used. Have one
   conversation with it first.

Q: Many rows show only an ID (like 0830fde6) instead of a name.
A: Those conversations have no title yet — Claude Code only generates a title
   after a few exchanges. Nothing is broken; you can still resume them.

Q: Double-clicking opens a terminal that says it cannot find the claude command.
A: The Claude Code CLI is not on your PATH.

Q: I am moving to another computer — can I bring my conversations?
A: Conversations live in %USERPROFILE%\.claude\projects\ — copy that folder.
   The UI settings live in the ui.json mentioned above.


License
-------
This program uses PySide6 (LGPL v3) and Pillow (MIT/HPND).
