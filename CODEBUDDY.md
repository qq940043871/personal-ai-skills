# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## What this repository is

A personal **skill library**, not an application. Each top-level directory is one independently loadable agent skill: its name equals the `name` field in `SKILL.md`, and the checkout sits at `~/.agents/skills`, so edits are live with no install step. Docs and skill bodies are written in Chinese; keep them that way.

There is no monorepo tooling — no root `package.json`, build, lint, or test runner. All validation is per-skill scripts checked in next to the skill.

## Taxonomy and routing

Skill names below are short forms; the real directory is prefix + name (e.g. `dev-avue-design`, `html-manage-pages`).

| Prefix | Role | Skills |
|---|---|---|
| `dev-` | development workflows and reference knowledge | `avue-design` (Avue v3.8.2 reference set), `feature-scaffold` (clarify → blueprint → code), `godot-zero-asset-game`, `jvm-triage`, `mipad-landscape`, `uniapp-to-miniprogram`, `web-stress-test` |
| `html-` | enterprise HTML prototypes: one generic base plus quadrant specializations | `prototype-base`, `architecture-design` (01-design), `manage-pages` (02-manage), `client-pages` (03-client), `mobile-pages` (04-mobile), `b2b-portal`, `app-workbench` |
| `visual-` | single-file HTML visuals plus headless export | `arch-diagram`, `diagram-suite`, `echarts-dashboard`, `threejs-scene`, `digital-twin`, `real-twin` |
| `tool-` | runnable automation utilities | `skill-publish`, `book-learning`, `b2b-bid-expert`, `b2b-business-expert`, `kb-audit-repair`, `wechat-jobs-monitor`, `yuque-export`, `daily-checkin`, `trae-checkin`, `electron-gui-click`, `remove-watermark` |
| — | standalone end-to-end workflows | `h5-app-packaging`, `prod-triage` |

Cross-skill routing (misrouting is the most common error):

- Diagrams: `visual-diagram-suite` is the type selector; `visual-arch-diagram` is only for layer-band architecture (no connectors).
- 3D: `visual-digital-twin` = ready-made dashboards (city / factory / port / refinery); `visual-threejs-scene` = build or customize a scene; `visual-real-twin` = Blender/GLB asset pipeline feeding either.
- HTML prototypes: use the matching quadrant skill; fall back to `html-prototype-base` when none matches.
- JVM incidents: `prod-triage` embeds a copy of `dev-jvm-triage`.

## Skill anatomy

```
<skill-name>/
├── SKILL.md        required: YAML frontmatter + the workflow itself
├── references/     deep docs, loaded on demand
├── assets/         copyable skeletons, templates, data
├── scripts/        runnable tooling (Python / Node / Java / shell)
└── templates/, config/   optional
```

- `SKILL.md` is the always-loaded index; heavy detail belongs in `references/` behind an explicit "read this when" table (see `dev-avue-design`, `html-b2b-portal`).
- The frontmatter `description` is the trigger surface. Chinese trigger phrases in it decide when the skill fires, so treat edits there as behaviour changes.
- In generator skills, `assets/` files are copied **into the user's project**, not used in place: `dev-uniapp-to-miniprogram/assets/{validate.py,selftest.js}` become the generated project's `tools/`; `h5-app-packaging/assets/*.template.mjs` become its build scripts.
- `html-b2b-portal/config.json` is the only machine-readable metadata mirror (version, author, industries, components). Mirror any SKILL.md metadata change there.
- Frontmatter conventions for publishing: required `description` / `description_zh` / `description_en` / `version` / `author`; first release is `0.1.0`; author is `hasWhere` unless the user overrides. Full rules in `tool-skill-publish/SKILL.md` §2.

## Commands (run from the repo root)

Marketplace packaging and its own regression test:

```bash
python tool-skill-publish/scripts/check_package.py <pkg.zip> --src <skill-dir> --dst <installed-copy>
python tool-skill-publish/scripts/test_checker_asserts.py
python tool-skill-publish/scripts/make_icon.py icon.svg icon-512.png 512 4
```

`check_package.py` exits 0 only when all six groups pass (zip top-level shape, frontmatter/placeholders, referenced-file existence, junk files, bundled self-check, three-way md5). Build the zip from the **parent** directory so the archive has a single `<skill-name>/` top level.

Diagrams and 2D dashboards:

```bash
python visual-arch-diagram/scripts/export_png.py 图.html --out 图.png
python visual-diagram-suite/scripts/export_png.py 图.html --out 图.png
python visual-echarts-dashboard/scripts/scaffold.py --industry bulk --title "XX驾驶舱" --out dash.html
python visual-echarts-dashboard/scripts/smoke_headless.py dash.html --size 1920x1080 --expect-panels 10 --shot preview.png
```

3D twin scenes:

```bash
python visual-digital-twin/scripts/build_twin.py --scene city --out out.html   # --engine classic | --offline | --config cfg.json
python visual-digital-twin/scripts/verify_screen.py out.html --shot out.png
python visual-threejs-scene/scripts/scaffold.py --list
python visual-threejs-scene/scripts/scaffold.py --scene warehouse --out twin.html
python visual-threejs-scene/scripts/smoke_headless.py twin.html --shot preview.png
```

HTML prototype gate:

```bash
python html-b2b-portal/scripts/check_prototype.py 原型.html [更多.html...]
```

Book learning site and knowledge-base audit:

```bash
python tool-book-learning/scripts/audit_notes.py --book <dir> --profile tech
python tool-book-learning/scripts/build_site.py --book <dir> --profile tech
python tool-book-learning/scripts/verify_site.py <built-site args>
python tool-kb-audit-repair/scripts/verify_kb.py --root <dir> [--json]
```

JVM evidence gathering (runs on the target host, not locally):

```bash
./dev-jvm-triage/scripts/jvm_diag.sh <pid> [--dump] [--out <dir>]
python dev-jvm-triage/scripts/scan_bytecode.py <jar-root> --sizes 32 --types short,int
javac -encoding UTF-8 dev-jvm-triage/scripts/HprofHistogram.java && java -Xmx1g HprofHistogram heap.hprof out.csv
```

Interpreter note: Playwright, PDF, and OCR scripts must run under the Python that actually has Playwright + PyMuPDF/RapidOCR installed (the docs call it "anaconda"). Plain `python` may be a different, minimal interpreter; standard-library-only scripts (`audit_notes`, `build_site`, `check_package`, `validate`) are safe anywhere.

## Conventions

- **Byte preservation**: `.gitattributes` sets `* -text`. Do not let git or editors normalise line endings, and keep binary assets (images, GLB, fonts) intact.
- **Output location**: skills write deliverables into a user-specified project directory, never into the skill directory. Deliverables are generally a single self-contained HTML file plus an exported PNG.
- **CDN stance differs by family, deliberately**: `visual-*` and `html-app-workbench` are zero-CDN and fully inlined so they open offline; `html-prototype-base` and its quadrants intentionally use Tailwind/Chart.js CDNs with no build step; `html-b2b-portal` may use CDNs but must degrade gracefully.
- **Version discipline**: `0.1.0` for a first release. The version appears in `SKILL.md`, `config.json` where present, the zip filename, and delivery docs — bump them together, then grep the whole skill for the old value.
- **`tool-wechat-jobs-monitor` is personal-use only** per its `NOTICE.md`. Never package, publish, or redistribute it.
- Verification is expected to be mechanical: the repo's habit is a runnable checker per skill, plus a regression test that proves the checker still fails on known-bad input.

## Consistency hazards

- `prod-triage/scripts/jvm/` is a byte-identical copy of `dev-jvm-triage/scripts/` (the skill was merged in). Change both or deliberately diverge.
- `visual-arch-diagram/scripts/export_png.py` and `visual-diagram-suite/scripts/export_png.py` share a CLI but are **not** identical files.
- The `html-*` skills document an external prototype workspace (`01-design/`, `02-manage/`, `03-client/`, `04-mobile/`) that does not exist in this repo; do not go looking for those directories here.
- Skills refer to each other by name (`arch-diagram` ↔ `diagram-suite`, `digital-twin` ↔ `threejs-scene` ↔ `real-twin`, `prod-triage` ↔ `jvm-triage`). Renaming or deleting a skill requires a repo-wide grep for its name, including other SKILL.md files' routing tables.
