/* ============================================================
 * 语雀知识库批量导出（浏览器控制台脚本）
 *
 * 用法：登录 https://www.yuque.com/ 后，在【任意已登录页面】按 F12
 *       打开控制台，整段粘贴运行。每完成一个知识库自动触发一次
 *       Blob 下载：yuque_<slug>.json（结构 {book, toc, docs, exportedAt}）
 *
 * 关键前提（为什么必须这么干）：
 *  - 会话 cookie 是 httpOnly，外部脚本(axios/curl)拿不到身份，
 *    所有 API 必须在已登录页面内用 fetch 发起（自动带 cookie）。
 *  - csrf 用 cookie 里的 yuque_ctoken（非 httpOnly，JS 可读）。
 *
 * 进度监控：window.__YQ（docsDone/docsTotal/booksTotal/errors）
 * 手动停止：控制台执行 __YQ.stop()
 * 只导部分库：改下面 ONLY_BOOKS
 * ============================================================ */
(() => {
  "use strict";

  // ---- 可调参数 ----
  const DELAY = 400;        // 每篇文档导出间隔(ms)，防限流
  const ONLY_BOOKS = [];    // 例：['co92v6']，填知识库 slugPath（URL 里那段）；空 = 全部

  const csrf = (document.cookie.match(/(?:^|;\s*)yuque_ctoken=([^;]+)/) || [])[1] || "";
  if (!csrf) console.warn("[YQ] 没找到 yuque_ctoken cookie，导出接口可能报 csrf 校验失败");

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const state = (window.__YQ = {
    running: true, phase: "list",
    booksTotal: 0, bookIndex: 0, docsDone: 0, docsTotal: 0,
    drafts: 0, errors: [], fatal: null,
    stop() { this.running = false; console.log("[YQ] 将在当前文档导完后停止"); },
  });
  const log = (...a) => console.log("[YQ]", ...a);

  // 统一 API 封装：同源 + 带身份 + csrf
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      credentials: "include",
      headers: { "content-type": "application/json", "x-csrf-token": csrf, ...(opts.headers || {}) },
      ...opts,
    });
    let body = null;
    try { body = await res.clone().json(); } catch {}
    return { ok: res.ok, status: res.status, body };
  }

  // 从导出接口响应里抠出官方转换结果的 URL（响应字段名没文档，多重兜底）
  function extractUrl(body) {
    if (!body) return null;
    const d = body.data != null ? body.data : {};
    const cand = d.attachment || d.url || d.exportUrl || body.attachment || body.url;
    if (typeof cand === "string" && /^https?:\/\//.test(cand)) return cand;
    const m = JSON.stringify(body).match(/https?:\\?\/\\?\/[^"]+/);
    return m ? m[0].replace(/\\\//g, "/") : null;
  }

  // 下载官方转换结果：URL 返回可能是纯 markdown 文本或 JSON 包装
  async function fetchExportResult(url) {
    let text = null, lastErr = null;
    for (const withCred of [true, false]) {          // 跨域 CDN 带凭证可能被拒，双重尝试
      try {
        const res = await fetch(url, { credentials: withCred ? "include" : "omit" });
        if (!res.ok) throw new Error("HTTP " + res.status);
        text = await res.text();
        break;
      } catch (e) { lastErr = e; }
    }
    if (text == null) throw lastErr || new Error("导出结果下载失败");
    if (/^\s*(<!DOCTYPE|<html)/i.test(text)) throw new Error("导出结果返回了 HTML 页(会话可能过期)，请重新登录后重跑");
    try {
      const j = JSON.parse(text);
      const inner = (j && (j.data != null ? j.data : j));
      const content = inner && (inner.content != null ? inner.content : inner.md != null ? inner.md : null);
      if (typeof content === "string") text = content;
    } catch {}
    return text;
  }

  // 1) 知识库列表（端点随版本可能变化，两个兜底；再不行用 ONLY_BOOKS + 手动确认）
  async function listBooks() {
    for (const ep of ["/api/mine/books?limit=100", "/api/mine/books_with_summary?limit=100"]) {
      try {
        const { ok, body } = await api(ep);
        const d = body && body.data != null ? body.data : body;
        const arr = Array.isArray(d) ? d : (d && Array.isArray(d.books) ? d.books : null);
        if (ok && arr && arr.length) {
          if (arr.length >= 100) log("⚠️ 库数达到 100 上限，若有更多请用 ONLY_BOOKS 手动补充");
          return arr;
        }
        log("listBooks 端点无数据:", ep, ok, body && body.message);
      } catch (e) { log("listBooks 失败:", ep, e.message); }
    }
    throw new Error("获取知识库列表失败。请在 ONLY_BOOKS 里手工填 slugPath（知识库 URL /<user>/<slug> 的 slug 段），并确认已登录");
  }

  // 2) 单库导出：目录 → 逐篇 POST export → 下载 markdown
  async function exportBook(book) {
    const { ok, body } = await api(`/api/books/${book.id}/toc`);
    const d = body && body.data != null ? body.data : body;
    const toc = (d && (Array.isArray(d) ? d : d.toc)) || [];
    if (!ok || !toc.length) throw new Error(`目录获取失败 ${book.slug}: HTTP ${ok ? "空toc" : ""} ${(body && body.message) || ""}`);

    const docNodes = toc.filter((n) => n.type === "DOC" && n.doc_id);
    state.docsTotal += docNodes.length;
    const docs = [];

    for (const node of docNodes) {
      if (!state.running) { log("已手动停止，本库 JSON 含已导出部分，其余缺失"); break; }
      const rec = {
        title: node.title, slug: node.url, doc_id: node.doc_id,
        level: node.level, parent_uuid: node.parent_uuid, sibling_index: node.sibling_index,
        md: null, board: false, error: null,
      };
      try {
        const r = await api(`/api/docs/${node.doc_id}/export`, {
          method: "POST", body: JSON.stringify({ type: "markdown" }),
        });
        if (!r.ok) {
          const msg = (r.body && (r.body.message || (r.body.data && r.body.data.message))) || "";
          throw Object.assign(new Error(`HTTP ${r.status} ${msg}`), { status: r.status, msg });
        }
        const url = extractUrl(r.body);
        if (url) rec.md = await fetchExportResult(url);
        else {
          const direct = r.body && r.body.data && r.body.data.content;
          if (typeof direct !== "string") throw new Error("导出响应里没找到内容 URL");
          rec.md = direct;
        }
      } catch (e1) {
        const msg = String(e1.message || e1);
        if (/请发布后再导出|status.*400/.test(msg) || e1.status === 400) {
          rec.error = "draft";                        // 未发布草稿导不了，且内容 API 也为空 → 用户空文档，占位即可
          state.drafts++;
        } else {
          try {                                       // 非草稿失败 → 可能是画板，试 lakeboard
            const r2 = await api(`/api/docs/${node.doc_id}/export`, {
              method: "POST", body: JSON.stringify({ type: "lakeboard" }),
            });
            if (!r2.ok) throw new Error("lakeboard HTTP " + r2.status);
            const url2 = extractUrl(r2.body);
            const t2 = url2 ? await fetchExportResult(url2) : String(JSON.stringify(r2.body && r2.body.data));
            JSON.parse(t2);                            // 画板产物必须是合法 JSON
            rec.md = t2; rec.board = true;
          } catch (e2) {
            rec.error = msg;
            state.errors.push({ book: book.slug, doc_id: node.doc_id, title: node.title, error: msg });
            log(`❌ ${node.title}: ${msg}`);
          }
        }
      }
      docs.push(rec);
      state.docsDone++;
      await sleep(DELAY);
    }

    return {
      book: { id: book.id, slug: book.slug, name: book.name, slugPath: book.slugPath || book.slug },
      toc, docs, exportedAt: new Date().toISOString(),
    };
  }

  function saveJSON(obj, filename) {
    const blob = new Blob([JSON.stringify(obj)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  }

  // ---- 主流程 ----
  (async () => {
    try {
      const books = (await listBooks()).filter(
        (b) => !ONLY_BOOKS.length || ONLY_BOOKS.includes(b.slugPath || b.slug)
      );
      if (!books.length) throw new Error("没有匹配的知识库（检查 ONLY_BOOKS 是否填了 slugPath）");
      state.booksTotal = books.length;
      log(`共 ${books.length} 个知识库：${books.map((b) => b.name || b.slug).join("、")}`);

      for (const book of books) {
        state.bookIndex++;
        state.phase = `export:${book.slug}`;
        const data = await exportBook(book);
        saveJSON(data, `yuque_${data.book.slug}.json`);
        log(`✅ [${state.bookIndex}/${books.length}] ${data.book.name} docs=${data.docs.length}`);
        await sleep(1000); // 给浏览器喘息，避免连续下载被拦
      }
      state.phase = "done";
      log(`🎉 全部完成 docs=${state.docsDone} 草稿=${state.drafts} 失败=${state.errors.length}`);
      if (state.errors.length) console.table(state.errors);
    } catch (e) {
      state.phase = "error";
      state.fatal = String((e && e.message) || e);
      log("💥", state.fatal);
    }
    state.running = false;
  })();

  log(`已启动。进度 window.__YQ（当前 phase=${state.phase}）。首次会询问"允许下载多个文件"，点允许。`);
})();
