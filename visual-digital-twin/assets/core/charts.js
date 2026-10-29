/* ============================================================
   DTCharts — 零依赖迷你图表库（Canvas 2D，支持 HiDPI）
   用途：面板内嵌图表，不引入 ECharts，保证离线可用
   提供：mount/line/bars/ring/donut/gauge
   ============================================================ */
(function (w) {
  'use strict';

  var CSS = {
    cyan: '#22d3ee', blue: '#3b82f6', violet: '#a855f7', teal: '#2dd4bf',
    amber: '#fbbf24', rose: '#fb7185', grid: 'rgba(34,211,238,.10)',
    axis: '#557ba4', label: '#8fb3d9', white: '#e6f4ff'
  };

  function hex2rgba(hex, a) {
    var h = hex.replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  /** 按设备像素比校正画布尺寸；返回 {ctx,w,h}（逻辑像素） */
  function fit(cv) {
    var dpr = Math.min(w.devicePixelRatio || 1, 2);
    var r = cv.getBoundingClientRect();
    var w0 = Math.max(1, Math.floor(r.width)), h0 = Math.max(1, Math.floor(r.height));
    if (cv.width !== w0 * dpr || cv.height !== h0 * dpr) {
      cv.width = w0 * dpr; cv.height = h0 * dpr;
    }
    var ctx = cv.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w0, h0);
    return { ctx: ctx, w: w0, h: h0 };
  }

  function niceStep(max) {
    var raw = max / 4;
    if (raw <= 0) return 1;
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var n = raw / mag;
    return (n >= 5 ? 10 : n >= 2 ? 5 : n >= 1 ? 2 : 1) * mag;
  }

  function gridLines(ctx, W, H, pad, rows, cols, labels) {
    ctx.strokeStyle = CSS.grid; ctx.lineWidth = 1;
    ctx.font = '10px system-ui,sans-serif'; ctx.fillStyle = CSS.axis;
    for (var i = 0; i <= rows; i++) {
      var y = Math.round(pad.t + (H - pad.t - pad.b) * i / rows) + .5;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    }
    for (var j = 0; j <= cols; j++) {
      var x = Math.round(pad.l + (W - pad.l - pad.r) * j / cols) + .5;
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
    }
    if (labels) {
      ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      for (var k = 0; k <= rows; k++) {
        var yy = pad.t + (H - pad.t - pad.b) * k / rows;
        ctx.fillText(labels.max - (labels.max - labels.min) * k / rows, pad.l - 6, yy);
      }
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      if (labels.x) for (var m = 0; m < labels.x.length; m++) {
        ctx.fillText(labels.x[m], pad.l + (W - pad.l - pad.r) * m / (labels.x.length - 1), H - pad.b + 6);
      }
    }
  }

  /** 折线 / 面积图：series=[{name,color,data:[]}] */
  function line(cv, series, opt) {
    opt = opt || {};
    var f = fit(cv), ctx = f.ctx, W = f.w, H = f.h;
    var pad = opt.pad || { l: 30, r: 8, t: 10, b: 16 };
    var all = []; (series || []).forEach(function (s) { all = all.concat(s.data || []); });
    if (!all.length) return;
    var max = opt.max || Math.max.apply(null, all) * 1.15;
    var min = opt.min || 0;
    gridLines(ctx, W, H, pad, 3, Math.max(1, ((series[0] && series[0].data.length) || 6) - 1),
      { max: +max.toFixed(0), min: +min.toFixed(0), x: opt.labels });
    var stepX = (W - pad.l - pad.r) / Math.max(1, series[0].data.length - 1);
    (series || []).forEach(function (s, si) {
      var color = s.color || (si ? CSS.violet : CSS.cyan);
      var pts = s.data.map(function (v, i) {
        return [pad.l + stepX * i, pad.t + (H - pad.t - pad.b) * (1 - (v - min) / (max - min || 1))];
      });
      if (opt.area !== false) {
        var g = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
        g.addColorStop(0, hex2rgba(color, .38)); g.addColorStop(1, hex2rgba(color, 0));
        ctx.beginPath(); ctx.moveTo(pts[0][0], H - pad.b);
        pts.forEach(function (p) { ctx.lineTo(p[0], p[1]); });
        ctx.lineTo(pts[pts.length - 1][0], H - pad.b); ctx.closePath();
        ctx.fillStyle = g; ctx.fill();
      }
      ctx.beginPath(); pts.forEach(function (p, i) { i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); });
      ctx.strokeStyle = color; ctx.lineWidth = 1.8; ctx.lineJoin = 'round';
      ctx.shadowColor = color; ctx.shadowBlur = 8; ctx.stroke(); ctx.shadowBlur = 0;
      // 末端脉冲点
      var last = pts[pts.length - 1];
      ctx.beginPath(); ctx.arc(last[0], last[1], 2.6, 0, 6.2832);
      ctx.fillStyle = '#fff'; ctx.fill();
      ctx.beginPath(); ctx.arc(last[0], last[1], 5.5, 0, 6.2832);
      ctx.fillStyle = hex2rgba(color, .35); ctx.fill();
    });
  }

  /** 柱状图：data=[{name,value,color}]，横向 bars 更省空间 */
  function bars(cv, data, opt) {
    opt = opt || {};
    var f = fit(cv), ctx = f.ctx, W = f.w, H = f.h;
    if (!data || !data.length) return;
    var horizontal = opt.horizontal !== false;
    var gap = opt.gap || .42;
    if (horizontal) {
      var rowH = H / data.length, bw = rowH * (1 - gap);
      var max = opt.max || Math.max.apply(null, data.map(function (d) { return d.value; })) * 1.1;
      var labelW = opt.labelWidth || 44;
      data.forEach(function (d, i) {
        var y = rowH * i + (rowH - bw) / 2;
        var len = (W - labelW - 34) * d.value / (max || 1);
        ctx.fillStyle = CSS.white; ctx.font = '10px system-ui,sans-serif';
        ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
        ctx.fillText(d.name.length > 6 ? d.name.slice(0, 6) : d.name, 0, y + bw / 2);
        ctx.fillStyle = 'rgba(34,211,238,.10)';
        ctx.fillRect(labelW, y, W - labelW - 34, bw);
        var g = ctx.createLinearGradient(labelW, 0, labelW + len, 0);
        g.addColorStop(0, d.color || CSS.blue); g.addColorStop(1, CSS.cyan);
        ctx.fillStyle = g; ctx.shadowColor = CSS.cyan; ctx.shadowBlur = 6;
        ctx.fillRect(labelW, y, Math.max(2, len), bw); ctx.shadowBlur = 0;
        ctx.fillStyle = CSS.cyan; ctx.textAlign = 'right';
        ctx.fillText(d.value + (opt.unit || ''), W, y + bw / 2);
      });
    } else {
      var pad = { l: 26, r: 6, t: 8, b: 18 };
      var max2 = opt.max || Math.max.apply(null, data.map(function (d) { return d.value; })) * 1.15;
      gridLines(ctx, W, H, pad, 3, data.length - 1, { max: +max2.toFixed(0), min: 0 });
      var bw2 = (W - pad.l - pad.r) / data.length * (1 - gap);
      data.forEach(function (d, i) {
        var hgt = (H - pad.t - pad.b) * d.value / (max2 || 1);
        var x = pad.l + (W - pad.l - pad.r) * i / data.length + ((W - pad.l - pad.r) / data.length - bw2) / 2;
        var g = ctx.createLinearGradient(0, H - pad.b - hgt, 0, H - pad.b);
        g.addColorStop(0, d.color || CSS.cyan); g.addColorStop(1, hex2rgba(d.color || CSS.cyan, .12));
        ctx.fillStyle = g; ctx.fillRect(x, H - pad.b - hgt, bw2, hgt);
        ctx.fillStyle = CSS.label; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
        ctx.font = '10px system-ui,sans-serif';
        ctx.fillText(d.name, x + bw2 / 2, H - pad.b + 5);
      });
    }
  }

  /** 环形进度：value/max */
  function ring(cv, value, max, opt) {
    opt = opt || {};
    var f = fit(cv), ctx = f.ctx, W = f.w, H = f.h;
    var cx = W / 2, cy = H / 2, r = Math.max(6, Math.min(W, H) / 2 - 6);
    var p = Math.max(0, Math.min(1, value / (max || 100)));
    var color = opt.color || CSS.cyan;
    ctx.lineWidth = opt.thickness || 7; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, 6.2832);
    ctx.strokeStyle = 'rgba(34,211,238,.12)'; ctx.stroke();
    // 刻度
    if (opt.ticks !== false) {
      for (var t = 0; t < 40; t++) {
        var a = -Math.PI / 2 + t / 40 * 6.2832;
        var inner = r + 4, outer = r + (t % 5 === 0 ? 9 : 6);
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(a) * inner, cy + Math.sin(a) * inner);
        ctx.lineTo(cx + Math.cos(a) * outer, cy + Math.sin(a) * outer);
        ctx.strokeStyle = t / 40 < p ? hex2rgba(color, .75) : 'rgba(34,211,238,.16)';
        ctx.lineWidth = 1; ctx.stroke();
      }
    }
    var start = -Math.PI / 2, end = start + p * 6.2832;
    var g = ctx.createLinearGradient(cx - r, cy - r, cx + r, cy + r);
    g.addColorStop(0, hex2rgba(color, .55)); g.addColorStop(1, color);
    ctx.lineWidth = opt.thickness || 7; ctx.strokeStyle = g;
    ctx.shadowColor = color; ctx.shadowBlur = 12;
    ctx.beginPath(); ctx.arc(cx, cy, r, start, end); ctx.stroke(); ctx.shadowBlur = 0;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#fff'; ctx.font = '700 ' + Math.round(r * .62) + 'px "DIN Alternate",Impact,system-ui';
    ctx.fillText((opt.text != null ? opt.text : Math.round(p * 100)) + (opt.suffix || '%'), cx, cy - 2);
    ctx.fillStyle = CSS.label; ctx.font = '10px system-ui,sans-serif';
    ctx.fillText(opt.label || '', cx, cy + r * .45);
  }

  /** 多环占比：data=[{name,value,color}] */
  function donut(cv, data, opt) {
    opt = opt || {};
    var f = fit(cv), ctx = f.ctx, W = f.w, H = f.h;
    var cx = W / 2, cy = H / 2, r = Math.max(6, Math.min(W, H) / 2 - 4);
    var total = data.reduce(function (a, b) { return a + b.value; }, 0) || 1;
    var a0 = -Math.PI / 2;
    data.forEach(function (d) {
      var a1 = a0 + d.value / total * 6.2832;
      ctx.beginPath(); ctx.arc(cx, cy, r, a0, a1);
      ctx.strokeStyle = d.color; ctx.lineWidth = opt.thickness || 12;
      ctx.shadowColor = d.color; ctx.shadowBlur = 8; ctx.stroke();
      a0 = a1 + .04;
    });
    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(34,211,238,.10)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx, cy, r - (opt.thickness || 12) / 2 - 3, 0, 6.2832); ctx.stroke();
  }

  /** 挂载并自动重绘 / 更新数据；返回 update(newData) */
  function mount(el, type, data, opt) {
    if (!el) return null;
    var cv = el.tagName === 'CANVAS' ? el : el.querySelector('canvas');
    if (!cv) return null;
    var draw = function () {
      try {
        if (type === 'line') line(cv, data.series || data, data.opt || opt);
        else if (type === 'bars') bars(cv, data.items || data, data.opt || opt || data.opt);
        else if (type === 'ring') ring(cv, data.value, data.max, data.opt || opt);
        else if (type === 'donut') donut(cv, data.items || data, data.opt || opt);
      } catch (e) { console.warn('[DTCharts]', e); }
    };
    // 首帧延后到布局稳定后绘制，避免容器高度为 0 时算出负半径
    requestAnimationFrame(draw);
    if (w.ResizeObserver) { new w.ResizeObserver(draw).observe(cv); }
    else { w.addEventListener('resize', draw); }
    return { update: function (d) { data = d; draw(); }, redraw: draw };
  }

  w.DTCharts = { line: line, bars: barAdapter, ring: ring, donut: donut, mount: mount, CSS: CSS, hex2rgba: hex2rgba, fit: fit };
  function barAdapter(cv, d, o) { bars(cv, d, o); }
})(window);
