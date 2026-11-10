# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## What this repository is

A personal **skill library**, not an application. Each top-level directory is one independently loadable agent skill: its name equals the `name` field in `SKILL.md`, and the checkout sits at `~/.agents/skills`, so edits are live with no install step. Docs and skill bodies are written in Chinese; keep them that way.

There is no monorepo tooling — no root `package.json`, build, lint, or test runner. All validation is per-skill scripts checked in next to the skill.

## Taxonomy and routing

Skill names below are short forms; the real directory is prefix + name (e.g. `dev-mipad-landscape`, `html-prototype-base`).

| Prefix | Role | Skills |
|---|---|---|
| `dev-` | development workflows and reference knowledge | `godot-zero-asset-game`, `mipad-landscape`, `prod-triage` (incident triage + JVM forensics), `uniapp-to-miniprogram`, `web-stress-test` |
| `html-` | enterprise HTML prototypes | `prototype-base` (base framework **plus** all four quadrants: `references/01-design-architecture.md`, `02-manage-pages.md`, `03-client-pages.md`, `04-mobile-pages.md`), `b2b-portal` (portal prototypes **plus** clarify → blueprint → code feature scaffolding) |
| `visual-` | single-file HTML visuals plus headless export | `arch-diagram`, `diagram-suite`, `echarts-dashboard`, `threejs-scene` (incl. Blender/GLB asset pipeline), `digital-twin`, `digital-sandbox` (raised terrain slab, layer toggles, section clipping, timeline) |
| `tool-` | runnable automation utilities | `skill-publish`, `book-learning`, `b2b-bid-expert`, `b2b-business-expert`, `wechat-jobs-monitor`, `yuque-export`, `checkin-zcode`, `check-trae`, `electron-gui-click` |
| — | standalone end-to-end workflows | `html-app-packaging` |

Cross-skill routing (misrouting is the most common error):

- Diagrams: `visual-diagram-suite` is the type selector; `visual-arch-diagram` is only for layer-band architecture (no connectors).
- 3D: `visual-digital-twin` = ready-made dashboards (city / factory / port / refinery); `visual-threejs-scene` = build or customize a scene, including the Blender MCP → GLB asset pipeline that replaced `visual-real-twin` (now absorbed); `visual-digital-sandbox` = the terrain slab is the subject (漫游 / 图层点亮 / 剖切 / 推演) rather than the KPI panels.
- HTML prototypes: always `html-prototype-base`; the quadrant (01-design / 02-manage / 03-client / 04-mobile) is chosen via its routing table and its matching `references/*.md` file, not via a separate skill. `html-b2b-portal` stays separate.
- B2B portals vs. one-line feature requests: both live in `html-b2b-portal` — §3 path A (5-step portal prototype) for page-shape requests, §3 path B (`references/feature-scaffold.md`: clarify → L/P/D/M/R layout blueprint → prototype or Vue/Java code) for "我要开发一个 XX 功能". There is no `dev-feature-scaffold` anymore.
- JVM incidents: only `dev-prod-triage` (its `references/04-jvm-offline.md` + `scripts/jvm/` own the whole subject; `dev-jvm-triage` is gone).

## Skill anatomy

```
<skill-name>/
├── SKILL.md        required: YAML frontmatter + the workflow itself
├── references/     deep docs, loaded on demand
├── assets/         copyable skeletons, templates, data
├── scripts/        runnable tooling (Python / Node / Java / shell)
└── templates/, config/   optional
```

- `SKILL.md` is the always-loaded index; heavy detail belongs in `references/` behind an explicit "read this when" table (see `dev-web-stress-test`, `html-b2b-portal`, `html-prototype-base`).
- The frontmatter `description` is the trigger surface. Chinese trigger phrases in it decide when the skill fires, so treat edits there as behaviour changes.
- In generator skills, `assets/` files are copied **into the user's project**, not used in place: `dev-uniapp-to-miniprogram/assets/{validate.py,selftest.js}` become the generated project's `tools/`; `html-app-packaging/assets/*.template.mjs` become its build scripts.
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

Digital sandbox (config → single-file HTML, then headless gate):

```bash
python visual-digital-sandbox/scripts/build_sandbox.py --list
python visual-digital-sandbox/scripts/build_sandbox.py --scene park --out sandbox-park.html   # --config my.json --strict
python visual-digital-sandbox/scripts/verify_sandbox.py sandbox-park.html --shot preview.png --strict-shot
```

HTML prototype gate:

```bash
python html-b2b-portal/scripts/check_prototype.py 原型.html [更多.html...]
```

Book learning site:

```bash
python tool-book-learning/scripts/audit_notes.py --book <dir> --profile tech
python tool-book-learning/scripts/build_site.py --book <dir> --profile tech
python tool-book-learning/scripts/verify_site.py <built-site args>
```

JVM evidence gathering (runs on the target host, not locally):

```bash
./dev-prod-triage/scripts/jvm/jvm_diag.sh <pid> [--dump] [--out <dir>]
python dev-prod-triage/scripts/jvm/scan_bytecode.py <jar-root> --sizes 32 --types short,int
javac -encoding UTF-8 dev-prod-triage/scripts/jvm/HprofHistogram.java && java -Xmx1g HprofHistogram heap.hprof out.csv
```

Interpreter note: Playwright, PDF, and OCR scripts must run under the Python that actually has Playwright + PyMuPDF/RapidOCR installed (the docs call it "anaconda"). Plain `python` may be a different, minimal interpreter; standard-library-only scripts (`audit_notes`, `build_site`, `check_package`, `validate`) are safe anywhere.

## Conventions

- **Byte preservation**: `.gitattributes` sets `* -text`. Do not let git or editors normalise line endings, and keep binary assets (images, GLB, fonts) intact.
- **Output location**: skills write deliverables into a user-specified project directory, never into the skill directory. Deliverables are generally a single self-contained HTML file plus an exported PNG.
- **CDN stance differs by family, deliberately**: `visual-*` skills are zero-CDN and fully inlined so they open offline; `html-prototype-base` and its quadrants intentionally use Tailwind/Chart.js CDNs with no build step; `html-b2b-portal` may use CDNs but must degrade gracefully.
- **Version discipline**: `0.1.0` for a first release. The version appears in `SKILL.md`, `config.json` where present, the zip filename, and delivery docs — bump them together, then grep the whole skill for the old value.
- **`tool-wechat-jobs-monitor` is personal-use only** per its `NOTICE.md`. Never package, publish, or redistribute it.
- Verification is expected to be mechanical: the repo's habit is a runnable checker per skill, plus a regression test that proves the checker still fails on known-bad input.

## Consistency hazards

- `dev-prod-triage` was formed by merging `dev-jvm-triage@1.0.0` into `prod-triage`, then renamed twice (`prod-triage-idev` → `dev-prod-triage`). Do not reintroduce a second copy of `scripts/jvm/` or a second JVM playbook.
- `dev-feature-scaffold` was absorbed into `html-b2b-portal` (path B). The L1-L10 / P1-P5 / D1-D2 / M1-M3 / R1-R3 layout library lives in `html-b2b-portal/references/feature-scaffold.md` and is mirrored in `config.json` → `layoutLibrary`; do not recreate the old skill or fork the layout tables.
- `visual-arch-diagram/scripts/export_png.py` and `visual-diagram-suite/scripts/export_png.py` share a CLI but are **not** identical files.
- The `html-*` skills document an external prototype workspace (`01-design/`, `02-manage/`, `03-client/`, `04-mobile/`) that does not exist in this repo; do not go looking for those directories here.
- `html-prototype-base` absorbed `html-architecture-design`, `html-manage-pages`, `html-client-pages`, and `html-mobile-pages`. Their quadrant playbooks now live in its `references/` (`01-design-architecture.md`, `02-manage-pages.md`, `03-client-pages.md`, `04-mobile-pages.md`) and the shell templates / page patterns in `references/layouts.md` and `references/page-patterns.md`. Do not recreate the four old skill directories, and do not duplicate their content back into `SKILL.md`.
- `visual-threejs-scene` absorbed `visual-real-twin` (Blender MCP modeling + `export_webgl.py` + `validate_glb.py` + `integrate_glb.py`, plus `references/blender-mcp.md` / `references/webgl-budget.md` / `templates/models-entry.jsonc`). Do not recreate the `visual-real-twin` directory.
- Skills refer to each other by name (`arch-diagram` ↔ `diagram-suite`, `digital-twin` ↔ `threejs-scene`). Renaming or deleting a skill requires a repo-wide grep for its name, including other SKILL.md files' routing tables.
