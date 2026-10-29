---
name: tool-skill-publish
display_name: 技能市场上架
display_name_en: Skill Marketplace Publishing
description: 把本地 Skill 打包并准备上架到 WorkBuddy 技能市场。当用户说"把 skill 上传到技能市场""发布技能""上架技能""提交技能审核""publish skill to marketplace"时使用。产出：合规的 SKILL.md frontmatter、符合平台结构的 zip 包、逐字段可粘贴的表单填写值、以及必填项自检报告。
description_zh: 把本地 Skill 准备成可提交技能市场的规范包（frontmatter 合规 + zip 结构正确 + 表单值齐全 + 自检）。
description_en: Prepare a local Skill for WorkBuddy marketplace submission — compliant frontmatter, correctly structured zip, ready-to-paste form values and self-checks.
version: 1.0.1
author: hasWhere
category: productivity
agent_created: true
tags: ["skill", "marketplace", "packaging", "publish"]
---

# 技能市场上架

## 0. 先讲清边界（必须先告诉用户）

**技能市场没有 API / CLI，无法由 agent 完成上传。** 唯一路径是开放平台工作台的人工流程：

1. 注册并入驻开放平台（<https://open.workbuddy.cn>）
2. 完成开发者 / 企业资质认证
3. 创建业务类型 = 技能
4. 完善基础信息与能力配置
5. 测试环境调试
6. **提交平台审核**
7. 审核通过后发布上线

所以你的职责 = 把物料准备到"只剩点提交"，然后明确告知用户最后一步必须他本人做。**不要声称已上传。**
应用内的「市场右上角【添加技能】→【创建技能】」是**对话式从零创建**，不能用来上传已有技能，别把它当成上传入口。

## 1. 反推平台 schema（文档没写全，必须实测）

官方文档 <https://open.workbuddy.cn/docs/skill> 只给字段名、不给枚举值。可靠办法是读**本机市场缓存**：

| 用途 | 路径 |
|------|------|
| 市场索引（含所有已上架技能的元数据） | `~/.workbuddy/skills-marketplace/.codebuddy-skill/marketplace.json` |
| 已安装技能实体（可看真实目录结构） | `~/.workbuddy/skills-marketplace/skills/<slug>/` |
| 市场图标 | `~/.workbuddy/skills-marketplace/icons/` |

索引顶层：`name / description / owner / tags_zh / tags_en / skills[]`
单条技能记录：`name / version / description / description_zh / description_en / source / examples_zh / examples_en / tags_zh / tags_en`

**`tags_zh` / `tags_en` 只能取固定 11 个值**（对照表）：

| tags_zh | tags_en |
|---------|---------|
| OPC·一人公司 | OPC · Solo Business |
| 生活服务 | Lifestyle Services |
| 开发工具 | Development Tools |
| 网站部署 | Website Deployment |
| 教育学习 | Education & Learning |
| 投资理财 | Investment & Finance |
| 内容创作 | Content Creation |
| 信息资讯 | News & Information |
| 效率工具 | Productivity Tools |
| 办公协同 | Collaboration |
| 商业运营 | Business Operations |

**`category` 不是严格枚举**（实测存在 capability / productivity / design / media / writing / document-processing / Design Tools / education / finance …）。选择原则：**找市场上最接近的同类型技能，照抄它的值**。用 §4 的脚本先扫一遍。

`_skillhub_meta.json` 是**安装时生成**的（含 `installedAt`），不是上传物，不要自己写。

## 2. SKILL.md frontmatter 规范

官方示例字段 + 实测最小值：

```yaml
---
name: your-skill-name                 # 技能标识，与目录名一致
display_name: 展示名称
display_name_en: Display Name
description: 一句话能力 + 触发词（写全，AI 靠它自动触发）
description_zh: 简短中文介绍
description_en: A Brief English Introduction
category: Design Tools                # 见 §1，照抄同类先例
version: 0.1.0                           # **首次创建一律 0.1.0**，不要默认 1.0.0
author: 合作方名称                      # 必填，须与开放平台认证主体一致
tags: ["标签1", "标签2"]
permissions:                          # 会写文件/联网时建议声明，照 guizang-ppt-skill 先例
  - file_write
  - optional_network_assets
permission_notes_zh: 说明本 Skill 会做什么（写哪些文件、是否联网）。
metadata:
  last_updated: "YYYY-MM-DD"
---
```

必填：`description` / `description_zh` / `description_en` / `version` / `author`
可选：`name` / `allowed-tools` / `disable-model-invocation` / `user-invocable`

> `author` 是唯一必须问用户的字段——**不要猜**，它要和资质认证主体一致，猜错会被审核卡住。
>
> ✅ **本机用户的开发者署名：`hasWhere`**（2026-09-20 确认）。下次直接用它，不必再问。仅在用户明确说"换个署名"时才改。

## 3. 目录结构与打包

官方列举的结构（**注意：不是白名单**）：

```
{skill-name}/
├── SKILL.md          ★ 必须
├── references/       可选，参考资料
├── scripts/          可选，可执行脚本
└── templates/        可选，模板文件
```

**关键认知**：实测 268 个已上架技能里，`assets/` 有 17 个、`prompts/` 6 个、`examples/` 5 个、`docs/` 4 个、`config/` 3 个，还有 `modules/ tests/ agents/ tools/` 等。所以**非标准目录不会被拒**，不必为了"合规"做无谓重命名（重命名会带来改引用、同步副本的连锁风险）。

**打包硬要求：zip 顶层必须是 `{skill-name}/`，不是 `SKILL.md`。** 这是"解析失败"最常见的成因。

```bash
# 在 skill 的【上一级目录】运行
python -c "import shutil; shutil.make_archive('OUT/skill-name-0.1.0','zip','.', 'skill-name')"
```

❌ 不要在 skill 目录内部 `zip -r`——那会让 zip 顶层变成 `SKILL.md`，平台解析失败。

## 4. 开工前的核查脚本（别信记忆，信文件系统）

```python
# 1) 目录真实内容 + 体积（防止索引写到空目录）
import os
B = "skill-name"
for dp, dn, fn in os.walk(B):
    dn[:] = [d for d in dn if d != "__pycache__"]
    for f in sorted(fn):
        p = os.path.join(dp, f)
        print(f"{os.path.getsize(p):>9,}  {p}")
# 空目录检查：zip 会丢掉空目录，别在文档里写"这里有示例"

# 2) 扫同类技能的 category / 结构先例
import json, os, collections
d = json.load(open(os.path.expanduser(
    "~/.workbuddy/skills-marketplace/.codebuddy-skill/marketplace.json"), encoding="utf-8"))
for s in d["skills"]:
    if "关键词" in (s.get("description_zh","")+s.get("description","")):
        print(s["name"], "|", s.get("tags_zh"), "|", s.get("source"))
R = os.path.expanduser("~/.workbuddy/skills-marketplace/skills")
tops = collections.Counter()
for s in os.listdir(R):
    p = os.path.join(R, s)
    if os.path.isdir(p):
        for e in os.listdir(p):
            if os.path.isdir(os.path.join(p, e)): tops[e] += 1
print(tops.most_common(15))   # 用真实分布判断哪种目录名被接受
```

## 5. 打包后必须做的独立自检

**别只验证源目录——要验证 zip 解包后的结果**，因为 zip 会丢空目录、丢隐藏文件、路径可能错层。

一条命令跑完全部检查：

```bash
python scripts/check_package.py "<包.zip>" --src "<开发源目录>" --dst "<安装副本目录>"
# 退出码 0 = 全部通过；1 = 有失败项（失败项逐条列出）
```

**两个容易困惑的点：**

- `--dst` 指**安装副本**目录（市场装完后的那一份）。若技能开发目录本身就在 `~/.workbuddy/skills/<name>/`（用户级技能，本机只有这一份，没有第二副本），把 `--src` 与 `--dst` 指向**同一路径**即可 —— 第 6 组里"副本无多余文件"的检查照样生效，md5 自比对无害。
- 第 5 组找不到 `scripts/check_prototype.py` / `scripts/check.py` 时会**静默跳过**，这不是失败。视觉类 / 模板类技能通常没有业务校验脚本，别误判成"检查没跑"。

**补一层业务断言（可选但强烈建议）**：`check_package.py` 只看结构、frontmatter 和 md5，**看不懂技能承诺的真假**。像"单文件、零 CDN、纯内联 CSS"这类承诺，必须自己解包后断言：扫所有 `assets/*.html` 的 `src=` / `href=` / `url()`，确认没有 `http(s)://` 或协议相对 `//host` 的外链。注意**先把 HTML 注释剥掉再数标签** —— 骨架注释里常写"…都在 `<style>` 里有定义"，朴素正则计数会把注释里的 `<style>` 当成真标签，报出假的不配平。

覆盖 6 组断言：

| # | 检查 | 为什么 |
|---|---|---|
| 1 | zip 顶层唯一目录 + `SKILL.md` 位置正确 | 顶层直接是 `SKILL.md` 是平台解析失败的头号原因 |
| 2 | frontmatter 可解析 + 必填齐全 + **author 非占位符** | 模板留着 `个人开发者` / `YOUR_NAME` 直接提交，审核卡主体一致性 |
| 3 | SKILL.md 里 `` `path/...` `` 引用是否真在包里 | 改过目录结构后最容易出现死引用 |
| 4 | 空目录 / `.pyc` `.tmp` `.bak` 等垃圾文件 | 空目录会导致文档里"声称有内容"却不实 |
| 5 | 跑包内自带校验脚本（自动找 `scripts/check_prototype.py`） | 源目录能过不代表包内能过 |
| 6 | 三方 md5：zip == 开发源 == 安装副本（+ 副本多余文件） | 打包后改过文件却忘了重打，是最隐蔽的错 |

> 改动 `check_package.py` 后跑一次 `python scripts/test_checker_asserts.py` —— 它构造 4 个已知缺陷包，反向断言每条检查必须报错。**从不报错的检查等于没有检查**，回归测试是唯一能发现"检查悄悄失效"的手段。

**等价手写版**（脚本文件不在时参考）：

```python
import zipfile, tempfile, os, re, subprocess, sys, yaml
z = "OUT/skill-name-0.1.0.zip"
tmp = tempfile.mkdtemp()
with zipfile.ZipFile(z) as f: f.extractall(tmp)
root = os.path.join(tmp, "skill-name")

# a) 顶层结构
with zipfile.ZipFile(z) as f:
    assert {n.split("/")[0] for n in f.namelist()} == {"skill-name"}, "顶层目录错了"
    assert "skill-name/SKILL.md" in f.namelist(), "SKILL.md 位置错了"

# b) frontmatter 可解析 + 必填齐全
t = open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
fm = yaml.safe_load(re.match(r"^---\s*\n(.*?)\n---\s*\n", t, re.S).group(1))
missing = [k for k in ["description","description_zh","description_en","version","author"] if not fm.get(k)]
print("必填缺失:", missing or "无")

# c) SKILL.md 里引用的每个文件是否真在包里
for r in sorted(set(re.findall(r"`((?:references|assets|scripts|templates)/[^`]+?\.\w+)`", t))):
    print("OK " if os.path.isfile(os.path.join(root, r)) else "缺失", r)

# d) 跑技能自带的校验脚本（如果有）
for cand in ("scripts/check_prototype.py", "scripts/check.py"):
    p = os.path.join(root, cand)
    if os.path.isfile(p):
        subprocess.run([sys.executable, p, *[os.path.join(root, x) for x in
                         os.listdir(os.path.join(root, "assets")) if x.endswith(".html")]])
```

## 6. 交付物清单

1. **`{skill-name}-{version}.zip`** —— 上架包
2. **图标** —— 市场列表图标，**交付尺寸 512×512**，见 §6.1

### 6.1 图标规格与导出

| 项 | 值 | 说明 |
|---|---|---|
| 交付尺寸 | **512×512 PNG** | 表单图标字段传这个；不要只给 SVG，多数表单不收 |
| 包内文件 | `icon.svg`（矢量母版） | 声明 `width/height="512"`、`viewBox` 保持原始整数坐标（如 `0 0 240 240`），**不要**为了"512"去重算所有坐标 |
| 圆角外 | 透明 | Chrome 参数 `--default-background-color=00000000`，否则圆角外会是黑/白底 |
| 渲染方式 | **4 倍超采样后降采样** | 渲染 2048 → LANCZOS 降到 512。直接渲 512 会让 1px 网格线与细描边落在像素边界上产生锯齿 |

导出脚本已随本 skill 提供：`scripts/make_icon.py`（本机无 cairosvg/svglib，走 Playwright + Chrome 4× 超采样）。

```bash
# Playwright 只装在 anaconda python，必须用它跑
python scripts/make_icon.py icon.svg icon-512.png 512 4
# → 渲染 2048px 后 LANCZOS 降采样到 512；自动断言尺寸 / 模式 RGBA / 四角 alpha=0 / 中心 alpha=255
# → 同时产出 icon-512_sizes.png：512→32px 多尺寸 + 深底对照，人工确认 32px 下仍可辨
# 退出码 0 = 核验通过；1 = 有失败项
```

> 脚本会把 SVG 根标签的 `width`/`height` 换成渲染尺寸、**保留原 viewBox 整数坐标**，所以母线不用为了"512"去重算所有坐标。透明底靠 `page.screenshot(omit_background=True)` + Chrome 启动参数 `--default-background-color=00000000` 双保险。

> 只交付**一个**图标文件进包（`icon.svg`）。包内同时放 svg + png 会让"平台读哪个"出现二义性；位图作为独立的表单上传资产放在工作区根目录。

**核验要求**（生成后必做，不能只靠"生成了"就交付）：

1. 像素尺寸断言 `im.size == (512, 512)`；
2. 四角抽样必须是 `alpha=0`，中心必须 `alpha=255`；
3. 出一张多尺寸核验图（512/256/128/96/64/48/32 + 深底对照），确认 32px 下仍可辨 —— 市场列表里实际展示尺寸很小。

3. **`上传说明_技能市场.md`** —— 含：
   - 边界说明（人工流程、无 API）
   - 表单逐字段填写值（含 `examples_zh/en` 4 条、`tags_zh/en`）
   - **待用户替换的字段清单**（尤其 `author`）
   - 操作步骤（含若要求声明工具白名单，填 `Read, Write, Edit, Glob, Grep, Bash`）
   - 重新打包命令
   - 结构自检对照表
   - 「解析失败」排查：① zip 顶层目录 ② frontmatter 被编辑器破坏 → 定位不了邮件 `openworkbuddy@tencent.com`

## 7. 易错点

| 坑 | 对策 |
|----|------|
| zip 顶层是 `SKILL.md` 而非 `{skill-name}/` | 在上一级目录用 `shutil.make_archive(..., '.', 'skill-name')` |
| `author` 用占位符就交付 | 本机用户署名为 `hasWhere`（见 §2 提示）；换别人时**必须问**。`check_package.py` 会自动检出 `个人开发者` / `YOUR_NAME` / `TODO` 等占位符 |
| 内联 heredoc 跑含 `\s` 的正则 | bash heredoc 传给 Windows Python 时**反斜杠会被吞**：`\s` 变成 `/s`，正则静默失配、返回 `None`，让人误判"文件没改成功"。含反斜杠的代码先写成 `.py` 再跑 |
| 文档里写了实际不存在的目录/文件 | 写索引前先 `os.walk`；空目录 zip 后会消失 |
| 为"合规"把 `assets/` 改名成 `templates/` | 非标准目录被市场接受，改名只会带来改引用+同步副本的连锁风险 |
| 只验证源目录 | 必须解包 zip 再验证结构与引用完整性 |
| 声称"已上传" | 没有 API，只能说"物料已就绪，最后一步需你在开放平台提交" |
| **重定版本号只改了 SKILL.md** | 见下方 §7.1 全套清单，漏一处前后就对不上 |
| **旧版本的 zip 没删** | 提交时极易拿错包。新版打完后**立刻**把 `{skill}-{旧版本}.zip` 删掉（送回收站），别留在同目录 |
| 清理文件后用异常判断成败 | `send2trash` 在部分机器上**操作已成功仍抛 `FileNotFoundError`**。必须用 `os.path.exists()` 复核，不要信异常 |

### 7.1 版本号约定与重定版本号

**首次创建一律用 `0.1.0`**（2026-10-14 用户明确要求）。`1.0.0` 语义上是
"接口已稳定、可放心依赖"，而新技能未经真实用户验证，先标 1.0.0 是虚高。

升版规则：

| 改动 | 升到 |
|---|---|
| 加功能、改触发词或输出格式，向后兼容 | 次版本号（`0.1.0` → `0.2.0`） |
| 改已有行为、可能让用户现有流程失效 | 补丁位或次版本号，**在说明里写清影响** |
| 只修 bug，不改行为 | 补丁位 +1（`0.1.0` → `0.1.1`） |
| 已被真实用户验证、接口冻结 | 才升 `1.0.0` |

**版本号散落多处，只改一处必然前后不一致**：

| 位置 | 说明 |
|---|---|
| `SKILL.md` frontmatter `version` | 权威值 |
| `config.json` `version` | 机器可读副本，必须同步（顺手核对 `author` 等字段是否与 SKILL.md 一致） |
| 上架包文件名 | `{skill-name}-{新版本}.zip`，并删除旧版本的包 |
| 上传说明/交付文档 | 全文替换旧版本号（交付物表、表单字段值、操作步骤、重打包命令、自检对照表 —— 实测一处文档里就有 6 处） |
| 文件名里带版本号的产物 | 如演示页 `演示_xxx_v1.4.html` → 同步改名 |
| 历史开发日志 | **不要改名**（那是史实）；改为**在顶部加"版本号说明"引用块**，声明内部编号与对外发布号的对应关系 |

改完必须复核**两件事**（缺一不可）：

1. 全目录搜索旧版本号 → 应零残留（历史日志里的有意保留除外）；
2. **解包读 zip 内的 SKILL.md**，确认 `version` 与文件名一致。
   只查开发源目录会漏 —— 改完 `SKILL.md` 忘了重打包时，
   源目录与 zip 的 md5 仍然"一致"（两边都是旧的），只有读包内容才能发现。

改完复核：全仓搜索旧版本号（预期只剩历史日志里的有意保留）、包内 `version` 字段、三方 md5。

