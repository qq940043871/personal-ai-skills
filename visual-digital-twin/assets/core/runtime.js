/* ============================================================
   DT Runtime — 大屏运行时（面板装配 / 引擎加载 / 数据脉冲 / 交互）
   加载优先级：CDN Three.js(UMD，兼容 file://) → 失败自动降级 Canvas 2D 等距渲染
   ============================================================ */
(function (w, d) {
  'use strict';

  var CFG = w.__DT_CONFIG__ || {};
  var THREE_SOURCES = (CFG.threeSources && CFG.threeSources.length ? CFG.threeSources : [
    'https://cdn.jsdelivr.net/npm/three@0.149.0/build/three.min.js',
    'https://unpkg.com/three@0.149.0/build/three.min.js',
    'https://lf26-cdn-tos.bytecdntp.com/cdn/expire-1-M/three.js/r128/three.min.js'
  ]);

  /* ---------------- 微型事件总线 ---------------- */
  var handlers = {};
  var Bus = {
    on: function (k, fn) { (handlers[k] = handlers[k] || []).push(fn); return Bus; },
    emit: function (k, p) { (handlers[k] || []).forEach(function (f) { try { f(p); } catch (e) { console.warn(e); } }); }
  };
  w.DTBus = Bus;

  var $ = function (s, r) { return (r || d).querySelector(s); };
  var el = function (tag, cls, html) {
    var n = d.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };

  /* ================= 面板组件 ================= */
  var Comp = {
    kpi: function (box, def) {
      var wrap = el('div', 'dt-kpis');
      (def.items || []).forEach(function (it) {
        var up = (it.trend || 0) >= 0;
        wrap.appendChild(el('div', 'dt-kpi',
          '<div class="dt-kpi-label">' + it.label + '</div>' +
          '<div><span class="dt-kpi-val" data-v>' + it.value + '</span>' +
          '<span class="dt-kpi-unit">' + (it.unit || '') + '</span>' +
          (it.trend != null ? '<span class="dt-kpi-trend ' + (up ? 'up' : 'down') + '">' +
            (up ? '▲' : '▼') + Math.abs(it.trend) + '%</span>' : '') + '</div>'));
      });
      box.appendChild(wrap);
      return {
        tick: function (items) {
          if (!items) return;
          items.forEach(function (it, i) {
            var node = wrap.querySelectorAll('.dt-kpi-val')[i];
            if (node) node.textContent = it.value;
          });
        }
      };
    },

    lineChart: function (box, def) {
      box.appendChild(el('div', 'dt-canvas-wrap', '<canvas style="width:100%;height:100%"></canvas>'));
      var m = w.DTCharts.mount(box.firstChild, 'line', { series: def.series, labels: def.labels }, def.opt);
      return {
        tick: function (items) {
          if (!items) return;
          items.forEach(function (s, i) {
            if (!def.series[i]) return;
            def.series[i].data = s.data ? s.data.slice() : (def.series[i].data.slice(1).concat(s.value));
          });
          if (m) m.update({ series: def.series, labels: def.labels });
        }
      };
    },

    bars: function (box, def) {
      box.appendChild(el('div', 'dt-canvas-wrap', '<canvas style="width:100%;height:100%"></canvas>'));
      var m = w.DTCharts.mount(box.firstChild, 'bars', { items: def.items }, def.opt);
      return { tick: function (items) { if (items && m) m.update({ items: items, opt: def.opt }); } };
    },

    ringGroup: function (box, def) {
      var grid = el('div', 'dt-flex-row');
      grid.style.gap = '10px'; grid.style.flexWrap = 'wrap'; grid.style.justifyContent = 'space-around';
      (def.items || []).forEach(function (it) {
        var cell = el('div');
        cell.style.cssText = 'flex:1 1 40%;min-width:82px;text-align:center;position:relative;height:96px';
        cell.innerHTML = '<canvas style="width:100%;height:84px"></canvas>' +
          '<div style="font-size:11px;color:var(--t2);margin-top:-6px">' + it.label + '</div>';
        grid.appendChild(cell);
        w.DTCharts.mount(cell.querySelector('canvas'), 'ring', { value: it.value, max: it.max, opt: it });
      });
      box.appendChild(grid);
      return null;
    },

    donut: function (box, def) {
      box.appendChild(el('div', 'dt-canvas-wrap', '<canvas style="width:100%;height:100%"></canvas>'));
      w.DTCharts.mount(box.firstChild, 'donut', { items: def.items }, def.opt);
      return null;
    },

    rank: function (box, def) {
      var list = el('div', 'dt-list');
      function render(items) {
        list.innerHTML = '';
        items.forEach(function (it, i) {
          var max = it.max || Math.max.apply(null, items.map(function (x) { return x.value; })) || 1;
          var li = el('div', 'dt-li');
          li.innerHTML = '<span class="dt-li-no">' + (i + 1) + '</span>' +
            '<span class="dt-li-name">' + it.name + '</span>' +
            '<span class="dt-li-val">' + it.value + (it.unit || '') + '</span>';
          if (it.dataId) li.setAttribute('data-focus', it.dataId);
          list.appendChild(li);
          if (i === 0 || def.bar !== false) {
            var barWrap = el('div');
            barWrap.style.cssText = 'margin:2px 0 2px 26px';
            barWrap.innerHTML = '<div class="dt-bar"><i style="width:' + (it.value / max * 100).toFixed(1) + '%"></i></div>';
            list.appendChild(barWrap);
          }
        });
      }
      render(def.items || []);
      box.appendChild(list);
      return { tick: render };
    },

    alarms: function (box) {
      var list = el('div', 'dt-list');
      box.appendChild(list);
      return {
        tick: function (items) {
          if (!items) return;
          list.innerHTML = '';
          items.slice(0, 30).forEach(function (a) {
            list.appendChild(el('div', 'dt-alarm ' + (a.level || 'err'),
              '<span><b>' + a.name + '</b> ' + a.text + '</span><time>' + a.time + '</time>'));
          });
        }
      };
    },

    switches: function (box, def) {
      (def.items || []).forEach(function (it) {
        var label = el('label', 'dt-sw',
          '<input type="checkbox" ' + (it.on !== false ? 'checked' : '') + '>' +
          '<span class="dt-sw-track"></span><span>' + it.label + '</span>');
        var input = label.querySelector('input');
        input.addEventListener('change', function () { Bus.emit('layer', { id: it.id, on: input.checked }); });
        box.appendChild(label);
      });
      return null;
    },

    entities: function (box, def) {
      var list = el('div', 'dt-list');
      (def.items || []).forEach(function (it) {
        var color = { normal: 'var(--ok)', warn: 'var(--warn)', alarm: 'var(--err)', run: 'var(--run)' }[it.status] || 'var(--ok)';
        var li = el('div', 'dt-li');
        li.innerHTML = '<i style="width:7px;height:7px;border-radius:50%;background:' + color +
          ';box-shadow:0 0 8px ' + color + ';flex:0 0 7px"></i>' +
          '<span class="dt-li-name">' + it.name + '</span>' +
          '<span class="dt-li-val">' + (it.value != null ? it.value + (it.unit || '') : '') + '</span>';
        li.setAttribute('data-focus', it.id);
        list.appendChild(li);
      });
      box.appendChild(list);
      return null;
    },

    legend: function (box, def) {
      var wrap = el('div', 'dt-legend-box');
      (def.items || []).forEach(function (it) {
        wrap.appendChild(el('span', 'dt-legend-item', '<i style="color:' + it.color + '"></i>' + it.label));
      });
      box.appendChild(wrap);
      return null;
    }
  };

  /* ================= 面板装配 ================= */
  var updaters = [];
  function buildPanels(colId, defs) {
    var col = $('#' + colId);
    if (!col) return;
    (defs || []).forEach(function (p) {
      var panel = el('div', 'dt-panel');
      panel.appendChild(el('div', 'dt-ph', '<h3>' + p.title + '</h3>' + (p.note ? '<small>' + p.note + '</small>' : '')));
      var body = el('div', 'dt-pb');
      panel.appendChild(body);
      var builder = Comp[p.type];
      if (builder) {
        var inst = builder(body, p.data || p);
        if (inst && inst.tick) updaters.push({ key: p.key, fn: inst.tick, data: p.data });
      } else {
        body.appendChild(el('div', 'dt-empty', '未支持的组件类型：' + p.type));
      }
      col.appendChild(panel);
    });
  }

  /* ================= 脉冲数据（Mock） ================= */
  function pulse() {
    updaters.forEach(function (u) {
      var items = (u.data && (u.data.items || u.data.series));
      if (!items) return;
      var next = items.map(function (it) {
        var v, dv;
        if (Array.isArray(it.data)) {
          v = it.data.slice(1);
          dv = Math.max(0, it.data[it.data.length - 1] + (Math.random() - .48) * (it.step || it.max * .04 || 3));
          v.push(Math.round(dv * 10) / 10);
          return { data: v };
        }
        var max = it.max || 100;
        if (it.max == null && it.step == null) return { value: it.value, max: it.max, unit: it.unit, name: it.name };
        dv = it.value + (Math.random() - .5) * (it.step || max * .02);
        dv = Math.max(0, Math.min(max, dv));
        it.value = Math.round(dv * 10) / 10;
        return { value: it.value, max: it.max, unit: it.unit, name: it.name };
      });
      u.fn(next);
    });
  }

  /* ================= 头部与时钟 ================= */
  function clock() {
    var n = new Date(), wk = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][n.getDay()];
    var p = function (x) { return x < 10 ? '0' + x : x; };
    var t = p(n.getHours()) + ':' + p(n.getMinutes()) + ':' + p(n.getSeconds());
    if ($('#dtChipClock')) $('#dtChipClock').textContent = t;
    if ($('#dtChipDate')) $('#dtChipDate').textContent = n.getFullYear() + '-' + p(n.getMonth() + 1) + '-' + p(n.getDate());
    if ($('#dtChipWeek')) $('#dtChipWeek').textContent = wk;
  }

  /* ================= 舞台四角装饰 ================= */
  function corners() {
    var st = $('#dtStage');
    ['tl', 'tr', 'bl', 'br'].forEach(function (p) { st.appendChild(el('div', 'dt-corner ' + p)); });
  }

  /* ================= 提示 & Toast ================= */
  var tipsTimer;
  function toast(msg) {
    var t = $('#dtStageTips');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(tipsTimer);
    tipsTimer = setTimeout(function () { t.classList.remove('show'); }, 2200);
  }

  /* ================= 工具条 ================= */
  function toolbar() {
    d.querySelectorAll('.dt-tbtn').forEach(function (b) {
      b.addEventListener('click', function () {
        var cmd = b.getAttribute('data-cmd');
        if (cmd === 'full') {
          var ay = $('#dtApp');
          if (!d.fullscreenElement) (ay.requestFullscreen || ay.webkitRequestFullscreen).call(ay);
          else d.exitFullscreen();
        } else if (cmd === 'orbit') {
          b.classList.toggle('on');
          Bus.emit('orbit', b.classList.contains('on'));
        } else { Bus.emit('cmd', cmd); }
      });
    });
  }

  /* ================= 实体聚焦联动 ================= */
  function bindFocus() {
    d.addEventListener('click', function (e) {
      var t = e.target.closest('[data-focus]');
      if (t) { Bus.emit('focus', { id: t.getAttribute('data-focus') }); toast('已定位：' + t.querySelector('.dt-li-name').textContent); }
    });
  }

  /* ================= Three.js 加载器 ================= */
  function loadThree(i, done) {
    if (i >= THREE_SOURCES.length) return done(false);
    var s = d.createElement('script');
    var settled = false;
    var timer = setTimeout(function () {
      if (settled) return; settled = true; s.remove();
      loadThree(i + 1, done);
    }, 6000);
    s.src = THREE_SOURCES[i];
    s.onload = function () {
      if (settled) return;
      clearTimeout(timer);
      if (w.THREE) { settled = true; done(true); }
      else { settled = true; s.remove(); loadThree(i + 1, done); }
    };
    s.onerror = function () { if (settled) return; settled = true; clearTimeout(timer); s.remove(); loadThree(i + 1, done); };
    d.head.appendChild(s);
  }

  /* ================= 启动 ================= */
  function boot() {
    $('#dtTitle').textContent = CFG.title || '数字孪生可视化平台';
    $('#dtSubtitle').textContent = CFG.subtitle || '';
    d.title = CFG.title || '数字孪生';
    buildPanels('dtColLeft', CFG.panels && CFG.panels.left);
    buildPanels('dtColRight', CFG.panels && CFG.panels.right);
    corners(); toolbar(); bindFocus(); clock();
    setInterval(clock, 1000);
    if (CFG.pulse !== false) setInterval(pulse, CFG.pulseInterval || 3000);
    Bus.on('alarm', function (a) { toast('⚠ ' + a.text); });

    var scene = w.__DT_SCENE__;
    var stage = $('#dtStage'), canvas = $('#dtCanvas');

    function start(mode) {
      $('#dtLoading').classList.add('hide');
      w.__DT_MODE__ = mode;
      if (mode === '3d') {
        $('#dtChipMode').innerHTML = '<em></em>三维渲染';
        try {
          w.__DT_CTRL__ = scene.init({
            THREE: w.THREE, canvas: canvas, container: stage, cfg: CFG, bus: Bus, toast: toast
          });
        } catch (e) {
          console.error('[DT] scene init failed', e);
          return start('2d');
        }
      } else if (mode === '3d-real') {
        // 写实引擎已自行完成场景构建（window.__DT_CTRL__ 由 engine.js 设置）
        $('#dtChipMode').innerHTML = '<em></em>写实三维';
        if (!w.__DT_CTRL__) { console.error('[DT] engine ready but ctrl missing'); return start('2d'); }
      } else {
        $('#dtChipMode').innerHTML = '<em style="background:var(--warn);box-shadow:0 0 8px var(--warn)"></em>二维降级';
        stage.appendChild(el('div', 'dt-offline-badge', '未加载三维引擎，已进入等距 2D 降级模式（数据面板功能完整）'));
        if (w.DTIso) w.__DT_CTRL__ = w.DTIso.init({ canvas: canvas, container: stage, cfg: CFG, scene: scene, bus: Bus });
      }
      if (CFG.alarms) Bus.emit('alarms', CFG.alarms);
    }

    // 渲染 bottomline：始终让告警滚动条有内容
    var mq = $('#dtAlarmList');
    if (CFG.alarms && CFG.alarms.length) {
      var html = '';
      CFG.alarms.concat(CFG.alarms).forEach(function (a) {
        html += '<span class="dt-marquee-item"><b>' + a.time + ' ' + a.name + '</b> · ' + a.text + '</span>';
      });
      mq.innerHTML = html;
    } else { mq.parentElement.style.display = 'none'; }

    if (CFG.forceMode === '2d' || CFG.offlineOnly) return start('2d');
    // 场景分派：写实（构建期 engineMode 标记）→ 经典（UMD）→ 2D 降级
    if (CFG.engineMode === 'realistic' && d.getElementById('dtEngineSrc')) return startRealistic();
    if (w.__DT_SCENE__) return loadThree(0, function (ok) { start(ok ? '3d' : '2d'); });
    start('2d');

    /* ---- 写实引擎加载链（必须在 boot 作用域内：要用 start/stage/canvas） ----
       探测 CDN（module 构建）→ 注入 importmap → Blob URL 动态 import 内联引擎源码
       → 引擎自报 __DT_ENGINE_READY__ → start('3d-real')；任何失败/超时 → 2D 降级 */
    function startRealistic() {
      var cdns = (CFG.threeModuleSources && CFG.threeModuleSources.length)
        ? CFG.threeModuleSources
        : ['https://cdn.jsdelivr.net/npm/three@0.160.0/', 'https://unpkg.com/three@0.160.0/'];
      var settled = false;
      var guard = setTimeout(function () { finish(new Error('引擎加载超时')); }, 20000);
      function finish(err) {
        if (settled) return;
        settled = true;
        clearTimeout(guard);
        w.__DT_ENGINE_READY__ = null; w.__DT_ENGINE_FAIL__ = null;
        if (err) { console.warn('[DT] 写实引擎不可用，降级 2D：', err); start('2d'); }
        else start('3d-real');
      }
      w.__DT_ENGINE_FAIL__ = function (err) { finish(err || new Error('engine fail')); };
      w.__DT_ENGINE_READY__ = function () { finish(null); };
      (function probe(i) {
        if (i >= cdns.length) return finish(new Error('无可用 CDN'));
        var ctl = ('AbortController' in w) ? new AbortController() : null;
        var t = setTimeout(function () { if (ctl) ctl.abort(); else probe(i + 1); }, 6000);
        fetch(cdns[i] + 'package.json', { mode: 'cors', signal: ctl ? ctl.signal : undefined })
          .then(function (r) {
            clearTimeout(t);
            if (!r.ok) throw new Error('CDN HTTP ' + r.status);
            var im = d.createElement('script');
            im.type = 'importmap';
            im.textContent = JSON.stringify({ imports: {
              'three': cdns[i] + 'build/three.module.js',
              'three/addons/': cdns[i] + 'examples/jsm/'
            }});
            d.head.appendChild(im);
            // importmap 就位后才能触发第一次模块加载（Blob URL 动态 import）
            var srcNode = d.getElementById('dtEngineSrc');
            if (!srcNode) return finish(new Error('缺少引擎源码槽位'));
            w.__DT_ENGINE_CTX__ = { canvas: canvas, container: stage, cfg: CFG, bus: Bus, toast: toast };
            import(URL.createObjectURL(new Blob([srcNode.textContent], { type: 'text/javascript' })))
              .catch(function (e) { finish(e); });
          })
          .catch(function () { clearTimeout(t); probe(i + 1); });
      })(0);
    }
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', boot); else boot();
})(window, document);
