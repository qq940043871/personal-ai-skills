/* ============================================================
   Scene: city — 智慧城市 / 园区楼宇数字孪生
   程序化生成街区（InstancedMesh 分区） + 路网流光 + 跨区飞线 +
   地标呼吸光柱 + 昼夜色调 + 分区聚焦
   统一接口：{ id, name, camera, iso(), init(ctx) -> ctrl }
   ============================================================ */
(function (w) {
  'use strict';

  var DISTRICTS = [
    { id: 'cbd', name: '中央商务区', color: 0x3b82f6, ring: 30, inner: 8, hMin: 26, hMax: 88, count: 130, pos: [0, 0, 0] },
    { id: 'tech', name: '科创园区', color: 0x22d3ee, ring: 26, inner: 6, hMin: 14, hMax: 46, count: 110, pos: [-92, 0, -58] },
    { id: 'resi', name: '居住社区', color: 0x2dd4bf, ring: 24, inner: 7, hMin: 10, hMax: 34, count: 150, pos: [96, 0, -46] },
    { id: 'indust', name: '智造片区', color: 0xa855f7, ring: 22, inner: 6, hMin: 8, hMax: 24, count: 90, pos: [78, 0, 84] },
    { id: 'trans', name: '交通枢纽', color: 0xfbbf24, ring: 20, inner: 5, hMin: 6, hMax: 20, count: 70, pos: [-84, 0, 80] }
  ];

  function windowTexture() {
    var cv = document.createElement('canvas'); cv.width = 32; cv.height = 64;
    var ctx = cv.getContext('2d');
    ctx.fillStyle = '#040a16'; ctx.fillRect(0, 0, 32, 64);
    for (var y = 2; y < 62; y += 5) {
      for (var x = 2; x < 30; x += 6) {
        var r = Math.random();
        if (r > .55) {
          ctx.fillStyle = r > .88 ? 'rgba(255,236,190,.95)' : r > .72 ? 'rgba(126,217,255,.85)' : 'rgba(59,130,246,.5)';
          ctx.fillRect(x, y, 3.4, 2.6);
        }
      }
    }
    var t = new w.THREE.CanvasTexture(cv);
    if (w.THREE.sRGBEncoding) t.encoding = w.THREE.sRGBEncoding;
    return t;
  }

  function init(ctx) {
    var THREE = ctx.THREE, canvas = ctx.canvas, bus = ctx.bus;
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(w.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    if (THREE.sRGBEncoding) renderer.outputEncoding = THREE.sRGBEncoding;

    var scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050b18, .0021);
    var camera = new THREE.PerspectiveCamera(42, 1, .5, 4000);
    camera.position.set(150, 130, 190);

    scene.add(new THREE.AmbientLight(0x4a7dbd, .95));
    var key = new THREE.DirectionalLight(0x9fd6ff, .75); key.position.set(120, 200, 90); scene.add(key);
    var rimC = new THREE.PointLight(0x22d3ee, 1.5, 420); rimC.position.set(-120, 70, -70); scene.add(rimC);
    var rimV = new THREE.PointLight(0xa855f7, 1.2, 420); rimV.position.set(130, 60, 110); scene.add(rimV);

    var root = new THREE.Group(); scene.add(root);
    var winTex = windowTexture();

    /* ---------- 地面 ---------- */
    var grid = w.DTH.ground(520, 52, 0x1e4d7a);
    root.add(grid);
    var base = new THREE.Mesh(
      new THREE.CircleGeometry(240, 96),
      new THREE.MeshBasicMaterial({ color: 0x06142c, transparent: true, opacity: .92 })
    );
    base.rotation.x = -Math.PI / 2; base.position.y = -.2; root.add(base);
    var rings = w.DTH.radar(150, 0x22d3ee, { count: 3, speed: .22 }); rings.position.y = .3; root.add(rings);

    /* ---------- 分区楼宇 ---------- */
    var groups = {}, pickTargets = [];
    DISTRICTS.forEach(function (dd, di) {
      var rnd = w.DTH.rng(di * 7919 + 13);
      var geo = new THREE.BoxGeometry(1, 1, 1);
      var mat = new THREE.MeshPhongMaterial({
        color: 0x122842,
        map: winTex, emissive: dd.color, emissiveIntensity: .45,
        shininess: 40, transparent: true, opacity: .96
      });
      var im = new THREE.InstancedMesh(geo, mat, dd.count);
      var capMat = new THREE.MeshBasicMaterial({ color: dd.color, transparent: true, opacity: .85, blending: THREE.AdditiveBlending, depthWrite: false });
      var caps = new THREE.InstancedMesh(new THREE.BoxGeometry(1, .5, 1), capMat, dd.count);

      var mtx = new THREE.Matrix4(), pos = new THREE.Vector3(), scl = new THREE.Vector3(), q = new THREE.Quaternion();
      for (var i = 0; i < dd.count; i++) {
        var ang = rnd() * Math.PI * 2;
        var rad = dd.inner + Math.sqrt(rnd()) * dd.ring;
        var bw = 4 + rnd() * 7, bd = 4 + rnd() * 7;
        var bh = dd.hMin + Math.pow(rnd(), 1.7) * (dd.hMax - dd.hMin);
        var x = dd.pos[0] + Math.cos(ang) * rad, z = dd.pos[2] + Math.sin(ang) * rad;
        pos.set(x, bh / 2, z); scl.set(bw, bh, bd);
        mtx.compose(pos, q, scl); im.setMatrixAt(i, mtx);
        pos.set(x, bh + .5, z); scl.set(bw * 1.02, .5, bd * 1.02);
        mtx.compose(pos, q, scl); caps.setMatrixAt(i, mtx);
      }
      im.instanceMatrix.needsUpdate = caps.instanceMatrix.needsUpdate = true;
      im.userData.data = { name: dd.name, desc: dd.count + ' 栋建筑接入', metrics: [['在线设备', (dd.count * 3.2).toFixed(0), '台']] };
      im.userData.layer = 'buildings';
      var g = new THREE.Group(); g.add(im); g.add(caps);
      g.userData.dd = dd;
      root.add(g);

      var lb = w.DTH.label(dd.name, { fontSize: 26, scale: 1.5, accent: '#' + new THREE.Color(dd.color).getHexString(), bg: 'rgba(4,14,32,.8)' });
      lb.position.set(dd.pos[0], dd.hMax + 22, dd.pos[2]);
      lb.userData.layer = 'labels';
      root.add(lb);

      var bc = w.DTH.beacon(2.4, dd.hMax + 16, dd.color);
      bc.position.set(dd.pos[0], (dd.hMax + 16) / 2, dd.pos[2]);
      bc.userData.layer = 'beacon';
      root.add(bc);

      groups[dd.id] = { group: g, cap: caps, body: im, label: lb, bc: bc, dd: dd };
      pickTargets.push(im);
    });

    /* ---------- 路网流光 ---------- */
    var roads = new THREE.Group(); roads.userData.layer = 'roads';
    var roadSet = [];
    DISTRICTS.forEach(function (dd, i) {
      if (i === 0) return;
      roadSet.push([
        new THREE.Vector3(dd.pos[0], .6, dd.pos[2]),
        new THREE.Vector3(dd.pos[0] * .55, .6, dd.pos[2] * .55),
        new THREE.Vector3(0, .6, 0)
      ]);
    });
    roadSet.forEach(function (arr) {
      var curve = new THREE.CatmullRomCurve3(arr);
      var pts = curve.getPoints(60);
      roads.add(w.DTH.neonLine(pts, 0x22d3ee, { opacity: .45 }));
      var fl = w.DTH.flow(curve, { count: 4, size: 3, color: 0x7dd3fc, speed: .3 });
      roads.add(fl);
      if (!roads.userData.flows) roads.userData.flows = [];
      roads.userData.flows.push(fl);
    });
    // 环形主干道
    [[70, 0x3b82f6], [126, 0x22d3ee], [190, 0xa855f7]].forEach(function (r) {
      var pts = [];
      for (var a = 0; a <= 64; a++) {
        var t = a / 64 * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(t) * r[0], .5, Math.sin(t) * r[0]));
      }
      roads.add(w.DTH.neonLine(pts, r[1], { opacity: .35 }));
      var cir = new THREE.CatmullRomCurve3(pts, true);
      var f = w.DTH.flow(cir, { count: 5, size: 2.6, color: r[1], speed: .18 });
      roads.add(f);
      (roads.userData.flows = roads.userData.flows || []).push(f);
    });
    root.add(roads);

    /* ---------- 跨区飞线 ---------- */
    var fly = new THREE.Group(); fly.userData.layer = 'fly';
    for (var i = 0; i < DISTRICTS.length; i++) {
      for (var j = i + 1; j < DISTRICTS.length; j++) {
        if (Math.random() > .55) continue;
        var a = DISTRICTS[i].pos, b = DISTRICTS[j].pos;
        var mid = new THREE.Vector3((a[0] + b[0]) / 2, 70 + Math.random() * 40, (a[2] + b[2]) / 2);
        var cv = new THREE.QuadraticBezierCurve3(
          new THREE.Vector3(a[0], 24, a[2]), mid, new THREE.Vector3(b[0], 24, b[2]));
        fly.add(w.DTH.neonLine(cv.getPoints(40), 0x7dd3fc, { opacity: .22 }));
        fly.add(w.DTH.flow(cv, { count: 2, size: 4, color: 0xa855f7, speed: .35 }));
      }
    }
    root.add(fly);

    /* ---------- 交互 ---------- */
    var orbit = w.DTH.Orbit(camera, canvas, { target: new THREE.Vector3(0, 14, 0), radius: 330, phi: 1.08, theta: 1.1, auto: true, speed: .045, maxDistance: 700, minDistance: 60 });
    var pk = w.DTH.picker(renderer, camera, canvas);
    pk.setTargets(pickTargets);
    canvas.addEventListener('mousemove', pk.onMove);
    canvas.addEventListener('click', function () {
      var hit = pk.pick();
      if (hit) { bus.emit('focus', { id: 'district:' + hit.obj.parent.userData.dd.id }); ctx.toast('已定位：' + hit.obj.parent.userData.dd.name); }
    });
    bus.on('cmd', function (cmd) { if (cmd === 'reset') orbit.reset(); });
    bus.on('orbit', function (on) { orbit.auto = on; });
    bus.on('layer', function (p) { ctrl.setLayer(p.id, p.on); });
    bus.on('focus', function (p) {
      var id = String(p.id || '').replace('district:', '');
      ctrl.focus(id);
    });

    function resize() {
      var r = canvas.getBoundingClientRect();
      if (!r.width || !r.height) return;
      renderer.setSize(r.width, r.height, false);
      camera.aspect = r.width / r.height; camera.updateProjectionMatrix();
    }
    resize();
    if (w.ResizeObserver) new w.ResizeObserver(resize).observe(canvas);
    w.addEventListener('resize', resize);

    var clock = new THREE.Clock(), acc = 0, fps = 60;
    function loop() {
      var dt = Math.min(clock.getDelta(), .05), t = clock.elapsedTime;
      acc += dt; fps = Math.round(fps * .92 + (1 / Math.max(dt, .001)) * .08);
      orbit.update(dt);
      rings.update(dt);
      (roads.userData.flows || []).forEach(function (f) { f.update(dt); });
      root.traverse(function (o) { if (o.update) o.update(dt, t); });
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    }
    var raf = requestAnimationFrame(loop);

    var ctrl = {
      stats: function () { return { fps: fps, faces: renderer.info.render.triangles }; },
      setLayer: function (id, on) {
        root.traverse(function (o) { if (o.userData && o.userData.layer === id) o.visible = on; });
        if (id === 'buildings') Object.keys(groups).forEach(function (k) {
          groups[k].body.visible = on; groups[k].cap.visible = on;
        });
      },
      focus: function (id) {
        var g = groups[id]; if (!g) return;
        var p = g.dd.pos;
        orbit.flyTo(new THREE.Vector3(p[0], 12, p[2]), 110, 1.05, Math.random() * 6.28);
        orbit.auto = false;
        Object.keys(groups).forEach(function (k) {
          groups[k].bc.visible = true;
          groups[k].bc.material.opacity = k === id ? .6 : .1;
        });
      },
      dispose: function () { cancelAnimationFrame(raf); renderer.dispose(); }
    };
    return ctrl;
  }

  w.__DT_SCENE__ = {
    id: 'city', name: '智慧城市 / 园区楼宇',
    camera: { pos: [150, 130, 190], target: [0, 14, 0] },
    init: init,
    iso: function () {
      return DISTRICTS.map(function (dd) {
        return { type: 'block', id: dd.id, name: dd.name, color: dd.color, x: dd.pos[0] / 2.4, z: dd.pos[2] / 2.4, w: dd.ring, d: dd.ring, h: dd.hMax };
      });
    }
  };
})(window);
