#!/usr/bin/env python3
"""scan_bytecode.py — 反查 `new <type>[<size>]` 字节码分配点。

给定一个解包后的 jar 根目录（Spring Boot fat jar 解压后含 BOOT-INF/classes
与 BOOT-INF/lib；也支持任意含 .class/.jar 的目录树），按 JVM 字节码规范匹配
「定长数组分配」指令序列，输出候选分配类。用于堆直方图发现「同长度海量基本
类型数组」指纹后，回到代码定位嫌疑分配点。

用法:
    python scan_bytecode.py <root> [--sizes 32] [--types short,int]

匹配的指令模式（JVMS）:
    iconst_<n> (n=0..5)  /  bipush <n> (6..127)  /  sipush <n> (128..32767)
    后跟 newarray <atype>

注意: 输出是「候选」不是定论——库类也可能命中（如 Tomcat HPACK、xmlbeans），
必须与 jstack 业务线程、堆里的对象上下文互证。
"""
import argparse
import os
import zipfile
from collections import Counter

ATYPE = {'boolean': 4, 'byte': 8, 'char': 5, 'float': 6,
         'double': 7, 'short': 9, 'int': 10, 'long': 11}

NEWARRAY = b'\xbc'


def pattern_for(size, atype):
    """`push <size>` + `newarray <atype>` 的字节序列。"""
    if 0 <= size <= 5:
        push = bytes([0x01 if size == 0 else 0x03 + size])      # iconst_0 / iconst_1..5
    elif size <= 127:
        push = b'\x10' + bytes([size])                          # bipush
    elif size <= 32767:
        push = b'\x11' + size.to_bytes(2, 'big')                # sipush
    else:
        raise ValueError(f'size {size} > 32767 not supported (ldc/wide needed)')
    return push + NEWARRAY + bytes([atype])


def patterns_for(sizes, types):
    pats = {}
    for t in types:
        at = ATYPE[t]
        for s in sizes:
            pats[pattern_for(s, at)] = f'new {t}[{s}]'
    return pats


def iter_classes(root):
    """yield (name, bytes)：根目录下全部 .class + 任意深度嵌套 jar 内的 .class。"""
    for dp, _, files in os.walk(root):
        for f in sorted(files):
            p = os.path.join(dp, f)
            if f.endswith('.class'):
                try:
                    with open(p, 'rb') as fh:
                        yield os.path.relpath(p, root), fh.read()
                except OSError as e:
                    print(f'ERR {p}: {e}')
            elif f.endswith('.jar'):
                try:
                    with zipfile.ZipFile(p) as z:
                        rel = os.path.relpath(p, root)
                        for n in z.namelist():
                            if n.endswith('.class'):
                                yield f'{rel}!{n}', z.read(n)
                except Exception as e:
                    print(f'ERR {p}: {e}')


def main():
    ap = argparse.ArgumentParser(description='scan bytecode for fixed-size primitive array allocation')
    ap.add_argument('root', help='解包后的 jar 根目录（含 BOOT-INF 或任意 class 树）')
    ap.add_argument('--sizes', default='32', help='逗号分隔的数组长度，如 32 或 256,32')
    ap.add_argument('--types', default='short,int', help='逗号分隔，可选: ' + ','.join(ATYPE))
    args = ap.parse_args()

    sizes = [int(x) for x in args.sizes.split(',') if x.strip()]
    types = [t.strip() for t in args.types.split(',') if t.strip()]
    for t in types:
        if t not in ATYPE:
            ap.error(f'unknown type: {t} (choose from {",".join(ATYPE)})')
    if not os.path.isdir(args.root):
        ap.error(f'root not a directory: {args.root}')

    pats = patterns_for(sizes, types)
    hits = Counter()
    total = Counter()

    for name, data in iter_classes(args.root):
        for pat, label in pats.items():
            if pat in data:
                print(f'{label}\t{name}')
                hits[label] += 1
            total[label] += 0  # placeholder keeps Counter ordered below

    print('\n=== SUMMARY ===')
    for label in sorted(hits):
        print(f'{label}: {hits[label]} class(es) matched')
    if not hits:
        print('no candidate allocation sites found — '
              'the arrays may come from Arrays.copyOf / runtime-sized allocation')


if __name__ == '__main__':
    main()
