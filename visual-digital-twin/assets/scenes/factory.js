/* ============================================================
   Scene: factory (realistic) — 智慧工厂 / 产线 · 写实版
   压型钢板厂房 + 玻璃办公楼 + 罐区(t1-t5) + 管网 + 传送产线 + AGV
   图层（对齐 templates/config/factory.json）：shell/lines/tanks/pipes/agv/labels
   实体：t1 配料反应釜A / t2 配料反应釜B / t3 恒温储罐 / t4 成品缓存罐 / t5 回收处理罐
   ============================================================ */
window.__DT_SCENE_SPEC__ = {
  id: 'factory', name: '智慧工厂 / 产线（写实）',
  camera: { pos: [95, 72, 115], target: [0, 8, 0] },
  textures: ['wallsteel', 'concrete', 'ground', 'tank', 'asphalt', 'crate'],

  iso: function () {
    return [
      { type: 'block', id: 'shell', name: '联合主厂房', color: 0x3b82f6, x: -18, z: -6, w: 60, d: 34, h: 18 },
      { type: 'block', id: 'office', name: '综合办公楼', color: 0x22d3ee, x: 24, z: -28, w: 18, d: 12, h: 14 },
      { type: 'block', id: 't3', name: '恒温储罐', color: 0xfb7185, x: 26, z: 14, w: 10, d: 10, h: 14 },
      { type: 'block', id: 't1', name: '配料反应釜 A', color: 0x2dd4bf, x: 38, z: 14, w: 8, d: 8, h: 12 },
      { type: 'block', id: 'lines', name: '成品产线', color: 0xa855f7, x: -14, z: 26, w: 46, d: 10, h: 5 }
    ];
  },

  init: async function (E, ctx) {
    const THREE = E.THREE, bus = ctx.bus;
    const root = E.root;

    /* ---------- 地面：混凝土厂区 + 沥青环路 ---------- */
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(420, 420), E.texMat('ground', { repeatX: 7, repeatY: 7, roughness: .95, color: 0x8f9a8c }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.05;
    ground.receiveShadow = true;
    root.add(ground);
    const yard = new THREE.Mesh(new THREE.PlaneGeometry(190, 150), E.texMat('concrete', { repeatX: 16, repeatY: 13, roughness: .8, color: 0xb9bdc2 }));
    yard.rotation.x = -Math.PI / 2; yard.position.y = 0.03;
    yard.receiveShadow = true;
    root.add(yard);
    const loop = new THREE.Mesh(new THREE.RingGeometry(96, 106, 64), E.texMat('asphalt', { repeatX: 20, repeatY: 2, roughness: .9 }));
    loop.rotation.x = -Math.PI / 2; loop.position.y = 0.05;
    root.add(loop);
    // RingGeometry 的 UV 是平面投影，直接用 asphalt 会拉伸——包一层细密的 repeat 修正
    if (loop.material.map) { loop.material.map = loop.material.map.clone(); loop.material.map.repeat.set(24, 2); loop.material.map.needsUpdate = true; }

    let seed = 4477;
    function rnd() { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }

    /* ---------- 联合主厂房（shell） ---------- */
    const shell = new THREE.Group(); shell.userData.layer = 'shell';
    const wallMat = E.texMat('wallsteel', { repeatX: 8, repeatY: 2, roughness: .55, metalness: .35, color: 0xb9c4cc });
    const hall = new THREE.Mesh(E.rbox(60, 16, 32, .3), wallMat);
    hall.position.set(-18, 8, -6);
    hall.castShadow = hall.receiveShadow = true;
    shell.add(hall);
    // 屋脊 + 天窗带
    const roof = new THREE.Mesh(new THREE.CylinderGeometry(16.2, 16.2, 60.5, 3, 1, false, 0, Math.PI), wallMat);
    roof.rotation.z = Math.PI / 2; roof.rotation.y = Math.PI / 2;
    roof.position.set(-18, 16, -6);
    roof.scale.set(1, 1, .22);
    roof.castShadow = true;
    shell.add(roof);
    const skylight = new THREE.Mesh(new THREE.BoxGeometry(44, .3, 3), E.mat({ color: 0xcfe4f5, roughness: .2, metalness: .6, emissive: 0xbfe0f5, emissiveIntensity: .12 }));
    skylight.position.set(-18, 19.4, -6);
    shell.add(skylight);
    // 大门（深色内嵌）
    const gate = new THREE.Mesh(new THREE.BoxGeometry(14, 9, .5), E.mat({ color: 0x3d454f, roughness: .7, metalness: .3 }));
    gate.position.set(-6, 4.5, 10.3);
    shell.add(gate);
    root.add(shell);

    /* ---------- 综合办公楼（玻璃） ---------- */
    const office = new THREE.Group(); office.userData.layer = 'shell';
    function windowTexture() {
      const cv = document.createElement('canvas'); cv.width = 64; cv.height = 64;
      const c2 = cv.getContext('2d');
      c2.fillStyle = '#2a3644'; c2.fillRect(0, 0, 64, 64);
      for (let y = 4; y < 60; y += 9) for (let x = 3; x < 60; x += 8) {
        c2.fillStyle = Math.random() > .3 ? 'rgba(140,196,235,.55)' : 'rgba(18,26,36,.95)';
        c2.fillRect(x, y, 5.4, 5.6);
      }
      const t = new THREE.CanvasTexture(cv);
      t.colorSpace = THREE.SRGBColorSpace;
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      return t;
    }
    const ofWin = windowTexture();
    const officeMat = E.mat({ color: 0xffffff, roughness: .2, metalness: .5 });
    officeMat.map = ofWin; officeMat.emissiveMap = ofWin;
    officeMat.emissive = new THREE.Color(0xffe9b8);
    officeMat.emissiveIntensity = .05;
    E.onTOD(function (t) { officeMat.emissiveIntensity = t === 'dusk' ? 1.0 : .05; });
    const officeBox = new THREE.Mesh(E.rbox(18, 14, 12, .25), officeMat);
    officeBox.position.set(24, 7, -28);
    officeBox.castShadow = officeBox.receiveShadow = true;
    office.add(officeBox);
    root.add(office);

    /* ---------- 罐区（t1-t5，实体聚焦目标） ---------- */
    const tanks = new THREE.Group(); tanks.userData.layer = 'tanks';
    const TANKS = [
      { id: 't1', name: '配料反应釜 A', pos: [38, 14], r: 3.4, h: 11, color: 0x2dd4bf, status: 'normal' },
      { id: 't2', name: '配料反应釜 B', pos: [48, 14], r: 3.4, h: 11, color: 0x2dd4bf, status: 'normal' },
      { id: 't3', name: '恒温储罐',     pos: [26, 14], r: 4.2, h: 14, color: 0xfb7185, status: 'alarm' },
      { id: 't4', name: '成品缓存罐',   pos: [58, 14], r: 3.0, h: 9,  color: 0x3b82f6, status: 'normal' },
      { id: 't5', name: '回收处理罐',   pos: [68, 14], r: 3.0, h: 9,  color: 0xfbbf24, status: 'warn' }
    ];
    const tankPick = [];
    const statusBeacons = {};
    TANKS.forEach(function (t) {
      const g = new THREE.Group();
      const body = new THREE.Mesh(new THREE.CylinderGeometry(t.r, t.r, t.h, 24), E.texMat('tank', { repeatX: 4, repeatY: 2, roughness: .5, metalness: .3 }));
      body.position.set(t.pos[0], t.h / 2, t.pos[1]);
      body.castShadow = body.receiveShadow = true;
      const top = new THREE.Mesh(new THREE.SphereGeometry(t.r, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), E.texMat('tank', { repeatX: 4, repeatY: 1, roughness: .5, metalness: .3 }));
      top.position.set(t.pos[0], t.h, t.pos[1]);
      top.castShadow = true;
      const base = new THREE.Mesh(new THREE.CylinderGeometry(t.r + .5, t.r + .7, .8, 24), E.mat({ color: 0x6b7280, roughness: .8 }));
      base.position.set(t.pos[0], .4, t.pos[1]);
      base.receiveShadow = true;
      // 直爬梯
      const ladder = new THREE.Mesh(new THREE.BoxGeometry(.5, t.h, .18), E.mat({ color: 0x2a3138, roughness: .6, metalness: .5 }));
      ladder.position.set(t.pos[0] + t.r + .2, t.h / 2, t.pos[1]);
      g.add(body, top, base, ladder);
      // 状态光柱（alarm 红 / warn 琥珀 / normal 微绿）
      const bcColor = t.status === 'alarm' ? 0xfb7185 : t.status === 'warn' ? 0xfbbf24 : 0x34d399;
      const bc = E.beaconPillar(t.r * .55, t.h + 10, bcColor);
      bc.position.set(t.pos[0], (t.h + 10) / 2, t.pos[1]);
      bc.material.opacity = t.status === 'normal' ? .28 : .8;
      g.add(bc);
      statusBeacons[t.id] = bc;
      g.userData.focusId = t.id;
      g.userData.data = { name: t.name, desc: t.status === 'alarm' ? '液位超限，需立即处置' : '运行中', metrics: [['罐体高度', t.h, 'm'], ['直径', t.r * 2, 'm']] };
      tanks.add(g);
      tankPick.push(body);
    });
    root.add(tanks);

    /* ---------- 管网（pipes）：罐区 → 厂房 ---------- */
    const pipes = new THREE.Group(); pipes.userData.layer = 'pipes';
    const pipeMat = E.mat({ color: 0x9aa3ad, roughness: .35, metalness: .7 });
    function pipe(x1, y1, z1, x2, y2, z2, r) {
      const v1 = new THREE.Vector3(x1, y1, z1), v2 = new THREE.Vector3(x2, y2, z2);
      const len = v1.distanceTo(v2);
      const seg = new THREE.Mesh(new THREE.CylinderGeometry(r || .28, r || .28, len, 10), pipeMat);
      seg.position.copy(v1).add(v2).multiplyScalar(.5);
      seg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v2.clone().sub(v1).normalize());
      seg.castShadow = true;
      pipes.add(seg);
    }
    const rackY = 3.2;
    // 管廊：沿 z=14 一条主管 + 各罐支管 + 进厂房
    pipe(26, rackY, 20.5, 68, rackY, 20.5, .34);
    TANKS.forEach(function (t) { pipe(t.pos[0], rackY, t.pos[1] + t.r, t.pos[0], rackY, 20.5, .2); });
    pipe(26, rackY, 20.5, 26, rackY, 12, .34);
    pipe(26, rackY, 12, -18, rackY, 12, .34);
    pipe(-18, rackY, 12, -18, 9, 12, .34);   // 进厂房
    pipe(24, 5, -22, 24, 5, 14, .3);          // 办公楼 - 罐区 供热管
    pipe(24, 5, 14, 38, 5, 14, .22);
    root.add(pipes);

    /* ---------- 成品产线（lines）：传送带 + 设备柜 ---------- */
    const lines = new THREE.Group(); lines.userData.layer = 'lines';
    const belt = new THREE.Mesh(E.rbox(46, 1.1, 2.4, .12), E.mat({ color: 0x23272e, roughness: .8 }));
    belt.position.set(-14, .9, 26);
    belt.castShadow = belt.receiveShadow = true;
    lines.add(belt);
    const beltMat2 = E.mat({ color: 0x444b54, roughness: .55, metalness: .4 });
    for (let x = -34; x <= 6; x += 4) {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(.4, .8, 2), beltMat2);
      leg.position.set(x, .4, 26);
      lines.add(leg);
    }
    // 线上货箱
    for (let i = 0; i < 7; i++) {
      const crate = new THREE.Mesh(E.rbox(1.8, 1.6, 1.8, .1), E.texMat('crate', { repeatX: 1, repeatY: 1, roughness: .8 }));
      crate.position.set(-32 + i * 6.2, 2.7, 26);
      crate.castShadow = true;
      lines.add(crate);
    }
    // 设备柜列
    for (let i = 0; i < 4; i++) {
      const cab = new THREE.Mesh(E.rbox(3.2, 4.6, 2.2, .15), E.mat({ color: 0x5f6a76, roughness: .45, metalness: .5 }));
      cab.position.set(-28 + i * 9, 2.3, 21);
      cab.castShadow = cab.receiveShadow = true;
      lines.add(cab);
    }
    root.add(lines);

    /* ---------- AGV（agv）：厂房 ↔ 罐区 往返 ---------- */
    const agvs = new THREE.Group(); agvs.userData.layer = 'agv';
    const AGV_PATHS = [
      [[-6, 22], [26, 22], [26, 14]],
      [[-12, 24], [48, 24], [48, 14]],
      [[0, 30], [-30, 30], [-30, 12]]
    ];
    for (let i = 0; i < 3; i++) {
      const g = new THREE.Group();
      const base = new THREE.Mesh(E.rbox(2.6, .7, 1.8, .12), E.mat({ color: 0xf2b632, roughness: .4, metalness: .3 }));
      base.position.y = .55; base.castShadow = true;
      const load = new THREE.Mesh(E.rbox(1.7, .8, 1.4, .08), E.texMat('crate', { roughness: .8 }));
      load.position.y = 1.35; load.castShadow = true;
      g.add(base, load);
      g.userData.path = AGV_PATHS[i];
      g.userData.t = i / 3;
      g.userData.speed = .05 + i * .012;
      g.userData.seg = 0;
      agvs.add(g);
    }
    root.add(agvs);
    function driveAgv(dt) {
      agvs.children.forEach(function (g) {
        const u = g.userData, P = u.path;
        u.t += dt * u.speed;
        if (u.t > 1) { u.t -= 1; u.seg = (u.seg + 1) % P.length; }
        const a = P[u.seg], b = P[(u.seg + 1) % P.length];
        const x = a[0] + (b[0] - a[0]) * u.t, z = a[1] + (b[1] - a[1]) * u.t;
        g.position.set(x, 0, z);
        g.rotation.y = Math.atan2(-(b[1] - a[1]), b[0] - a[0]);
      });
    }

    /* ---------- 标签 ---------- */
    const labels = new THREE.Group(); labels.userData.layer = 'labels';
    [
      { t: '联合主厂房', p: [-18, 22, -6] },
      { t: '综合办公楼', p: [24, 18, -28] },
      { t: '罐区', p: [47, 24, 14] },
      { t: '成品产线', p: [-14, 8, 26] }
    ].forEach(function (L) {
      const lb = E.label(L.t, { scale: 1.2 });
      lb.position.set(L.p[0], L.p[1], L.p[2]);
      labels.add(lb);
    });
    root.add(labels);

    /* ---------- 交互 ---------- */
    const orbit = E.orbit(E.camera, E.canvas, {
      target: new THREE.Vector3(0, 8, 0), auto: true, speed: .035,
      minDistance: 40, maxDistance: 420
    });
    const pk = E.picker(E.renderer, E.camera, E.canvas);
    pk.setTargets(tankPick);
    E.canvas.addEventListener('mousemove', pk.onMove);
    E.canvas.addEventListener('click', function () {
      const hit = pk.pick();
      if (hit && hit.obj.parent && hit.obj.parent.userData.focusId) {
        bus.emit('focus', { id: hit.obj.parent.userData.focusId });
        ctx.toast('已定位：' + hit.obj.parent.userData.data.name);
      }
    });
    bus.on('cmd', function (cmd) { if (cmd === 'reset') orbit.reset(); });
    bus.on('orbit', function (on) { orbit.setAuto(on); });
    bus.on('layer', function (p) { setLayer(p.id, p.on); });
    bus.on('focus', function (p) { focus(String(p.id || '')); });

    function setLayer(id, on) {
      root.traverse(function (o) { if (o.userData && o.userData.layer === id) o.visible = on; });
    }
    function focus(id) {
      const t = TANKS.find(function (x) { return x.id === id; });
      if (t) {
        orbit.flyTo(new THREE.Vector3(t.pos[0], 6, t.pos[1]), 46, 1.05);
        Object.keys(statusBeacons).forEach(function (k) {
          statusBeacons[k].material.opacity = k === id ? 1 : (TANKS.find(function (x) { return x.id === k; }).status === 'normal' ? .28 : .8);
        });
        return;
      }
      const spots = {
        shell: { v: [-18, 8, -6], r: 95 }, office: { v: [24, 7, -28], r: 55 }, lines: { v: [-14, 3, 26], r: 60 }
      };
      const s = spots[id];
      if (s) orbit.flyTo(new THREE.Vector3(s.v[0], s.v[1], s.v[2]), s.r, 1.05);
    }

    return {
      orbitRef: orbit,
      update: function (dt, t) {
        driveAgv(dt);
        tanks.children.forEach(function (g) {
          g.children.forEach(function (c) { if (c.update) c.update(dt, t); });
        });
      },
      setLayer: setLayer,
      focus: focus,
      dispose: function () {}
    };
  }
};
