/* ============================================================
   Scene: port — 港口物流 / 交通枢纽数字孪生
   Shader 海面 + 集装箱堆场 + 岸桥联动 + 航线飞线 + 集卡流转
   ============================================================ */
(function (w) {
  'use strict';

  var CRANES = [
    { id: 'cr1', name: '岸桥 1# 泊位A', x: -34, z: -20, color: 0x22d3ee },
    { id: 'cr2', name: '岸桥 2# 泊位A', x: -12, z: -20, color: 0x22d3ee },
    { id: 'cr3', name: '岸桥 3# 泊位B', x: 12, z: -20, color: 0x3b82f6 },
    { id: 'cr4', name: '岸桥 4# 泊位B', x: 34, z: -20, color: 0x3b82f6 }
  ];
  var CTN_COLORS = [0x22d3ee, 0x3b82f6, 0x2dd4bf, 0xfbbf24, 0xfb7185, 0xa855f7, 0xe6f4ff];

  function init(ctx) {
    var THREE = ctx.THREE, canvas = ctx.canvas, bus = ctx.bus;
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(w.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    if (THREE.sRGBEncoding) renderer.outputEncoding = THREE.sRGBEncoding;

    var scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x04101f, .0018);
    var camera = new THREE.PerspectiveCamera(46, 1, .5, 4000);
    camera.position.set(140, 96, 168);

    scene.add(new THREE.AmbientLight(0x4f7fb8, 1.0));
    var sun = new THREE.DirectionalLight(0xbfe4ff, .75); sun.position.set(80, 140, 100); scene.add(sun);
    var pl = new THREE.PointLight(0x22d3ee, 1.3, 320); pl.position.set(-60, 50, -40); scene.add(pl);
    var p2 = new THREE.PointLight(0xa855f7, 1.0, 320); p2.position.set(70, 44, 60); scene.add(p2);

    var root = new THREE.Group(); scene.add(root);

    /* ---------- 海面（自定义 Shader 波浪） ---------- */
    var seaUniforms = { uTime: { value: 0 }, uDeep: { value: new THREE.Color(0x03101f) }, uShallow: { value: new THREE.Color(0x0a5b86) } };
    var sea = new THREE.Mesh(
      new THREE.PlaneGeometry(900, 620, 90, 62),
      new THREE.ShaderMaterial({
        uniforms: seaUniforms,
        transparent: true,
        vertexShader: [
          'uniform float uTime;',
          'varying vec2 vUv;',
          'varying float vH;',
          'float wave(vec2 p){',
          '  return sin(p.x*0.08 + uTime*0.9)*1.6 + sin(p.y*0.11 - uTime*0.7)*1.4 + sin((p.x+p.y)*0.05 + uTime*0.45)*1.1;',
          '}',
          'void main(){',
          '  vUv = uv;',
          '  vec3 pos = position;',
          '  float h = wave(pos.xy);',
          '  pos.z += h;',
          '  vH = h;',
          '  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos,1.0);',
          '}'
        ].join('\n'),
        fragmentShader: [
          'uniform vec3 uDeep;',
          'uniform vec3 uShallow;',
          'varying vec2 vUv;',
          'varying float vH;',
          'void main(){',
          '  float m = smoothstep(-2.0,2.6,vH);',
          '  vec3 col = mix(uDeep, uShallow, m);',
          '  float foam = smoothstep(1.9,2.6,vH)*0.55;',
          '  col += vec3(0.35,0.85,1.0)*foam;',
          '  float d = distance(vUv, vec2(0.5));',
          '  float a = smoothstep(0.52,0.16,d);',
          '  gl_FragColor = vec4(col, a*0.95);',
          '}'
        ].join('\n')
      })
    );
    sea.rotation.x = -Math.PI / 2; sea.position.y = -.6;
    sea.userData.layer = 'sea';
    root.add(sea);

    /* ---------- 码头平台 ---------- */
    var quay = new THREE.Group(); quay.userData.layer = 'quay';
    var dock = new THREE.Mesh(new THREE.BoxGeometry(210, 8, 74),
      new THREE.MeshPhongMaterial({ color: 0x0f2c4a, shininess: 20 }));
    dock.position.set(0, 3.4, 18); quay.add(dock);
    var gridHelper = w.DTH.ground(220, 22, 0x22d3ee);
    gridHelper.position.set(0, 7.7, 18); quay.add(gridHelper);
    root.add(quay);

    /* ---------- 集装箱堆场（InstancedMesh） ---------- */
    var yard = new THREE.Group(); yard.userData.layer = 'yard';
    var bays = [
      { id: 'y1', name: 'A 区重箱堆场', x: -66, z: 52, w: 76, d: 34, rows: 5, cols: 9, layers: 3 },
      { id: 'y2', name: 'B 区空箱堆场', x: 66, z: 52, w: 76, d: 30, rows: 5, cols: 9, layers: 2 },
      { id: 'y3', name: 'C 区中转堆场', x: 0, z: 46, w: 60, d: 24, rows: 4, cols: 7, layers: 2 }
    ];
    var yardTargets = [];
    bays.forEach(function (B, bi) {
      var rnd = w.DTH.rng(bi * 131 + 7);
      var total = B.rows * B.cols * B.layers;
      var geo = new THREE.BoxGeometry(1, 1, 1);
      var mat = new THREE.MeshPhongMaterial({ shininess: 30 });
      var im = new THREE.InstancedMesh(geo, mat, total);
      var mtx = new THREE.Matrix4(), p = new THREE.Vector3(), s = new THREE.Vector3(), q = new THREE.Quaternion();
      var cw = B.w / B.cols * .82, cd = B.d / B.rows * .74, ch = 5.2;
      var i = 0;
      for (var L = 0; L < B.layers; L++) {
        for (var R = 0; R < B.rows; R++) {
          for (var C = 0; C < B.cols; C++) {
            if (L > 0 && rnd() < .3 + L * .18) continue;
            var x = B.x + (C - (B.cols - 1) / 2) * (B.w / B.cols);
            var z = B.z + (R - (B.rows - 1) / 2) * (B.d / B.rows);
            p.set(x, 8 + ch * L + ch / 2, z); s.set(cw, ch * .92, cd);
            mtx.compose(p, q, s); im.setMatrixAt(i, mtx);
            im.setColorAt(i, new THREE.Color(CTN_COLORS[Math.floor(rnd() * CTN_COLORS.length)]));
            i++;
          }
        }
      }
      im.count = i;
      im.instanceMatrix.needsUpdate = true;
      if (im.instanceColor) im.instanceColor.needsUpdate = true;
      im.userData.data = { name: B.name, desc: '箱位 ' + B.rows * B.cols + ' · 层数 ' + B.layers, metrics: [['堆存', Math.round(i * 1.6) + '', 'TEU']] };
      yard.add(im);
      yardTargets.push(im);
      var lb = w.DTH.label(B.name, { fontSize: 20, scale: 1, accent: '#7dd3fc' });
      lb.position.set(B.x, 26, B.z + B.d / 2); lb.userData.layer = 'labels'; yard.add(lb);
    });
    root.add(yard);

    /* ---------- 岸桥（联动动画） ---------- */
    var cranes = new THREE.Group(); cranes.userData.layer = 'crane';
    var craneMap = {};
    CRANES.forEach(function (C, idx) {
      var g = new THREE.Group();
      var steel = new THREE.MeshPhongMaterial({ color: 0x16395d, shininess: 40 });
      // 门架
      [-14, 14].forEach(function (dx) {
        [-8, 8].forEach(function (dz) {
          var leg = new THREE.Mesh(new THREE.BoxGeometry(1.8, 40, 1.8), steel);
          leg.position.set(dx, 20 + 8, dz); g.add(leg);
        });
      });
      // 横梁
      var beam = new THREE.Mesh(new THREE.BoxGeometry(74, 1.6, 3),
        new THREE.MeshPhongMaterial({ color: 0x1d4a78, emissive: C.color, emissiveIntensity: .25, shininess: 50 }));
      beam.position.set(0, 48.5, 0); g.add(beam);
      // 前伸吊臂
      var boom = new THREE.Mesh(new THREE.BoxGeometry(46, 1.4, 2.2), steel);
      boom.position.set(-32, 48.5, 0); g.add(boom);
      // 驾驶/小车
      var trolley = new THREE.Group();
      var tBody = new THREE.Mesh(new THREE.BoxGeometry(6, 3.4, 5),
        new THREE.MeshPhongMaterial({ color: 0x9be8ff, emissive: C.color, emissiveIntensity: .6, shininess: 70 }));
      trolley.add(tBody);
      var cable = new THREE.Mesh(new THREE.CylinderGeometry(.18, .18, 26, 6),
        new THREE.MeshBasicMaterial({ color: 0x7dd3fc, transparent: true, opacity: .55 }));
      cable.position.y = -14; trolley.add(cable);
      var spreader = new THREE.Mesh(new THREE.BoxGeometry(13, 1.6, 5),
        new THREE.MeshPhongMaterial({ color: 0xfbbf24, emissive: 0xfbbf24, emissiveIntensity: .45 }));
      spreader.position.y = -27; trolley.add(spreader);
      trolley.position.set(0, 46.5, 0);
      trolley.add(w.DTH.glowSprite(C.color, 9, .5));
      g.add(trolley);
      var lb = w.DTH.label(C.name, { fontSize: 19, scale: .9, accent: '#' + new THREE.Color(C.color).getHexString() });
      lb.position.set(0, 58, 0); lb.userData.layer = 'labels'; g.add(lb);

      g.position.set(C.x, 0, C.z);
      root.add(g);
      cranes.add(g);
      craneMap[C.id] = { g: g, trolley: trolley, phase: idx * 1.6, spreader: spreader, color: C.color };
    });
    root.add(cranes);

    /* ---------- 航线飞线 + 船舶 ---------- */
    var routes = new THREE.Group(); routes.userData.layer = 'route';
    var seaFlows = [];
    [[-150, -180, 0x7dd3fc], [0, -230, 0xa855f7], [150, -170, 0x22d3ee]].forEach(function (r) {
      var cv = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(r[0], 4, r[1]),
        new THREE.Vector3(r[0] * .3, 40, -240),
        new THREE.Vector3(0, 6, -60)
      );
      routes.add(w.DTH.neonLine(cv.getPoints(50), r[2], { opacity: .28 }));
      var f = w.DTH.flow(cv, { count: 3, size: 5, color: r[2], speed: .18 });
      routes.add(f); seaFlows.push(f);
    });
    root.add(routes);

    var ships = new THREE.Group(); ships.userData.layer = 'ship';
    var shipList = [];
    for (var sIdx = 0; sIdx < 3; sIdx++) {
      var ship = new THREE.Group();
      var hull = new THREE.Mesh(new THREE.SphereGeometry(16, 24, 14),
        new THREE.MeshPhongMaterial({ color: sIdx === 1 ? 0x254a6e : 0x16375c, shininess: 50 }));
      hull.scale.set(3.1, .62, 1.15); ship.add(hull);
      var deck = new THREE.Mesh(new THREE.BoxGeometry(26, 6, 14),
        new THREE.MeshPhongMaterial({ color: 0x1d4a78, shininess: 40 }));
      deck.position.set(-14, 6, 0); ship.add(deck);
      var bridge = new THREE.Mesh(new THREE.BoxGeometry(9, 8, 10),
        new THREE.MeshPhongMaterial({ color: 0x9be8ff, emissive: 0x22d3ee, emissiveIntensity: .35 }));
      bridge.position.set(-20, 12, 0); ship.add(bridge);
      ship.add(w.DTH.glowSprite(0x22d3ee, 26, .45));
      ships.add(ship);
      shipList.push({ m: ship, z: -120 - sIdx * 70, dir: sIdx % 2 ? 1 : -1, spd: 6 + sIdx * 2 });
    }
    root.add(ships);

    /* ---------- 集卡流转 ---------- */
    var trucks = new THREE.Group(); trucks.userData.layer = 'truck';
    var truckPath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-72, 8.6, 12), new THREE.Vector3(-72, 8.6, 40), new THREE.Vector3(-20, 8.6, 44),
      new THREE.Vector3(20, 8.6, 40), new THREE.Vector3(66, 8.6, 20), new THREE.Vector3(66, 8.6, 8),
      new THREE.Vector3(20, 8.6, 6), new THREE.Vector3(-30, 8.6, 6)
    ], true);
    trucks.add(w.DTH.neonLine(truckPath.getPoints(90), 0xfbbf24, { opacity: .28 }));
    var truckList = [];
    for (var tI = 0; tI < 5; tI++) {
      var tg = new THREE.Group();
      var cab = new THREE.Mesh(new THREE.BoxGeometry(5, 4, 5),
        new THREE.MeshPhongMaterial({ color: 0x1d3f66, emissive: 0xfbbf24, emissiveIntensity: .3, shininess: 60 }));
      tg.add(cab);
      var load = new THREE.Mesh(new THREE.BoxGeometry(9, 5, 5),
        new THREE.MeshPhongMaterial({ color: CTN_COLORS[tI % CTN_COLORS.length], shininess: 40 }));
      load.position.x = -7; tg.add(load);
      tg.add(w.DTH.glowSprite(0xfbbf24, 6, .6));
      trucks.add(tg);
      truckList.push({ m: tg, t: tI / 5 });
    }
    root.add(trucks);

    /* ---------- 交互 ---------- */
    var orbit = w.DTH.Orbit(camera, canvas, { target: new THREE.Vector3(0, 12, 0), radius: 240, phi: .95, theta: 1.15, auto: true, speed: .042, minDistance: 70, maxDistance: 620 });
    var pk = w.DTH.picker(renderer, camera, canvas);
    pk.setTargets(yardTargets);
    canvas.addEventListener('mousemove', pk.onMove);
    canvas.addEventListener('click', function () {
      var hit = pk.pick();
      if (hit) ctx.toast(hit.obj.userData.data.name + '：' + hit.obj.userData.data.metrics[0].join(' '));
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
      seaUniforms.uTime.value = t;
      seaFlows.forEach(function (f) { f.update(dt); });
      Object.keys(craneMap).forEach(function (k) {
        var C = craneMap[k];
        var ph = (t * .35 + C.phase) % 6.2832;
        var tx = Math.sin(ph) * 26 - 8;
        C.trolley.position.x = tx;
        C.spreader.position.y = -27 + Math.max(0, Math.sin(ph * 1.3)) * 15;
      });
      shipList.forEach(function (o) {
        o.z += o.dir * o.spd * dt;
        if (o.z > -80) o.dir = -1; if (o.z < -320) o.dir = 1;
        o.m.position.set(o.dir > 0 ? 40 : -40, 2 + Math.sin(t * 1.4) * .5, o.z);
        o.m.rotation.y = o.dir > 0 ? Math.PI : 0;
      });
      truckList.forEach(function (o) {
        o.t += dt * .035; if (o.t > 1) o.t -= 1;
        var pp = truckPath.getPointAt(o.t), pn = truckPath.getPointAt((o.t + .003) % 1);
        o.m.position.copy(pp); o.m.lookAt(pn);
      });
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    }
    var raf = requestAnimationFrame(loop);

    var ctrl = {
      stats: function () { return { fps: 60, faces: renderer.info.render.triangles }; },
      setLayer: function (id, on) { root.traverse(function (o) { if (o.userData && o.userData.layer === id) o.visible = on; }); },
      focus: function (id) {
        var C = craneMap[id];
        if (C) { orbit.flyTo(new THREE.Vector3(C.g.position.x, 16, C.g.position.z), 90, 1.0, 1.2); orbit.auto = false; }
        else { orbit.flyTo(new THREE.Vector3(0, 14, 40), 150, .85, 1.0); orbit.auto = false; }
      },
      dispose: function () { cancelAnimationFrame(raf); renderer.dispose(); }
    };
    return ctrl;
  }

  w.__DT_SCENE__ = {
    id: 'port', name: '港口物流 / 交通枢纽',
    camera: { pos: [140, 96, 168], target: [0, 12, 0] },
    init: init,
    iso: function () {
      return [
        { type: 'yard', id: 'y1', name: 'A 区重箱堆场', color: 0x22d3ee, x: -33, z: 26, w: 38, d: 17, h: 16 },
        { type: 'yard', id: 'y2', name: 'B 区空箱堆场', color: 0x3b82f6, x: 33, z: 26, w: 38, d: 15, h: 10 },
        { type: 'yard', id: 'y3', name: 'C 区中转堆场', color: 0x2dd4bf, x: 0, z: 23, w: 30, d: 12, h: 10 }
      ];
    }
  };
})(window);
