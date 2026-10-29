/* 工作台数据层 WorkbenchDB（ES5 + localStorage）
 * 用法：本文件全文并入 index.html 的 <script>（单文件交付，不外链），
 *      先 WorkbenchDB.init(schema) 再读写；schema 见 schema-template.json。
 * 接口契约与升级 full_stack 的替换方式见 references/library-commands.md「SDK 契约」。
 * 约束：全程 ES5——var/function、'+' 拼字符串；禁止箭头函数、let/const、模板串、
 *      async/await、fetch、class、includes（用 indexOf 替代）。
 */
var WorkbenchDB = (function () {
  var PREFIX = 'workbench:';
  var schemas = {}; // table -> schema

  function nowIso() { return new Date().toISOString(); }
  function genId() { return 'r-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10); }
  function storeKey(table) { return PREFIX + table; }
  function copy(v) { return JSON.parse(JSON.stringify(v)); }

  function readAll(table) {
    try {
      var raw = window.localStorage.getItem(storeKey(table));
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function writeAll(table, rows) {
    window.localStorage.setItem(storeKey(table), JSON.stringify(rows));
  }

  /* 类型矫正：空值回落 default，否则按 field.type 归一 */
  function coerce(field, value) {
    if (value === undefined || value === null || value === '') {
      return field.default !== undefined ? copy(field.default) : null;
    }
    if (field.type === 'number') { var n = Number(value); return isNaN(n) ? 0 : n; }
    if (field.type === 'boolean') { return value === true || value === 'true' || value === 1; }
    return String(value);
  }

  function autoValue(name) {
    if (name === 'id') { return genId(); }
    if (name === 'created_at') { return nowIso(); }
    return undefined;
  }

  /* 按 schema 整理一行：insert 时补 auto 字段，全部字段类型矫正并截断 maxLength */
  function normalize(schema, row, isInsert) {
    var out = {}, i, f, v;
    row = row || {};
    for (i = 0; i < schema.fields.length; i++) {
      f = schema.fields[i];
      if (row[f.name] !== undefined && row[f.name] !== null) {
        v = row[f.name];
      } else if (isInsert && f.auto) {
        v = autoValue(f.name);
      } else {
        v = undefined;
      }
      v = coerce(f, v);
      if (v !== null && f.maxLength && typeof v === 'string' && v.length > f.maxLength) {
        v = v.slice(0, f.maxLength);
      }
      out[f.name] = v;
    }
    return out;
  }

  function validate(schema, row) {
    var errors = [], i, f;
    for (i = 0; i < schema.fields.length; i++) {
      f = schema.fields[i];
      if (f.auto) { continue; } // 自动字段不校验
      if (f.required && (row[f.name] === null || row[f.name] === undefined || row[f.name] === '')) {
        errors.push((f.label || f.name) + ' 不能为空');
      }
      if (row[f.name] !== null && f.type === 'enum' && f.options && f.options.indexOf(row[f.name]) === -1) {
        errors.push((f.label || f.name) + ' 取值无效');
      }
    }
    return errors;
  }

  /* 注册表结构；表为空且 schema.seed 非空时自动灌种子 */
  function init(schema) {
    schemas[schema.table] = schema;
    if (schema.seed && schema.seed.length && readAll(schema.table).length === 0) {
      var rows = [], i;
      for (i = 0; i < schema.seed.length; i++) { rows.push(normalize(schema, schema.seed[i], true)); }
      writeAll(schema.table, rows);
    }
    return schema;
  }

  /* 全量读取（created_at 降序，新的在前）；传 filterFn(row) 做过滤 */
  function list(table, filterFn) {
    var rows = readAll(table);
    rows.sort(function (a, b) {
      var ca = a.created_at || '', cb = b.created_at || '';
      return ca < cb ? 1 : (ca > cb ? -1 : 0);
    });
    if (typeof filterFn === 'function') {
      return rows.filter(function (r) { return filterFn(r); });
    }
    return rows;
  }

  /* 插入一行；返回 {ok, errors, row} */
  function insert(table, row) {
    var schema = schemas[table];
    if (!schema) { return { ok: false, errors: ['表未 init: ' + table], row: null }; }
    var rec = normalize(schema, row, true);
    var errs = validate(schema, rec);
    if (errs.length) { return { ok: false, errors: errs, row: null }; }
    var rows = readAll(table);
    rows.push(rec);
    writeAll(table, rows);
    return { ok: true, errors: [], row: rec };
  }

  function mixin(base, patch) {
    var out = copy(base), k;
    for (k in patch) {
      if (Object.prototype.hasOwnProperty.call(patch, k)) { out[k] = patch[k]; }
    }
    return out;
  }

  /* 按 id 局部更新；返回 {ok, errors, row} */
  function update(table, id, patch) {
    var schema = schemas[table];
    if (!schema) { return { ok: false, errors: ['表未 init: ' + table], row: null }; }
    var rows = readAll(table), i, found = -1;
    for (i = 0; i < rows.length; i++) { if (rows[i].id === id) { found = i; break; } }
    if (found === -1) { return { ok: false, errors: ['记录不存在'], row: null }; }
    var merged = normalize(schema, mixin(rows[found], patch || {}), false);
    var errs = validate(schema, merged);
    if (errs.length) { return { ok: false, errors: errs, row: null }; }
    rows[found] = merged;
    writeAll(table, rows);
    return { ok: true, errors: [], row: merged };
  }

  /* 删除一行；返回删除条数 */
  function remove(table, id) {
    var rows = readAll(table);
    var next = rows.filter(function (r) { return r.id !== id; });
    writeAll(table, next);
    return rows.length - next.length;
  }

  /* 覆盖式重灌种子；返回灌入条数（调用前必须经用户确认） */
  function seed(table) {
    var schema = schemas[table];
    if (!schema || !schema.seed) { return 0; }
    var rows = [], i;
    for (i = 0; i < schema.seed.length; i++) { rows.push(normalize(schema, schema.seed[i], true)); }
    writeAll(table, rows);
    return rows.length;
  }

  /* 清空整表（破坏性，必须走确认弹层） */
  function clear(table) { writeAll(table, []); }

  return {
    init: init,
    list: list,
    insert: insert,
    update: update,
    remove: remove,
    seed: seed,
    clear: clear
  };
})();
