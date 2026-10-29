/* ============================================================
   Scene: factory — 智慧工厂 / 产线数字孪生
   厂房外壳 + 传送带产线 + 反应罐组 + 管道流向 + AGV 巡检 + 设备状态灯
   ============================================================ */
(function (w) {
  'use strict';

  var LINES = [
    { id: 'l1', name: '一号装配线', z: -18, len: 74, speed: 9, color: 0x22d3ee, status: 'run' },
    { id: 'l2', name: '二号焊装线', z: 0, len: 74, speed: 7, color: 0x3b82f6, status: 'run' },
    { id: 'l3', name: '三号检测线', z: 18, len: 74, speed: 5.5, color: 0x2dd4bf, status: 'warn' }
  ];
  var TANKS = [
    { id: 't1', name: '配料反应釜 A', x: -46, z: -30, h: 22, r: 6, status: 'normal' },
    { id: 't2', name: '配料反应釜 B', x: -46, z: -14, h: 22, r: 6, status: 'normal' },
    { id: 't3', name: '恒温储罐', x: -46, z: 4, h: 26, r: 7, status: 'alarm' },
    { id: 't4', name: '成品缓存罐', x: 46, z: -30, h: 20, r: 5.5, status: 'normal' },
    { id: 't5', name: '回收处理罐', x: 46, z: -12, h: 20, r: 5.5, status: 'warn' }
  ];
  var STATUS_COLOR = { normal: 0x34d399, warn: 0xfbbf24, alarm: 0xfb7185, run: 0x60a5fa };

  function beltTexture() {
    var cv = document.createElement('canvas'); cv.width = 16; cv.height = 16;
    var x = cv.getContext('2d');
    x.fillStyle = '#0b1c34'; x.fillRect(0, 0, 16, 16);
    x.fillStyle = 'rgba(34,211,238,.55)';
    for (var i = 0; i < 16; i += 4) x.fillRect(i, 0, 1.6, 16);
    var t = new w.THREE.CanvasTexture(cv);
    t.wrapS = t.wrapT = w.THREE.RepeatWrapping;
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
    scene.fog = new THREE.FogExp2(0x050b18, .0032);
    var camera = new THREE.PerspectiveCamera(45, 1, .5, 3000);
    camera.position.set(96, 74, 118);

    scene.add(new THREE.AmbientLight(0x5583b8, 1.05));
    var d1 = new THREE.DirectionalLight(0xbfe4ff, .8); d1.position.set(60, 120, 40); scene.add(d1);
    var p1 = new THREE.PointLight(0x22d3ee, 1.4, 220); p1.position.set(-50, 40, -20); scene.add(p1);
    var p2 = new THREE.PointLight(0xa855f7, 1.1, 220); p2.position.set(55, 36, 30); scene.add(p2);

    var root = new THREE.Group(); scene.add(root);
    root.add(w.DTH.ground(360, 36, 0x1e4d7a));

    /* ---------- 厂房外壳（半透明 + 轮廓） ---------- */
    var shell = new THREE.Group(); shell.userData.layer = 'shell';
    var shellMat = new THREE.MeshPhongMaterial({
      color: 0x0d2a4a, transparent: true, opacity: .16, shininess: 10
    });
    var hall = new THREE.Mesh(new THREE.BoxGeometry(150, 40, 96), shellMat);
    hall.position.set(0, 20, 0); shell.add(hall);
    var edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(150, 40, 96)),
      new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: .5 })
    );
    edges.position.copy(hall.position); shell.add(edges);
    // 屋顶桁架
    for (var i = -70; i <= 70; i += 14) {
      var truss = new THREE.Mesh(
        new THREE.BoxGeometry(.8, .8, 96),
        new THREE.MeshBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: .35, blending: THREE.AdditiveBlending })
      );
      truss.position.set(i, 40.2, 0); shell.add(truss);
    }
    root.add(shell);

    /* ---------- 产线 ---------- */
    var beltTex = beltTexture(), lines = {}, products = [];
    var linesGrp = new THREE.Group(); linesGrp.userData.layer = 'lines';
    LINES.forEach(function (L) {
      var belt = new THREE.Mesh(
        new THREE.BoxGeometry(L.len, 1.6, 9),
        new THREE.MeshPhongMaterial({ map: beltTex.clone(), color: 0x14395c, emissive: L.color, emissiveIntensity: .22, shininess: 30 })
      );
      belt.material.map.repeat.set(L.len / 6, 1);
      belt.material.map.needsUpdate = true;
      belt.position.set(0, 7, L.z);
      belt.userData.scroll = true; belt.userData.speed = L.speed;
      linesGrp.add(belt);
      // 支腿
      for (var x = -L.len / 2 + 6; x < L.len / 2; x += 14) {
        var leg = new THREE.Mesh(new THREE.BoxGeometry(1.2, 7, 1.2),
          new THREE.MeshPhongMaterial({ color: 0x1a3a5e }));
        leg.position.set(x, 3.5, L.z); linesGrp.add(leg);
      }
      // 头部/尾部设备
      [-1, 1].forEach(function (s) {
        var unit = new THREE.Mesh(new THREE.BoxGeometry(8, 12, 12),
          new THREE.MeshPhongMaterial({ color: 0x16375c, emissive: L.color, emissiveIntensity: .16, shininess: 40 }));
        unit.position.set(s * (L.len / 2 + 3), 8, L.z);
        linesGrp.add(unit);
      });
      // 线上工件
      var rnd = w.DTH.rng(Math.abs(L.z) + 7);
      for (var k = 0; k < 9; k++) {
        var prod = new THREE.Mesh(new THREE.BoxGeometry(4.4, 4.4, 4.4),
          new THREE.MeshPhongMaterial({ color: 0x9be8ff, emissive: L.color, emissiveIntensity: .55, shininess: 60 }));
        prod.position.set(-L.len / 2 + rnd() * L.len, 9.4, L.z);
        linesGrp.add(prod);
        products.push({ m: prod, spd: L.speed, min: -L.len / 2, max: L.len / 2 });
      }
      var lb = w.DTH.label(L.name, { fontSize: 22, scale: 1.1, accent: '#' + new THREE.Color(L.color).getHexString() });
      lb.position.set(0, 20, L.z); lb.userData.layer = 'labels'; linesGrp.add(lb);
      lines[L.id] = belt;
    });
    root.add(linesGrp);

    /* ---------- 反应罐组 ---------- */
    var tanksRoot = new THREE.Group(); tanksRoot.userData.layer = 'tanks';
    var tankMap = {};
    TANKS.forEach(function (T, i) {
      var g = new THREE.Group();
      var bodyMat = new THREE.MeshPhongMaterial({ color: 0x17385c, emissive: STATUS_COLOR[T.status], emissiveIntensity: .18, shininess: 60, transparent: true, opacity: .96 });
      var body = new THREE.Mesh(new THREE.CylinderGeometry(T.r, T.r, T.h, 24, 1), bodyMat);
      body.position.y = T.h / 2 + 4; g.add(body);
      var cap = new THREE.Mesh(new THREE.SphereGeometry(T.r, 24, 12, 0, 6.2832, 0, 1.2),
        new THREE.MeshPhongMaterial({ color: 0x1d4a78, shininess: 70 }));
      cap.position.y = T.h + 4; g.add(cap);
      // 箍圈
      for (var b = 1; b <= 3; b++) {
        var ring = new THREE.Mesh(new THREE.TorusGeometry(T.r * 1.02, .35, 8, 32),
          new THREE.MeshBasicMaterial({ color: STATUS_COLOR[T.status], transparent: true, opacity: .6, blending: THREE.AdditiveBlending }));
        ring.rotation.x = Math.PI / 2; ring.position.y = 4 + T.h * b / 4; g.add(ring);
      }
      // 状态灯
      var lamp = w.DTH.glowSprite(STATUS_COLOR[T.status], T.h * .55, .95);
      lamp.position.y = T.h + 10; lamp.userData.lamp = true; g.add(lamp);
      var lb = w.DTH.label(T.name, { fontSize: 20, scale: .95, accent: '#' + new THREE.Color(STATUS_COLOR[T.status]).getHexString() });
      lb.position.set(0, T.h + 17, 0); lb.userData.layer = 'labels'; g.add(lb);
      g.position.set(T.x, 0, T.z);
      g.userData.data = { name: T.name, desc: '设备状态：' + T.status, metrics: [['液位', (40 + i * 9) + '', '%']] };
      tanksRoot.add(g);
      tankMap[T.id] = g;
    });
    root.add(tanksRoot);

    /* ---------- 管道 + 流向 ---------- */
    var pipes = new THREE.Group(); pipes.userData.layer = 'pipes';
    var pipeMat = new THREE.MeshPhongMaterial({ color: 0x2a6ba8, shininess: 60, transparent: true, opacity: .9 });
    var routes = [
      [[-46, 12, -30], [-46, 30, -30], [-20, 30, -18], [0, 26, -18]],
      [[-46, 12, -14], [-40, 34, -14], [-10, 34, 0], [0, 26, 0]],
      [[-46, 12, 4], [-46, 36, 4], [-16, 36, 12], [0, 26, 18]],
      [[70, 10, -18], [70, 30, -18], [46, 26, -30]],
      [[70, 10, 18], [64, 28, 18], [46, 24, -12]]
    ];
    var pipeFlows = [];
    routes.forEach(function (r) {
      var curve = new THREE.CatmullRomCurve3(r.map(function (p) { return new THREE.Vector3(p[0], p[1], p[2]); }));
      var tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, 1.5, 10, false), pipeMat);
      pipes.add(tube);
      var f = w.DTH.flow(curve, { count: 3, size: 2.6, color: 0x7dd3fc, speed: .3 });
      pipes.add(f); pipeFlows.push(f);
    });
    root.add(pipes);

    /* ---------- AGV 巡检小车 ---------- */
    var agvs = new THREE.Group(); agvs.userData.layer = 'agv';
    var agvPath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-64, .8, 42), new THREE.Vector3(0, .8, 44), new THREE.Vector3(64, .8, 42),
      new THREE.Vector3(68, .8, 20), new THREE.Vector3(0, .8, 34), new THREE.Vector3(-66, .8, 22)
    ], true);
    agvs.add(w.DTH.neonLine(agvPath.getPoints(80), 0xfbbf24, { opacity: .3 }));
    var agvList = [];
    for (var a = 0; a < 3; a++) {
      var car = new THREE.Group();
      var bodyC = new THREE.Mesh(new THREE.BoxGeometry(6, 2.6, 3.6),
        new THREE.MeshPhongMaterial({ color: 0x1d3f66, emissive: 0xfbbf24, emissiveIntensity: .3, shininess: 60 }));
      car.add(bodyC);
      car.add(w.DTH.glowSprite(0xfbbf24, 5, .7));
      agvs.add(car);
      agvList.push({ m: car, t: a / 3 });
    }
    root.add(agvs);

    /* ---------- 交互 ---------- */
    var orbit = w.DTH.Orbit(camera, canvas, { target: new THREE.Vector3(0, 14, 0), radius: 240, phi: 1.02, theta: 1.35, auto: true, speed: .04, minDistance: 50, maxDistance: 480 });
    var pk = w.DTH.picker(renderer, camera, canvas);
    pk.setTargets(tanksRoot.children);
    canvas.addEventListener('mousemove', pk.onMove);
    canvas.addEventListener('click', function () {
      var hit = pk.pick();
      if (hit) ctx.toast('设备：' + hit.obj.userData.data.name);
    });
    bus.on('cmd', function (c) { if (c === 'reset') orbit.reset(); });
    bus.on('orbit', function (on) { orbit.auto = on; });
    bus.on('layer', function (p) { ctrl.setLayer(p.id, p.on); });
    bus.on('focus', function (p) { ctrl.focus(String(p.id || '')); });

    function resize() {
      var r = canvas.getBoundingClientRect();
      if (!r.width || !r.height) return;
      renderer.setSize(r.width, r.height, false);
      camera.aspect = r.width / r.height; camera.updateProjectionMatrix();
    }
    resize();
    if (w.ResizeObserver) new w.ResizeObserver(resize).observe(canvas);
    w.addEventListener('resize', resize);

    var clock = new THREE.Clock();
    function loop() {
      var dt = Math.min(clock.getDelta(), .05), t = clock.elapsedTime;
      orbit.update(dt);
      products.forEach(function (o) {
        o.m.position.x += o.spd * dt;
        o.m.rotation.y += dt * .8;
        if (o.m.position.x > o.max) o.m.position.x = o.min;
      });
      Object.keys(lines).forEach(function (k) {
        var belt = lines[k];
        if (belt.material.map) { belt.material.map.offset.x -= dt * .35; }
      });
      pipeFlows.forEach(function (f) { f.update(dt); });
      agvList.forEach(function (o) {
        o.t += dt * .045; if (o.t > 1) o.t -= 1;
        var p = agvPath.getPointAt(o.t), p2 = agvPath.getPointAt((o.t + .004) % 1);
        o.m.position.copy(p); o.m.lookAt(p2);
      });
      tanksRoot.traverse(function (o) {
        if (o.userData.lamp) o.material.opacity = .5 + Math.abs(Math.sin(t * 2)) * .5;
      });
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    }
    var raf = requestAnimationFrame(loop);

    var ctrl = {
      stats: function () { return { fps: 60, faces: renderer.info.render.triangles }; },
      setLayer: function (id, on) { root.traverse(function (o) { if (o.userData && o.userData.layer === id) o.visible = on; }); },
      focus: function (id) {
        var g = tankMap[id] || tankMap['t3'];
        if (!g) return;
        orbit.flyTo(new THREE.Vector3(g.position.x, 14, g.position.z), 78, 1.0, 0.9);
        orbit.auto = false;
      },
      dispose: function () { cancelAnimationFrame(raf); renderer.dispose(); }
    };
    return ctrl;
  }

  w.__DT_SCENE__ = {
    id: 'factory', name: '智慧工厂 / 产线',
    camera: { pos: [96, 74, 118], target: [0, 14, 0] },
    init: init,
    iso: function () {
      return LINES.map(function (L) {
        return { type: 'belt', id: L.id, name: L.name, color: L.color, x: 0, z: L.z / 2, w: L.len / 2, d: 5, h: 6 };
      }).concat(TANKS.map(function (T) {
        return { type: 'tank', id: T.id, name: T.name, color: STATUS_COLOR[T.status], x: T.x / 2, z: T.z / 2, w: T.r, d: T.r, h: T.h / 2 };
      }));
    }
  };
})(window);
