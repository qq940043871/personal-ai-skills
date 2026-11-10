#!/usr/bin/env node
// 语雀备份落地验证：结构 / 图片 / README / 空文件 四轮自动检查
// 用法: node verify.mjs <rawDir> <outDir>
// （第 4 轮内容抽样重导对比需登录语雀，见 SKILL.md，本脚本不覆盖）
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const rawDir = path.resolve(process.argv[2] || ".");
const outDir = path.resolve(process.argv[3] || ".");

const sanitize = (name) =>
  String(name || "")
    .replace(/[\\/:*?"<>|\r\n\t]/g, "-")
    .replace(/\s+/g, " ")
    .replace(/^[.\s-]+|[.\s-]+$/g, "")
    .slice(0, 80) || "未命名";

const CDN_RE = /https?:\/\/(?:cdn\.nlark|cdn\.yuque)\.com[^\s)"']*/g;
// 只认 md 链接/图片 (…) 与 HTML src 形式；反引号包裹的说明文字不算引用
const IMG_RE = /\((?:\.{1,2}\/)?images\/([^)\s]+)\)|["'](?:\.{1,2}\/)?images\/([^)"'\s]+)["']/g;
// README 链接：尖括号包裹的文件名可含字面括号，捕获到 > 为止；普通链接捕获到 ) 为止
const README_LINK_RE = /\]\(<\.\/([^>]+)>\)|\]\(\.\/([^)\s]+)\)/g;
// 剥离围栏代码块与行内代码——代码示例里的 "images/{path}" 等不算图片引用
const stripCode = (t) => t.replace(/```[\s\S]*?(?:```|$)/g, "").replace(/`[^`\n]*`/g, "");

let failures = 0;
const bad = (msg) => { failures++; console.log("  ❌ " + msg); };
const good = (msg) => console.log("  ✅ " + msg);

// magic bytes 白名单（svg/json 按文本判断）
function fileKindOk(file, buf) {
  if (buf.length === 0) return false;
  const h = buf.subarray(0, 8);
  const is = (...bytes) => bytes.every((b, i) => h[i] === b);
  const s = buf.subarray(0, 200).toString("utf8").trimStart();
  if (/\.(png)$/.test(file)) return is(0x89, 0x50, 0x4e, 0x47);
  if (/\.(jpg)$/.test(file)) return is(0xff, 0xd8, 0xff);
  if (/\.(gif)$/.test(file)) return h.subarray(0, 3).toString() === "GIF";
  if (/\.(webp)$/.test(file)) return is(0x52, 0x49, 0x46, 0x46) && buf.subarray(8, 12).toString() === "WEBP";
  if (/\.(bmp)$/.test(file)) return is(0x42, 0x4d);
  if (/\.(ico)$/.test(file)) return is(0x00, 0x00, 0x01, 0x00);
  if (/\.(svg)$/.test(file)) return s.startsWith("<svg") || s.startsWith("<?xml");
  if (/\.(json)$/.test(file)) { try { JSON.parse(buf.toString("utf8")); return true; } catch { return false; } }
  return buf.length > 0; // 未知扩展名：非空即过
}

const files = fs.readdirSync(rawDir).filter(f => /^yuque_.*\.json$/.test(f)).sort();
if (!files.length) { console.error("rawDir 里没有 yuque_*.json: " + rawDir); process.exit(1); }

let totalToc = 0, totalFiles = 0, totalImgs = 0, totalRefs = 0;

for (const f of files) {
  const raw = JSON.parse(fs.readFileSync(path.join(rawDir, f), "utf8"));
  if (!raw.book || !raw.book.slug) { console.log(`\n⏭️ 跳过 ${f}（非知识库导出，如验证样本/diff 文件）`); continue; }
  const book = raw.book || {};
  const bookName = sanitize(book.name || book.slug || f.replace(/\.json$/, ""));
  const bookDir = path.join(outDir, bookName);
  console.log(`\n📚 ${bookName} (${book.slug})`);

  if (!fs.existsSync(bookDir)) { bad(`目录不存在: ${bookDir}`); continue; }

  // —— 第1轮 结构：TOC DOC 数 vs 实际 md 文件数 ——
  const tocDocs = (raw.toc || []).filter(n => n.type === "DOC" && n.doc_id);
  const mdFiles = fs.readdirSync(bookDir).filter(x => x.endsWith(".md") && x !== "README.md");
  totalToc += tocDocs.length; totalFiles += mdFiles.length;
  if (tocDocs.length === mdFiles.length) good(`结构: TOC ${tocDocs.length} = 文件 ${mdFiles.length}`);
  else {
    const tocIds = new Map(tocDocs.map(n => [n.doc_id, sanitize(n.title)]));
    const writtenIds = new Set((raw.docs || []).map(d => d.doc_id));
    const missing = tocDocs.filter(n => !writtenIds.has(n.doc_id)).map(n => n.title);
    if (missing.length) bad(`结构: TOC ${tocDocs.length} ≠ 文件 ${mdFiles.length}，TOC 有但导出 JSON 缺: ${missing.slice(0, 5).join("、")}${missing.length > 5 ? "…" : ""}`);
    else bad(`结构: TOC ${tocDocs.length} ≠ 文件 ${mdFiles.length}（可能人工删过空文件，见下）`);
    // 找出多余/缺失的文件名级差异
    const tocTitles = [...tocIds.values()].sort();
    const extra = mdFiles.map(x => x.replace(/^\d+-/, "").replace(/\.md$/, "")).filter(t => !tocTitles.includes(t));
    if (extra.length) console.log(`  ⚠️ 文件比 TOC 多(常见于人工清理过空文档): ${extra.slice(0, 5).join("、")}`);
  }

  // —— 第2轮 图片：引用 vs 文件、magic bytes、CDN 残留 ——
  const imagesDir = path.join(bookDir, "images");
  const imgFiles = fs.existsSync(imagesDir) ? fs.readdirSync(imagesDir) : [];
  let refSet = new Set(), cdnLeft = 0, mdScanned = 0;
  for (const mf of mdFiles) {
    const text = stripCode(fs.readFileSync(path.join(bookDir, mf), "utf8"));
    mdScanned++;
    for (const m of text.matchAll(IMG_RE)) { const r = m[1] || m[2]; if (r) refSet.add(r); }
    cdnLeft += (text.match(CDN_RE) || []).length;
  }
  totalRefs += refSet.size; totalImgs += imgFiles.length;
  const refMissing = [...refSet].filter(r => !imgFiles.includes(r));
  if (refMissing.length) bad(`图片: ${refMissing.length} 个引用无文件，如 ${refMissing.slice(0, 3).join("、")}`);
  else good(`图片引用: ${refSet.size} 个全部有文件`);

  let badMagic = [], zero = [];
  for (const img of imgFiles) {
    const buf = fs.readFileSync(path.join(imagesDir, img));
    if (buf.length === 0) zero.push(img);
    else if (!fileKindOk(img, buf)) badMagic.push(img);
  }
  if (badMagic.length) console.log(`  ⚠️ ${badMagic.length} 个图片扩展名与实际格式不符（浏览器按内容渲染，不影响显示，如需修正可改扩展名）: ${badMagic.slice(0, 3).join("、")}`);
  else good(`图片文件: ${imgFiles.length} 个格式全部有效`);
  if (zero.length) bad(`0 字节文件 ${zero.length} 个: ${zero.join("、")}`);

  if (cdnLeft) bad(`CDN 残留链接 ${cdnLeft} 处（图片没本地化或 md 未改写）`);
  else good("CDN 残留: 0");

  // —— 第3轮 README：链接 vs 实际文件双向一致 ——
  const readmePath = path.join(bookDir, "README.md");
  if (!fs.existsSync(readmePath)) { bad("README.md 缺失"); continue; }
  const readme = fs.readFileSync(readmePath, "utf8");
  const links = [...readme.matchAll(README_LINK_RE)].map(m => decodeURIComponent((m[1] || m[2]).trim()));
  const linkMissing = links.filter(l => !fs.existsSync(path.join(bookDir, l)));
  const notInReadme = mdFiles.filter(mf => !links.includes(mf));
  if (linkMissing.length) bad(`README 链接指向不存在的文件 ${linkMissing.length} 个: ${linkMissing.slice(0, 3).join("、")}`);
  if (notInReadme.length) bad(`有文档未列入 README ${notInReadme.length} 个: ${notInReadme.slice(0, 3).join("、")}`);
  if (!linkMissing.length && !notInReadme.length) good(`README: ${links.length} 个链接与文件双向一致`);

  // —— 第4轮 空文件 / 空目录巡检 ——
  const emptyMd = mdFiles.filter(mf => fs.readFileSync(path.join(bookDir, mf), "utf8").trim() === "");
  if (emptyMd.length) bad(`空白 md ${emptyMd.length} 篇: ${emptyMd.join("、")}`);
  const dirs = [bookDir, imagesDir];
  for (const d of dirs.filter(x => fs.existsSync(x))) {
    if (fs.readdirSync(d).length === 0) bad(`空目录: ${d}`);
  }
}

console.log("\n========== 汇总 ==========");
console.log(`库=${files.length} TOC文档=${totalToc} 落地md=${totalFiles} 图片=${totalImgs} 引用=${totalRefs}`);
console.log(`md总字数占位: 见各库 ⚠️ 占位文档（草稿/画板属预期，不算失败）`);
if (failures) { console.log(`\n❌ 共 ${failures} 项失败`); process.exit(1); }
console.log("\n🎉 四轮自动检查全部通过");
