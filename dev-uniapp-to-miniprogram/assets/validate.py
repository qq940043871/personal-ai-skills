"""小程序工程自检：JSON 语法、页面文件齐备、组件引用可解析、tabBar 图标存在、WXML 标签闭合、包体积。"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS = []
WARNINGS = []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def rel(p):
    return os.path.relpath(p, ROOT).replace('\\', '/')


# ---------- 1. JSON 语法 ----------
json_files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    if 'node_modules' in dirpath:
        continue
    for f in filenames:
        if f.endswith('.json'):
            json_files.append(os.path.join(dirpath, f))

for path in sorted(json_files):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            json.load(fh)
    except Exception as e:
        err('JSON 解析失败 %s: %s' % (rel(path), e))

# ---------- 2. app.json 页面齐备 ----------
app_json_path = os.path.join(ROOT, 'app.json')
app = {}
if os.path.exists(app_json_path):
    with open(app_json_path, 'r', encoding='utf-8') as fh:
        app = json.load(fh)
else:
    err('缺少 app.json')

for page in app.get('pages', []):
    for ext in ('.js', '.json', '.wxml', '.wxss'):
        p = os.path.join(ROOT, page + ext)
        if not os.path.exists(p):
            err('页面文件缺失: %s' % rel(p))

# ---------- 3. tabBar 图标 ----------
for item in app.get('tabBar', {}).get('list', []):
    for key in ('iconPath', 'selectedIconPath'):
        if key in item:
            p = os.path.join(ROOT, item[key])
            if not os.path.exists(p):
                err('tabBar 图标缺失: %s' % item[key])
            elif os.path.getsize(p) > 40 * 1024:
                err('tabBar 图标超过 40KB: %s' % item[key])

# ---------- 4. usingComponents 引用 ----------
for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        if not f.endswith('.json'):
            continue
        path = os.path.join(dirpath, f)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            continue
        comps = data.get('usingComponents') or {}
        for tag, target in comps.items():
            if target.startswith('/'):
                base = os.path.join(ROOT, target.lstrip('/'))
            else:
                base = os.path.normpath(os.path.join(dirpath, target))
            ok = False
            for ext in ('.js', '.json', '.wxml'):
                if os.path.exists(base + ext):
                    ok = True
                    break
            if not ok:
                err('组件不存在: %s -> %s (在 %s)' % (tag, target, rel(path)))

# ---------- 5. WXML 标签闭合 ----------
VOID_TAGS = {'image', 'input', 'icon', 'progress', 'import', 'include', 'wxs', 'slot',
             'checkbox', 'radio', 'switch', 'slider', 'audio', 'video', 'camera', 'canvas',
             'live-player', 'live-pusher', 'open-data', 'navigator', 'web-view'}
TAG_RE = re.compile(r'<(/?)([a-zA-Z][\w-]*)([^<>]*?)(/?)>', re.S)

for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        if not f.endswith('.wxml'):
            continue
        path = os.path.join(dirpath, f)
        with open(path, 'r', encoding='utf-8') as fh:
            src = fh.read()
        src = re.sub(r'<!--.*?-->', '', src, flags=re.S)
        # 先把引号内的属性值遮蔽掉，否则 wx:if="{{a <= 4}}" 里的 '<' '>' 会被当成标签
        def mask_attr(m):
            s = m.group(0)
            return s[0] + ' ' * (len(s) - 2) + s[-1]
        masked = re.sub(r'"[^"]*"', mask_attr, src)
        masked = re.sub(r"'[^']*'", mask_attr, masked)
        stack = []
        for m in TAG_RE.finditer(masked):
            closing, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
            if closing:
                if not stack:
                    err('WXML %s: 多余的闭合标签 </%s>' % (rel(path), tag))
                elif stack[-1][0] != tag:
                    err('WXML %s: 标签未正确嵌套，期望 </%s> 实际 </%s>'
                        % (rel(path), stack[-1][0], tag))
                    stack.pop()
                else:
                    stack.pop()
            else:
                if selfclose or tag in VOID_TAGS:
                    continue
                stack.append((tag, m.start()))
        for tag, pos in stack:
            line = src[:pos].count('\n') + 1
            err('WXML %s: 第 %d 行 < %s > 未闭合' % (rel(path), line, tag))

# ---------- 6. WXSS 花括号配平 ----------
for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        if not f.endswith('.wxss'):
            continue
        path = os.path.join(dirpath, f)
        with open(path, 'r', encoding='utf-8') as fh:
            src = fh.read()
        stripped = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
        if stripped.count('{') != stripped.count('}'):
            err('WXSS %s: 花括号不配平 {=%d }=%d'
                % (rel(path), stripped.count('{'), stripped.count('}')))

# ---------- 7. 体积统计（遵循 project.config.json 的 packOptions.ignore） ----------
IGNORED_DIRS = set()
IGNORED_FILES = set()
cfg_path = os.path.join(ROOT, 'project.config.json')
if os.path.exists(cfg_path):
    try:
        with open(cfg_path, 'r', encoding='utf-8') as fh:
            cfg = json.load(fh)
        for rule in (cfg.get('packOptions', {}) or {}).get('ignore', []) or []:
            value = str(rule.get('value', '')).strip().strip('/').replace('\\', '/')
            if not value:
                continue
            if rule.get('type') == 'folder':
                IGNORED_DIRS.add(value)
            else:
                IGNORED_FILES.add(value)
    except Exception as e:
        warn('读取 project.config.json 打包忽略规则失败: %s' % e)


def is_packed(relpath):
    """该相对路径是否会被打进小程序包（被 packOptions.ignore 排除的不算）。"""
    if relpath in IGNORED_FILES:
        return False
    for d in IGNORED_DIRS:
        if relpath == d or relpath.startswith(d + '/'):
            return False
    return True


total = 0
excluded = 0
largest = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    if 'node_modules' in dirpath:
        continue
    for f in filenames:
        p = os.path.join(dirpath, f)
        size = os.path.getsize(p)
        if not is_packed(rel(p)):
            excluded += size
            continue
        total += size
        largest.append((size, rel(p)))
largest.sort(reverse=True)

print('=== 包体统计（已按 packOptions.ignore 排除） ===')
print('参与打包的文件数: %d' % len(largest))
for size, name in largest[:8]:
    print('  %8d B  %s' % (size, name))
print('打包体积: %.1f KB (主包限制 2048 KB)' % (total / 1024.0))
if excluded:
    print('已排除(不打入包): %.1f KB%s'
          % (excluded / 1024.0, ('  [' + ', '.join(sorted(IGNORED_DIRS)) + ']') if IGNORED_DIRS else ''))

if total > 2048 * 1024:
    err('主包体积超限: %.1f KB > 2048 KB' % (total / 1024.0))

if WARNINGS:
    print('\n=== 警告 (%d) ===' % len(WARNINGS))
    for w in WARNINGS:
        print('  ! ' + w)

if ERRORS:
    print('\n=== 错误 (%d) ===' % len(ERRORS))
    for e in ERRORS:
        print('  X ' + e)
    sys.exit(1)
else:
    print('\n校验通过，未发现问题。')
