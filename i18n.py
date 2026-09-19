"""界面文字的中英对照。

**中文原文本身就是键** —— 不另起一套 key 名。好处有三：
  1. 不用维护「key ↔ 中文」的对照表，少一处会对不上的地方
  2. 漏翻时直接回落成中文，界面上永远不会出现 `search.label` 这种东西
  3. 读代码时一眼能看出这句显示的是什么

用法：把界面字符串包一层 T()，需要格式化的照常接 %：

    self.setWindowTitle(T("会话簿"))
    label.setText(T("%d 个对话") % n)

不在 EN 里的字符串原样返回 —— 所以加新文案时忘了翻译，也只是那一句是中文，
不会崩、不会出现空白。
"""

LANG = "zh"

EN = {
    '会话簿':
        'SessionLedger',
    '会话簿 %s　·　© 2026 %s　·　MIT 许可':
        'SessionLedger %s　·　© 2026 %s　·　MIT License',
    '设置':
        'Settings',
    '回收站':
        'Trash',
    '回收站 (%d)':
        'Trash (%d)',
    '回收站 —— 已删除的对话':
        'Trash — deleted conversations',
    '搜索':
        'Search',
    '刷新':
        'Refresh',
    '搜索名字 / 文件夹 / 最后提问…（Ctrl+F）':
        'Search name / folder / last prompt… (Ctrl+F)',
    '名字':
        'Name',
    '文件夹':
        'Folder',
    '最后活动':
        'Last active',
    '条数':
        'Turns',
    '原文件夹':
        'Original folder',
    '删除时间':
        'Deleted',
    '双击行：接着聊\u3000·\u3000F2：改名\u3000·\u3000Delete：删除\u3000·\u3000Ctrl / Shift 点击：多选\u3000·\u3000点击表头：排序':
        'Double-click: resume\u3000·\u3000F2: rename\u3000·\u3000Delete: remove\u3000·\u3000Ctrl / Shift click: multi-select\u3000·\u3000Click header: sort',
    '接着聊':
        'Resume',
    '改名':
        'Rename',
    '删除':
        'Delete',
    '复制命令':
        'Copy command',
    '共 %d 个对话 · %.0f MB%s':
        '%d conversations · %.0f MB%s',
    '  ·  筛出 %d 个':
        '  ·  %d matched',
    '  ·  %d 个无法读取标题':
        '  ·  %d unreadable',
    '正在读取记录…':
        'Reading records…',
    '读取记录出错':
        'Failed to read records',
    '无法读取对话名称':
        'Unreadable conversation titles',
    '%d 个对话无法读取标题（占多数），列表中仅显示编号。\n\n通常是因为 Claude Code 更改了记录文件格式，本工具需要相应更新。\n\n这些对话本身未受影响：文件内容未被修改，只是无法显示标题。':
        '%d conversations have unreadable titles (most of them). Only their IDs can be shown.\n\nThis usually means Claude Code changed its record format and this tool needs to catch up.\n\nThe conversations themselves are unaffected: no file was modified, the titles simply cannot be read.',
    '最后问：':
        'Last prompt: ',
    '最后问： ':
        'Last prompt: ',
    '目录 ':
        'Folder ',
    '分支 ':
        'Branch ',
    '改过名':
        'renamed',
    '   （文件已不存在）':
        '   (file missing)',
    '请先选择一项':
        'Select an item first',
    '请先选择一个对话':
        'Select a conversation first',
    '已选中 %d 个对话。「删除」将一次全部移入回收站（会先询问），「复制命令」每行输出一条。':
        '%d conversations selected. Delete moves them all to the trash at once (you will be asked first); Copy command outputs one per line.',
    '已在新窗口打开（目录 %s）':
        'Opened in a new window (folder %s)',
    '无法打开':
        'Cannot open',
    '已复制 %d 条命令（每行一条）':
        'Copied %d commands (one per line)',
    '已复制：claude --resume ':
        'Copied: claude --resume ',
    '已将 %d 个对话移入回收站':
        'Moved %d conversations to the trash',
    '已移入回收站':
        'Moved to the trash',
    '有 %d 个未能删除':
        '%d could not be deleted',
    '提示':
        'Notice',
    '将这个对话移入回收站？\n\n%s\n\n（在官方 /resume 中也将不可见；如需撤销，可在回收站中恢复）':
        'Move this conversation to the trash?\n\n%s\n\n(It will also be hidden from /resume. You can restore it from the trash later.)',
    '将这 %d 个对话移入回收站？\n\n%s\n\n（在官方 /resume 中也将不可见；如需撤销，可在回收站中恢复）':
        'Move these %d conversations to the trash?\n\n%s\n\n(They will also be hidden from /resume. You can restore them from the trash later.)',
    '这 %d 个对话的文件将被永久删除，无法恢复。\n确定继续吗？':
        'The files for these %d conversations will be permanently deleted. Continue?',
    '\n… 还有 %d 个':
        '\n… and %d more',
    '部分对话未能恢复':
        'Some conversations could not be restored',
    '这些对话已从列表中移除，在官方 /resume 中也无法看到。\n彻底删除的文件无法恢复。':
        'These conversations have been removed from the list and are no longer visible in /resume.\nFiles deleted permanently cannot be recovered.',
    '恢复':
        'Restore',
    '彻底删除':
        'Delete permanently',
    '清空回收站':
        'Empty the trash',
    '回收站为空':
        'The trash is empty',
    '其中 %d 个对话的文件将被永久删除，无法恢复。\n确定继续吗？':
        'The files for the %d conversations inside will be permanently deleted. Continue?',
    '回收站中找不到该文件':
        'That file is no longer in the trash',
    '原位置已存在同名文件，未覆盖':
        'A file with that name already exists at the original location; not overwritten',
    '新名字：':
        'New name:',
    '名字不能为空':
        'The name cannot be empty',
    '改名失败':
        'Rename failed',
    '已重命名 —— 官方 /resume 中也会显示新名称':
        'Renamed — the new name will also appear in /resume',
    '新建对话':
        'New Session',
    '迁移工作区':
        'Move workspace',
    '选择新的工作区':
        'Choose the new workspace',
    '有对话正在使用中':
        'Some conversations are in use',
    '以下对话正在使用中，请先关闭再迁移：\n\n%s':
        'The following conversations are in use; close them before migrating:\n\n%s',
    '所选对话已在此工作区中':
        'The selected conversations are already in this workspace.',
    '将以下 %d 个对话的工作区改为：\n\n%s\n\n%s\n\n'
    '将改写对话文件中记录的路径，并把文件移至新目录对应的项目文件夹。\n'
    '原文件会先完整备份到配置目录的 migrate_backup/ 下。':
        'Change the workspace of the following %d conversations to:\n\n%s\n\n%s\n\n'
        'This rewrites the paths stored in the conversation files and moves them to the\n'
        'project folder for the new directory.\n'
        'The original files are backed up to migrate_backup/ in the config directory first.',
    '部分对话迁移失败':
        'Some conversations failed to migrate.',
    '迁移完成 %d 个，失败 %d 个':
        'Moved %d, failed %d',
    '已迁移 %d 个对话到 %s':
        'Moved %d conversations to %s',
    '没有对话被迁移':
        'No conversations were moved',
    '对话文件不存在': 'The session file does not exist',
    '没指定目标目录': 'No target folder given',
    '工作区没变': 'The workspace is unchanged',
    '目标目录不存在': 'The target folder does not exist',
    '备份失败，已中止：%s': 'Backup failed, aborted: %s',
    '改写失败，原文件没动：%s': 'Rewrite failed; the original was left untouched: %s',
    '目标文件夹里已经有同 ID 的对话了':
        'The target folder already contains a conversation with the same ID',
    '移动文件失败：%s': 'Failed to move the file: %s',
    '已改 %d 处记录，文件移到 %s':
        'Rewrote %d records; moved the file to %s',
    '打开目录':
        'Open folder',
    '默认工作区':
        'Default workspace',
    '常规':
        'General',
    '当前图片':
        'Current image',
    '暂不适用':
        'N/A',
    '外观':
        'Appearance',
    '每次对话使用独立子目录':
        'Separate subfolder per session',
    '并为它建立一个独立的产出子目录（以时间戳命名）':
        'and create a separate output subfolder for it, named after the timestamp',
    '已在新窗口新建对话（目录 %s，产出目录 %s/）':
        'New session started in a new window (folder %s; output folder %s/)',
    '尚未设置 —— 点击右侧「选择…」，或直接粘贴路径':
        'Not set — click Choose…, or paste a path in',
    '选择…':
        'Choose…',
    '选择默认工作区':
        'Choose a default workspace',
    '尚未设置默认工作区':
        'No default workspace yet',
    '请在「设置」中选择一个目录。':
        'Choose a directory in Settings.',
    '在 %s 中新建一个 Claude Code 对话':
        'Start a new Claude Code session in %s',
    '尚未设置默认工作区 —— 请在「设置」中选择':
        'No default workspace — choose one in Settings',
    '已在新窗口新建对话（目录 %s）':
        'New session started in a new window (folder %s)',
    '目录不存在':
        'Folder not found',
    '找不到默认工作区：\n\n%s\n\n请在「设置」中重新选择。':
        'The default workspace is missing:\n\n%s\n\nPlease choose a new one in Settings.',
    '找不到此对话的目录：\n\n%s':
        'The folder for this conversation is missing:\n\n%s',
    '打不开这个目录：\n\n%s':
        'Could not open this folder:\n\n%s',
    '（无记录）':
        '(not recorded)',
    '已选择 %d 个，打开第一个的目录：%s':
        '%d selected — opening the folder of the first one: %s',
    '语言':
        'Language',
    '主题':
        'Theme',
    '跟随系统':
        'Follow system',
    '浅色 · ':
        'Light · ',
    '深色 · ':
        'Dark · ',
    '文字对比':
        'Text contrast',
    '柔和':
        'Soft',
    '标准':
        'Standard',
    '高对比':
        'High',
    '面板不透明度':
        'Panel opacity',
    '几乎全透明':
        'almost clear',
    '很透明':
        'very clear',
    '半透明':
        'translucent',
    '偏实':
        'mostly solid',
    '接近实心':
        'nearly solid',
    '隔行深浅交替':
        'Alternating row shading',
    '背景图':
        'Background image',
    '（当前未设置背景）':
        '(no background image set)',
    '淡化':
        'Fade',
    '柔化':
        'Soften',
    '关闭':
        'Close',
    '选择图片…':
        'Choose image…',
    '移除背景':
        'Remove background',
    '选择背景图':
        'Choose a background image',
    '图片 (*.jpg *.jpeg *.png *.gif *.bmp *.webp);;所有文件 (*)':
        'Images (*.jpg *.jpeg *.png *.gif *.bmp *.webp);;All files (*)',
    '珠光':
        'Pearl',
    '暖纸':
        'Warm Paper',
    '雾灰':
        'Mist',
    '晨曦':
        'Dawn',
    '午夜':
        'Midnight',
    '极夜':
        'Polar',
    '熔岩':
        'Magma',
    '会话簿 —— 出错了':
        'SessionLedger — Error',
    '程序遇到错误，详情已记录到日志。\n\n日志位置：\n%s\n\n如果反复出现，请将日志文件发送给开发者。':
        'The program encountered an error. Details were written to the log:\n\n%s\n\nIf this keeps happening, please send the log file to the developer.',
    '未找到对话记录':
        'No conversations found',
    '未找到 Claude Code 的对话记录。\n\n本程序读取的是 Claude Code 存储在本机的对话，\n因此需要先安装 Claude Code 并至少使用过一次。\n\n安装方法：npm install -g @anthropic-ai/claude-code\n或参考 https://claude.ai/code':
        'No Claude Code conversations were found.\n\nThis app reads Claude Code conversations stored on this machine, so Claude Code\nmust be installed and used at least once.\n\nInstall: npm install -g @anthropic-ai/claude-code\nOr see https://claude.ai/code',
    '刚刚':
        'just now',
    '%d 分钟前':
        '%d min ago',
    '%d 小时前':
        '%d h ago',
    '昨天 ':
        'Yesterday ',
    '%d 天前':
        '%d d ago',
    '「接着聊」目前只支持 Windows':
        '"Resume" is currently Windows-only',
}


def set_lang(code):
    """code: "zh" / "en"。其他值一律当中文。"""
    global LANG
    LANG = "en" if code == "en" else "zh"


def get_lang():
    return LANG


def T(zh, **kw):
    """把中文原文换成当前语言。查不到就原样返回（且不报错）。

    带 %s / %d 的照常：T("%d 个对话") % n
    """
    s = EN.get(zh, zh) if LANG == "en" else zh
    return s % kw if kw else s
