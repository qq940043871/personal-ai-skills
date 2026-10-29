/* ============================================================
   DTH — Three.js 场景工具箱（兼容 three r128 / r149 UMD 全局版）
   提供：伪随机、贴图标签、光晕精灵、简易轨道控制器、地面网格、
        流光曲线、雷达扫描环、射线拾取
   ============================================================ */
(function (w) {
  'use strict';

  var P = {
    cyan: 0x22d3ee, blue: 0x3b82f6, violet: 0xa855f7, teal: 0x2dd4bf,
    amber: 0xfbbf24, rose: 0xfb7185, white: 0xe6f4ff, deep: 0x0a1a33
  };

  /** 可复现伪随机 */
  function rng(seed) {
    var s = seed || 1;
    return function () {
      s = (s * 1664525 + 1013904223) % 4294967296;
      return s / 4294967296;
    };
  }

  /** 生成带科技边框的文字贴图 Sprite */
  function label(text, opt) {
    var THREE = w.THREE;
    opt = opt || {};
    var fs = opt.fontSize || 30, pad = opt.pad || 12;
    var cv = document.createElement('canvas');
    var ctx = cv.getContext('2d');
    ctx.font = '600 ' + fs + 'px "PingFang SC","Microsoft YaHei",system-ui,sans-serif';
    var tw = Math.ceil(ctx.measureText(text).width);
    cv.width = Math.ceil(tw + pad * 4); cv.height = Math.ceil(fs * 2.1);
    ctx = cv.getContext('2d');
    // 背板
    ctx.fillStyle = opt.bg || 'rgba(6,20,42,.82)';
    roundRect(ctx, 1, 1, cv.width - 2, cv.height - 2, 6); ctx.fill();
    ctx.strokeStyle = opt.border || 'rgba(34,211,238,.55)'; ctx.lineWidth = 1.5;
    roundRect(ctx, 1, 1, cv.width - 2, cv.height - 2, 6); ctx.stroke();
    // 左侧高亮竖条
    ctx.fillStyle = opt.accent || '#22d3ee';
    ctx.fillRect(1, cv.height * .22, 3, cv.height * .56);
    ctx.font = '600 ' + fs + 'px "PingFang SC","Microsoft YaHei",system-ui,sans-serif';
    ctx.fillStyle = opt.color || '#e6f4ff';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.shadowColor = opt.accent || '#22d3ee'; ctx.shadowBlur = 8;
    ctx.fillText(text, cv.width / 2, cv.height / 2 + 1);

    var tex = new THREE.CanvasTexture(cv);
    if (THREE.sRGBEncoding) tex.encoding = THREE.sRGBEncoding;
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({
      map: tex, transparent: true, depthTest: opt.depthTest !== false, depthWrite: false
    }));
    var scale = opt.scale || 1;
    sp.scale.set(cv.width / 90 * scale, cv.height / 90 * scale, 1);
    sp.userData.aspect = cv.width / cv.height;
    return sp;
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  }

  /** 径向渐变光晕精灵（模拟 Bloom） */
  function glowSprite(color, size, opacity) {
    var THREE = w.THREE;
    var cv = document.createElement('canvas'); cv.width = cv.height = 128;
    var ctx = cv.getContext('2d');
    var g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(.28, 'rgba(255,255,255,.55)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, 128, 128);
    var tex = new THREE.CanvasTexture(cv);
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({
      map: tex, color: color, transparent: true, opacity: opacity == null ? .9 : opacity,
      blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false
    }));
    sp.scale.set(size, size, 1);
    return sp;
  }

  function glowTexture(colorInner, colorOuter) {
    var cv = document.createElement('canvas'); cv.width = cv.height = 64;
    var ctx = cv.getContext('2d');
    var g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, colorInner || 'rgba(255,255,255,1)');
    g.addColorStop(1, colorOuter || 'rgba(255,255,255,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, 64, 64);
    var t = new w.THREE.CanvasTexture(cv);
    if (w.THREE.sRGBEncoding) t.encoding = w.THREE.sRGBEncoding;
    return t;
  }

  /** 极简轨道控制器：左键旋转 / 滚轮缩放 / 右键平移 / 阻尼 */
  function Orbit(camera, dom, opt) {
    opt = opt || {};
    var target = opt.target || new w.THREE.Vector3();
    var sph = new w.THREE.Spherical();
    var off = camera.position.clone().sub(target);
    sph.setFromVector3(off);
    var state = { sph: sph, tSph: sph.clone(), target: target, tTarget: target.clone(), down: 0, auto: opt.auto !== false, speed: opt.speed || .06, dragging: false, enabled: true };
    var minD = opt.minDistance || 20, maxD = opt.maxDistance || 900;
    var minP = opt.minPolar == null ? .12 : opt.minPolar, maxP = opt.maxPolar == null ? 1.52 : opt.maxPolar;
    var last = { x: 0, y: 0 };

    function down(e) { if (!state.enabled) return; state.down = e.button === 2 ? 2 : 1; last.x = e.clientX; last.y = e.clientY; state.dragging = true; }
    function move(e) {
      if (!state.dragging || !state.enabled) return;
      var dx = e.clientX - last.x, dy = e.clientY - last.y;
      last.x = e.clientX; last.y = e.clientY;
      if (state.down === 1) {
        state.auto = false;
        state.tSph.theta -= dx * .005;
        state.tSph.phi = Math.max(minP, Math.min(maxP, state.tSph.phi - dy * .005));
      } else {
        var p = new w.THREE.Vector3().subVectors(camera.position, target);
        var right = new w.THREE.Vector3().crossVectors(camera.up, p).normalize();
        var upv = new w.THREE.Vector3().crossVectors(p, right).normalize();
        var k = p.length() * .0016;
        state.tTarget.addScaledVector(right, dx * k).addScaledVector(upv, -dy * k);
      }
    }
    function up() { state.dragging = false; state.down = 0; }
    function wheel(e) {
      if (!state.enabled) return;
      e.preventDefault();
      state.tSph.radius = Math.max(minD, Math.min(maxD, state.tSph.radius * (1 + (e.deltaY > 0 ? .1 : -.1))));
    }
    dom.addEventListener('mousedown', down);
    w.addEventListener('mousemove', move);
    w.addEventListener('mouseup', up);
    dom.addEventListener('wheel', wheel, { passive: false });
    dom.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    // 触摸
    dom.addEventListener('touchstart', function (e) { down({ button: 1, clientX: e.touches[0].clientX, clientY: e.touches[0].clientY }); });
    dom.addEventListener('touchmove', function (e) { e.preventDefault(); move(e.touches[0]); }, { passive: false });
    dom.addEventListener('touchend', up);

    state.update = function (dt) {
      if (state.auto) state.tSph.theta += state.speed * dt;
      var k = 1 - Math.pow(.0015, dt);
      state.sph.radius += (state.tSph.radius - state.sph.radius) * k;
      state.sph.theta += (state.tSph.theta - state.sph.theta) * k;
      state.sph.phi += (state.tSph.phi - state.sph.phi) * k;
      target.lerp(state.tTarget, k);
      camera.position.copy(target).add(new w.THREE.Vector3().setFromSpherical(state.sph));
      camera.lookAt(target);
    };
    state.reset = function () { state.tSph.set(opt.radius || 200, opt.phi || 1.0, opt.theta || 0.8); state.tTarget.set(0, 0, 0); };
    state.flyTo = function (v, radius, phi, theta) {
      state.tTarget.copy(v);
      if (radius) state.tSph.radius = radius;
      if (phi) state.tSph.phi = phi;
      if (theta != null) state.tSph.theta = theta;
    };
    return state;
  }

  /** 发光线框材质（半透明科技感） */
  function neonLine(points, color, opt) {
    var THREE = w.THREE;
    opt = opt || {};
    var g = new THREE.BufferGeometry().setFromPoints(points);
    var m = new THREE.LineBasicMaterial({
      color: color, transparent: true, opacity: opt.opacity == null ? .55 : opt.opacity,
      blending: opt.additive === false ? THREE.NormalBlending : THREE.AdditiveBlending, depthWrite: false
    });
    return new THREE.Line(g, m);
  }

  /** 地面网格 + 渐变圆盘 */
  function ground(size, div, color, centerLine) {
    var THREE = w.THREE;
    var g = new THREE.Group();
    var grid = new THREE.GridHelper(size, div, color, color);
    grid.material.opacity = .18; grid.material.transparent = true;
    g.add(grid);
    if (centerLine !== false) {
      var c = 0x1e4d7a;
      var geo = new THREE.RingGeometry(size * .46, size * .48, 96);
      var mat = new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: .5, side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
      var r = new THREE.Mesh(geo, mat); r.rotation.x = -Math.PI / 2; r.position.y = .2;
      g.add(r);
    }
    return g;
  }

  /** 流光：沿曲线运动的光点组 */
  function flow(curve, opt) {
    var THREE = w.THREE;
    opt = opt || {};
    var count = opt.count || 3, size = opt.size || 3.2, color = opt.color || P.cyan;
    var grp = new THREE.Group();
    var geo = new THREE.SphereGeometry(size * .34, 10, 10);
    var mat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: .95, blending: THREE.AdditiveBlending, depthWrite: false });
    var items = [];
    for (var i = 0; i < count; i++) {
      var m = new THREE.Mesh(geo, mat);
      var halo = glowSprite(color, size * 2.4, .7);
      m.add(halo);
      grp.add(m);
      items.push({ mesh: m, t: i / count, spd: opt.speed || .22 });
    }
    grp.update = function (dt) {
      for (var i = 0; i < items.length; i++) {
        var it = items[i];
        it.t += dt * it.spd; if (it.t > 1) it.t -= 1;
        var p = curve.getPointAt(Math.max(.0001, Math.min(.9999, it.t)));
        it.mesh.position.copy(p);
      }
    };
    return grp;
  }

  /** 雷达 / 扩散波环 */
  function radar(radius, color, opt) {
    var THREE = w.THREE;
    opt = opt || {};
    var count = opt.count || 3;
    var grp = new THREE.Group();
    var rings = [];
    for (var i = 0; i < count; i++) {
      var g = new THREE.RingGeometry(radius * .97, radius, 72);
      var m = new THREE.MeshBasicMaterial({
        color: color, transparent: true, opacity: .55, side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending, depthWrite: false
      });
      var mesh = new THREE.Mesh(g, m);
      mesh.rotation.x = -Math.PI / 2;
      grp.add(mesh); rings.push({ m: mesh, t: i / count });
    }
    grp.update = function (dt) {
      for (var i = 0; i < rings.length; i++) {
        var r = rings[i]; r.t += dt * (opt.speed || .28); if (r.t > 1) r.t -= 1;
        var s = .1 + r.t * 1.6;
        r.m.scale.set(s, s, s);
        r.m.material.opacity = .6 * (1 - r.t);
      }
    };
    return grp;
  }

  /** 竖直扫描光柱（建筑/设备上方的呼吸光） */
  function beacon(radius, height, color) {
    var THREE = w.THREE;
    var geo = new THREE.CylinderGeometry(radius * .35, radius, height, 16, 1, true);
    var mat = new THREE.MeshBasicMaterial({
      color: color, transparent: true, opacity: .22, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, depthWrite: false
    });
    var m = new THREE.Mesh(geo, mat);
    m.update = function (dt, t) { m.material.opacity = .12 + Math.abs(Math.sin(t)) * .22; };
    return m;
  }

  /** 射线拾取 */
  function picker(renderer, camera, dom) {
    var THREE = w.THREE;
    var ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), last = { x: -1, y: -1 }, targets = [];
    return {
      setTargets: function (t) { targets = t; },
      onMove: function (e) {
        var r = dom.getBoundingClientRect();
        last.x = e.clientX - r.left; last.y = e.clientY - r.top;
        mouse.x = (last.x / r.width) * 2 - 1;
        mouse.y = -(last.y / r.height) * 2 + 1;
      },
      pick: function () {
        if (!targets.length) return null;
        ray.setFromCamera(mouse, camera);
        var hits = ray.intersectObjects(targets, false);
        for (var i = 0; i < hits.length; i++) {
          if (hits[i].object.visible && hits[i].object.userData.data) return { obj: hits[i].object, data: hits[i].object.userData.data, point: hits[i].point };
        }
        return null;
      },
      screen: function () { return last; }
    };
  }

  w.DTH = {
    P: P, rng: rng, label: label, glowSprite: glowSprite, glowTexture: glowTexture,
    Orbit: Orbit, neonLine: neonLine, ground: ground, flow: flow, radar: radar,
    beacon: beacon, picker: picker, roundRect: roundRect
  };
})(window);
