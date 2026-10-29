# -*- coding: utf-8 -*-
"""
把成员头像内联成 base64，生成 utils/avatars.js。

背景：`<image src="/images/avatars/xxx.jpg">` 这种本地文件路径在部分运行环境
（预览运行时 / 打包链路）解析失败，导致头像全部显示为破图。内联 base64
后，图片不再依赖任何路径解析，任何环境都能渲染。

微信 <image> 的 src 支持 data:image/jpeg;base64,... （注意不能含换行，
所以下面按定长切块再用 join('') 拼回，既保证单行正确又避免超长行）。
"""

import base64
import io
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, 'images', 'avatars')
OUT_FILE = os.path.join(ROOT, 'utils', 'avatars.js')

# 输出 key 与 store.js 中 AVATARS 的 key 保持一致
MAPPING = [
    ('dad', 'avatar-dad.jpg'),
    ('mom', 'avatar-mom.jpg'),
    ('dabao', 'avatar-son.jpg'),
    ('erbao', 'avatar-baby.jpg'),
    ('grandma', 'avatar-grandma.jpg'),
]

SIZE = 200          # 头像统一 200x200，足够 3x 屏显示
QUALITY = 85
CHUNK = 120         # 每行 base64 字符数


def encode(path):
    """读图 -> 统一尺寸 -> JPEG -> base64（单行、无换行）"""
    img = Image.open(path).convert('RGB')
    if img.size != (SIZE, SIZE):
        img = img.resize((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=QUALITY, optimize=True,
             progressive=False, subsampling=0)
    raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode('ascii')
    # 保险：剔除任何空白字符，微信遇到换行会解析失败
    b64 = ''.join(b64.split())
    return b64, len(raw)


def main():
    header = [
        '// 由 tools/gen_avatars_b64.py 自动生成，请勿手改。',
        '// 头像以 base64 内联，避免运行时对本地文件路径解析不一致导致 <image> 加载失败。',
        '',
    ]
    body = []
    names = []
    total_b64 = 0
    total_raw = 0

    for key, filename in MAPPING:
        path = os.path.join(SRC_DIR, filename)
        if not os.path.exists(path):
            raise SystemExit('缺少素材: %s' % path)
        b64, raw_size = encode(path)
        uri = 'data:image/jpeg;base64,' + b64
        chunks = [uri[i:i + CHUNK] for i in range(0, len(uri), CHUNK)]
        body.append('const %s = [' % key)
        for c in chunks:
            body.append("  '%s'," % c)
        body.append("].join('')")
        body.append('')
        names.append(key)
        total_b64 += len(uri)
        total_raw += raw_size
        print('  %-8s %s  jpeg=%d B  base64=%d B  行数=%d'
              % (key, filename, raw_size, len(uri), len(chunks)))

    tail = ['module.exports = {']
    for n in names:
        tail.append('  %s: %s,' % (n, n))
    tail.append('}')

    text = '\n'.join(header + body + tail) + '\n'
    with io.open(OUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)

    print('')
    print('输出: %s' % OUT_FILE)
    print('原图合计 %.1f KB -> base64 合计 %.1f KB，文件 %.1f KB'
          % (total_raw / 1024.0, total_b64 / 1024.0,
             os.path.getsize(OUT_FILE) / 1024.0))
    print('单行最长 %d 字符' % max(len(l) for l in text.split('\n')))


if __name__ == '__main__':
    main()
