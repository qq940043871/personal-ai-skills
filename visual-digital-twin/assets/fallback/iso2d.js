/* ============================================================
   DTIso — 零依赖 Canvas 2D 等距降级渲染器
   在 Three.js 无法加载时启用：手写 3D 旋转 + 30° 等距投影，
   保留体积感、数据流光与标签，数据面板功能完全不受影响。
   ============================================================ */
(function (w, d) {
  'use strict';

  var COS30 = Math.cos(Math.PI / 6), YK = .86;

  function hex(n) { return '#' + ('000000' + (n >>> 0).toString(16)).slice(-6); }
  function rgba(n, a) {
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  function shade(n, k) {
    var r = Math.min(255, Math.round(((n >> 16) & 255) * k)),
      g = Math.min(255, Math.round(((n >> 8) & 255) * k)),
      b = Math.min(255, Math.round((n & 255) * k));
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  function init(ctx) {
    var canvas = ctx.canvas, bus = ctx.bus;
    var c2 = canvas.getContext('2d');
    var nodes = (ctx.scene && ctx.scene.iso) ? ctx.scene.iso() : [];
    var theta = .9, autoRotate = true, focusId = null, focusMix = 0;
    var W = 0, H = 0, dpr = 1;
    var t0 = performance.now(), t = 0, last = t0;
    var flows = nodes.length ? nodes.map(function (n, i) { return { a: i, b: (i + 1) % nodes.length, p: i / nodes.length }; }) : [];

    function resize() {
      var r = canvas.getBoundingClientRect();
      if (!r.width || !r.height) return;
      dpr = Math.min(w.devicePixelRatio || 1, 2);
      W = r.width; H = r.height;
      canvas.width = Math.floor(W * dpr); canvas.height = Math.floor(H * dpr);
      c2.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    if (w.ResizeObserver) new w.ResizeObserver(resize).observe(canvas);
    w.addEventListener('resize', resize);

    function P(x, y, z) {
      var ct = Math.cos(theta), st = Math.sin(theta);
      var X = x * ct - z * st, Z = x * st + z * ct;
      var scale = Math.min(W, H) / 260;
      var cx = W / 2, cy = H / 2 + H * .06;
      return [cx + (X - Z) * COS30 * scale, cy + (X + Z) * (1 - YK + .5) * scale - y * scale * YK];
    }

    function poly(pts, fill, stroke, lw) {
      c2.beginPath();
      pts.forEach(function (p, i) { i ? c2.lineTo(p[0], p[1]) : c2.moveTo(p[0], p[1]); });
      c2.closePath();
      if (fill) { c2.fillStyle = fill; c2.fill(); }
      if (stroke) { c2.strokeStyle = stroke; c2.lineWidth = lw || 1; c2.stroke(); }
    }

    function roundNodes() {
      // 深度排序：画家算法
      return nodes.slice().sort(function (a, b) {
        var ao = a.x * Math.sin(theta) + a.z * Math.cos(theta);
        var bo = b.x * Math.sin(theta) + b.z * Math.cos(theta);
        return ao - bo;
      });
    }

    function gridFloor(scale) {
      c2.save();
      c2.strokeStyle = 'rgba(34,211,238,.10)'; c2.lineWidth = 1;
      var R = 120, step = 20;
      for (var g = -R; g <= R; g += step) {
        var a1 = P(g, 0, -R), a2 = P(g, 0, R);
        poly([a1, a2], null, 'rgba(34,211,238,.10)', 1);
        var b1 = P(-R, 0, g), b2 = P(R, 0, g);
        poly([b1, b2], null, 'rgba(34,211,238,.10)', 1);
      }
      // 地面扩散环
      for (var k = 0; k < 3; k++) {
        var rr = .3 + (t * .18 + k / 3) % 1 * .7;
        if (rr > .98) continue;
        c2.beginPath(); c2.ellipse(W / 2, H / 2 + H * .06, rr * Math.min(W, H) * .42, rr * Math.min(W, H) * .22, 0, 0, 6.2832);
        c2.strokeStyle = 'rgba(34,211,238,' + (.35 * (1 - rr)) + ')'; c2.lineWidth = 1.4; c2.stroke();
      }
      c2.restore();
    }

    function drawNode(n, active) {
      var hw = n.w / 2, hd = n.d / 2, hgt = n.h;
      var top = [
        P(n.x - hw, hgt, n.z - hd), P(n.x + hw, hgt, n.z - hd),
        P(n.x + hw, hgt, n.z + hd), P(n.x - hw, hgt, n.z + hd)
      ];
      var bot = [
        P(n.x - hw, 0, n.z - hd), P(n.x + hw, 0, n.z - hd),
        P(n.x + hw, 0, n.z + hd), P(n.x - hw, 0, n.z + hd)
      ];
      var col = n.color || 0x22d3ee;
      var alpha = active ? 1 : .92;
      // 右侧面
      poly([top[1], top[2], bot[2], bot[1]], rgba(col, .20 * alpha), rgba(col, .55), 1);
      // 左侧面
      poly([top[3], top[2], bot[2], bot[3]], rgba(col, .13 * alpha), rgba(col, .45), 1);
      // 顶面
      poly(top, rgba(col, active ? .5 : .34), shade(col, 1.35), 1.4);
      // 顶面棱线脉冲
      var pulse = (Math.sin(t * 2 + n.x * .1) + 1) / 2;
      poly([top[0], top[1]], null, rgba(col, .25 + pulse * .6), 1.6);
      // 竖向流光
      if (n.type === 'belt' || n.type === 'block') {
        var tt = (t * .5 + n.z * .02) % 1;
        var p = P(n.x - hw + n.w * tt, hgt + 1, n.z);
        c2.beginPath(); c2.arc(p[0], p[1], 2.6, 0, 6.2832);
        c2.fillStyle = 'rgba(255,255,255,.9)'; c2.fill();
        c2.beginPath(); c2.arc(p[0], p[1], 6, 0, 6.2832);
        c2.fillStyle = rgba(col, .3); c2.fill();
      }
      // 标签
      var lp = P(n.x, hgt + 12, n.z);
      c2.save();
      c2.font = '600 11px "PingFang SC","Microsoft YaHei",system-ui,sans-serif';
      var tw = c2.measureText(n.name).width;
      c2.fillStyle = 'rgba(4,14,32,.78)';
      c2.fillRect(lp[0] - tw / 2 - 6, lp[1] - 9, tw + 12, 17);
      c2.strokeStyle = rgba(col, .6); c2.lineWidth = 1;
      c2.strokeRect(lp[0] - tw / 2 - 6, lp[1] - 9, tw + 12, 17);
      c2.fillStyle = active ? '#ffffff' : '#bfe4ff';
      c2.textAlign = 'center'; c2.textBaseline = 'middle';
      c2.fillText(n.name, lp[0], lp[1]);
      c2.restore();
    }

    function drawFlows() {
      flows.forEach(function (f) {
        var A = nodes[f.a], B = nodes[f.b];
        if (!A || !B) return;
        var p = (f.p + t * .12) % 1;
        var x = A.x + (B.x - A.x) * p, z = A.z + (B.z - A.z) * p;
        var y = A.h + Math.sin(p * Math.PI) * 34 + 6;
        var pt = P(x, y, z);
        c2.beginPath(); c2.arc(pt[0], pt[1], 2.8, 0, 6.2832);
        c2.fillStyle = 'rgba(167,139,250,.95)'; c2.fill();
        c2.beginPath(); c2.arc(pt[0], pt[1], 7, 0, 6.2832);
        c2.fillStyle = 'rgba(167,139,250,.28)'; c2.fill();
      });
    }

    function frame(now) {
      var dt = Math.min((now - last) / 1000, .05); last = now; t += dt;
      if (autoRotate) theta += dt * .08;
      if (focusId) focusMix = Math.min(1, focusMix + dt * 2);
      c2.clearRect(0, 0, W, H);
      var g = c2.createRadialGradient(W / 2, H * .35, 10, W / 2, H * .5, Math.max(W, H) * .75);
      g.addColorStop(0, 'rgba(16,44,84,.55)'); g.addColorStop(1, 'rgba(2,5,13,0)');
      c2.fillStyle = g; c2.fillRect(0, 0, W, H);
      gridFloor();
      var list = roundNodes();
      for (var i = 0; i < list.length; i++) drawNode(list[i], list[i].id === focusId);
      drawFlows();
      c2.save();
      c2.fillStyle = 'rgba(139,179,217,.55)';
      c2.font = '11px system-ui,sans-serif'; c2.textAlign = 'left';
      c2.fillText('等距降级模式 · 拖拽可旋转视角 · 滚轮缩放', 12, H - 12);
      c2.restore();
      raf = requestAnimationFrame(frame);
    }
    var raf = requestAnimationFrame(frame);

    // 交互：拖拽旋转 / 滚轮缩放（视觉缩放用 W/H 重算不便，改为节点高度微调 + 旋转）
    var dragging = false, lx = 0, zoom = 1;
    canvas.addEventListener('mousedown', function (e) { dragging = true; lx = e.clientX; });
    w.addEventListener('mouseup', function () { dragging = false; });
    w.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      theta += (e.clientX - lx) * .006; lx = e.clientX;
    });
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      zoom = Math.max(.6, Math.min(1.8, zoom * (e.deltaY > 0 ? .94 : 1.06)));
      nodes.forEach(function (n) { n._h0 = n._h0 || n.h; n.h = n._h0 * zoom; });
    }, { passive: false });

    bus.on('layer', function (p) {
      nodes.forEach(function (n) { if (n.type === p.id || n.id === p.id) n._hide = !p.on; });
      nodes = nodes.filter(function (n) { return true; });
    });
    bus.on('focus', function (p) { ctrl.focus(String(p.id || '')); });
    bus.on('orbit', function (on) { autoRotate = on; });
    bus.on('cmd', function (c) { if (c === 'reset') { theta = .9; zoom = 1; nodes.forEach(function (n) { if (n._h0) n.h = n._h0; }); } });

    var ctrl = {
      stats: function () { return { fps: 60, faces: nodes.length * 12 }; },
      setLayer: function (id, on) { nodes.forEach(function (n) { if (n.id === id) n.hidden = !on; }); },
      focus: function (id) {
        focusId = id; focusMix = 0; autoRotate = false;
        setTimeout(function () { autoRotate = true; focusId = null; }, 6000);
      },
      dispose: function () { cancelAnimationFrame(raf); }
    };
    return ctrl;
  }

  w.DTIso = { init: init };
})(window, document);
