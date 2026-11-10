#!/usr/bin/env node
// browser-use/IAB 驱动浏览器时，Blob 下载落盘为 C:\Users\qq940\Downloads\<uuid>.tmp，
// 无文件名对应关系。本脚本扫描 Downloads，按 JSON 内容(book.slug)识别语雀导出文件，
// 复制到 _raw 目录并命名为 yuque_<slug>.json。
// 用法: node collect_downloads.mjs [downloadsDir] <rawDir> [--force]
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2).filter(a => a !== "--force");
const force = process.argv.includes("--force");
const rawDir = path.resolve(args.pop() || ".");
const dlDir = path.resolve(args[0] || path.join(process.env.USERPROFILE || "", "Downloads"));

if (!fs.existsSync(rawDir)) { console.error("rawDir 不存在: " + rawDir); process.exit(1); }
if (!fs.existsSync(dlDir)) { console.error("Downloads 不存在: " + dlDir); process.exit(1); }

const tmps = fs.readdirSync(dlDir).filter(f => f.endsWith(".tmp"));
let copied = 0, skippedOthers = 0, dup = 0, badParse = 0;

for (const f of tmps) {
  const full = path.join(dlDir, f);
  let text;
  try { text = fs.readFileSync(full, "utf8"); } catch { continue; }
  let obj;
  try { obj = JSON.parse(text); } catch { badParse++; continue; } // 半截下载或其他程序的 .tmp
  // 严格校验：必须是语雀导出 JSON 的形状
  const slug = obj && obj.book && obj.book.slug;
  if (!slug || !Array.isArray(obj.docs) || !Array.isArray(obj.toc)) { skippedOthers++; continue; }

  const dest = path.join(rawDir, `yuque_${slug}.json`);
  if (fs.existsSync(dest) && !force) {
    console.log(`跳过(已存在): ${dest}（--force 覆盖）`);
    dup++;
    continue;
  }
  fs.copyFileSync(full, dest);
  console.log(`✅ ${f} → ${path.basename(dest)}  book="${obj.book.name}" docs=${obj.docs.length} exportedAt=${obj.exportedAt || "?"}`);
  copied++;
}

console.log(`DONE 新收集=${copied} 已存在跳过=${dup} 非语雀文件=${skippedOthers} 解析失败=${badParse}`);
