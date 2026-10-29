/* ============================================================
   Scene: city (realistic) — 智慧城市 / 园区楼宇 · 写实版
   物理天空 + PBR（混凝土楼体/玻璃幕墙/沥青路网/草坪）+ 行驶车流
   + 分区标签/光柱 + 跨区数据流（克制）
   接口契约（engine.js）：window.__DT_SCENE_SPEC__ = {id,name,camera,textures,iso,init}
   图层（对齐 templates/config/city.json）：buildings/roads/fly/labels/beacon
   实体：cbd/tech/resi/indust/trans（面板点击聚焦）
   ============================================================ */
/* ---------- 分区定义（与 classic 版一致；iso/init 共用） ---------- */
const DISTRICTS = [
  { id: 'cbd',    name: '中央商务区', color: 0x3b82f6, ring: 30, inner: 8,  hMin: 26, hMax: 88, count: 60, pos: [0, 0, 0] },
  { id: 'tech',   name: '科创园区',   color: 0x22d3ee, ring: 26, inner: 6,  hMin: 14, hMax: 46, count: 50, pos: [-92, 0, -58] },
  { id: 'resi',   name: '居住社区',   color: 0x2dd4bf, ring: 24, inner: 7,  hMin: 10, hMax: 34, count: 62, pos: [96, 0, -46] },
  { id: 'indust', name: '智造片区',   color: 0xa855f7, ring: 22, inner: 6,  hMin: 8,  hMax: 24, count: 44, pos: [78, 0, 84] },
  { id: 'trans',  name: '交通枢纽',   color: 0xfbbf24, ring: 20, inner: 5,  hMin: 6,  hMax: 20, count: 34, pos: [-84, 0, 80] }
];

window.__DT_SCENE_SPEC__ = {
  id: 'city', name: '智慧城市 / 园区楼宇（写实）',
  camera: { pos: [190, 150, 230], target: [0, 10, 0] },
  textures: ['concrete', 'asphalt', 'ground', 'lawn', 'glass'],

  iso: function () {
    return DISTRICTS.map(function (dd) {
      return { type: 'block', id: dd.id, name: dd.name, color: dd.color, x: dd.pos[0] / 2.4, z: dd.pos[2] / 2.4, w: dd.ring, d: dd.ring, h: dd.hMax };
    });
  },

  init: async function (E, ctx) {
    const THREE = E.THREE, bus = ctx.bus;
    const root = E.root;

    /* ---------- 地面（大地 + 草坪补丁） ---------- */
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(900, 900), E.texMat('ground', { repeatX: 9, repeatY: 9, roughness: .95, color: 0x9aa294 }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.05;
    ground.receiveShadow = true;
    root.add(ground);

    const lawnPatches = [];
    DISTRICTS.forEach(function (dd) {
      if (dd.id === 'cbd') return;
      const p = new THREE.Mesh(new THREE.PlaneGeometry(dd.ring * 2.6, dd.ring * 2.6), E.texMat('lawn', { repeatX: 10, repeatY: 10, roughness: 1 }));
      p.rotation.x = -Math.PI / 2; p.position.set(dd.pos[0], 0.02, dd.pos[2]);
      p.receiveShadow = true;
      root.add(p); lawnPatches.push(p);
    });

    /* ---------- 路网（沥青 + 路缘） ---------- */
    const roads = new THREE.Group(); roads.userData.layer = 'roads';
    const ROAD_W = 10;
    const laneLines = [];
    function addRoad(x1, z1, x2, z2) {
      const dx = x2 - x1, dz = z2 - z1;
      const len = Math.sqrt(dx * dx + dz * dz);
      const horizontal = Math.abs(dx) >= Math.abs(dz);
      const road = new THREE.Mesh(
        new THREE.PlaneGeometry(horizontal ? len : ROAD_W, horizontal ? ROAD_W : len),
        E.texMat('asphalt', { repeatX: horizontal ? len / 8 : 1, repeatY: horizontal ? 1 : len / 8, roughness: .9 })
      );
      road.rotation.x = -Math.PI / 2;
      if (!horizontal) road.rotation.z = Math.PI / 2;
      road.position.set((x1 + x2) / 2, 0.06, (z1 + z2) / 2);
      road.receiveShadow = true;
      roads.add(road);
      laneLines.push([x1, z1, x2, z2]);
    }
    // 主干道：十字 + 各分区联络线 + 环路
    addRoad(-180, 0, 180, 0);
    addRoad(0, -180, 0, 180);
    DISTRICTS.forEach(function (dd) {
      if (dd.id === 'cbd') return;
      addRoad(dd.pos[0], dd.pos[2], dd.pos[0] * .2, dd.pos[2] * .2);
    });
    for (let a = 0; a < 4; a++) {
      const x1 = Math.cos(a * Math.PI / 2) * 150, z1 = Math.sin(a * Math.PI / 2) * 150;
      const x2 = Math.cos((a + 1) * Math.PI / 2) * 150, z2 = Math.sin((a + 1) * Math.PI / 2) * 150;
      addRoad(x1, z1, x2, z2);
    }
    root.add(roads);

    /* ---------- 车流（沿主干道行驶） ---------- */
    const cars = new THREE.Group(); cars.userData.layer = 'roads';
    const carColors = [0xd8dde3, 0x2b3a4d, 0x8c1f28, 0x274a78, 0x6b7280, 0xc7cdd6];
    const carGeo = E.rbox(4.4, 1.15, 2.0, .18);
    const cabGeo = E.rbox(2.3, .8, 1.86, .16);
    const wheelGeo = new THREE.CylinderGeometry(.34, .34, .3, 10);
    wheelGeo.rotateZ(Math.PI / 2);
    const wheelMat = E.mat({ color: 0x14171c, roughness: .9 });
    const glassMat = E.mat({ color: 0x18222e, roughness: .15, metalness: .4 });
    const roadPaths = [];
    laneLines.forEach(function (L, i) {
      if (i % 2) return; // 取一半车道，避免过密
      roadPaths.push({ a: [L[0], L[1]], b: [L[2], L[3]], dir: 1, lane: 2.2 });
      roadPaths.push({ a: [L[2], L[3]], b: [L[0], L[1]], dir: -1, lane: -2.2 });
    });
    let seed = 20261019;
    function rnd() { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }
    for (let i = 0; i < 26; i++) {
      const path = roadPaths[Math.floor(rnd() * roadPaths.length)];
      const g = new THREE.Group();
      const body = new THREE.Mesh(carGeo, E.mat({ color: carColors[i % carColors.length], roughness: .35, metalness: .55 }));
      body.position.y = .75; body.castShadow = true;
      const cab = new THREE.Mesh(cabGeo, glassMat);
      cab.position.set(-.3, 1.6, 0); cab.castShadow = true;
      g.add(body, cab);
      [[1.5, .9], [1.5, -.9], [-1.5, .9], [-1.5, -.9]].forEach(function (w) {
        const wheel = new THREE.Mesh(wheelGeo, wheelMat);
        wheel.position.set(w[0], .34, w[1]);
        g.add(wheel);
      });
      g.userData.path = path;
      g.userData.t = rnd();
      g.userData.speed = .028 + rnd() * .02;
      cars.add(g);
    }
    root.add(cars);
    function driveCars(dt) {
      cars.children.forEach(function (g) {
        const p = g.userData.path, u = g.userData;
        u.t += dt * u.speed; if (u.t > 1) u.t -= 1;
        const x = p.a[0] + (p.b[0] - p.a[0]) * u.t;
        const z = p.a[1] + (p.b[1] - p.a[1]) * u.t;
        const dx = p.b[0] - p.a[0], dz = p.b[1] - p.a[1];
        const len = Math.sqrt(dx * dx + dz * dz) || 1;
        // 车道偏移（右侧通行）
        const ox = -dz / len * p.lane, oz = dx / len * p.lane;
        g.position.set(x + ox, 0, z + oz);
        g.rotation.y = Math.atan2(-dz, dx);
      });
    }

    /* ---------- 路灯 ---------- */
    const lamps = new THREE.Group(); lamps.userData.layer = 'roads';
    const poleGeo = new THREE.CylinderGeometry(.12, .16, 7, 6);
    const poleMat = E.mat({ color: 0x3c434c, roughness: .6, metalness: .5 });
    const headMat = E.mat({ color: 0xd8e2ec, roughness: .4, emissive: 0xfff2cf, emissiveIntensity: .04 });
    E.onTOD(function (t) { headMat.emissiveIntensity = t === 'dusk' ? 1.4 : .04; });
    laneLines.forEach(function (L, i) {
      if (i % 3) return;
      for (let s = .18; s < .9; s += .3) {
        const x = L[0] + (L[2] - L[0]) * s, z = L[1] + (L[3] - L[1]) * s;
        const pole = new THREE.Mesh(poleGeo, poleMat);
        pole.position.set(x + 6, 3.5, z + 6); pole.castShadow = true;
        const head = new THREE.Mesh(E.rbox(1.6, .3, .5, .1), headMat);
        head.position.set(x + 5.3, 7, z + 6);
        lamps.add(pole, head);
      }
    });
    root.add(lamps);

    /* ---------- 玻璃幕墙贴图（昼夜两态） ---------- */
    function windowTexture(density) {
      const cv = document.createElement('canvas'); cv.width = 64; cv.height = 128;
      const c2 = cv.getContext('2d');
      c2.fillStyle = '#28323e'; c2.fillRect(0, 0, 64, 128);
      for (let y = 4; y < 124; y += 8) {
        for (let x = 4; x < 60; x += 9) {
          const r = Math.random();
          if (r > (1 - density)) {
            c2.fillStyle = r > .93 ? 'rgba(255,236,190,.95)' : 'rgba(126,190,235,.5)';
            c2.fillRect(x, y, 6, 4.6);
          } else {
            c2.fillStyle = 'rgba(16,24,34,.9)';
            c2.fillRect(x, y, 6, 4.6);
          }
        }
      }
      const t = new THREE.CanvasTexture(cv);
      t.colorSpace = THREE.SRGBColorSpace;
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      return t;
    }
    const winDay = windowTexture(.06);
    const winMat = E.mat({ color: 0xffffff, roughness: .18, metalness: .55 });
    winMat.map = winDay;
    winMat.emissiveMap = winDay;
    winMat.emissive = new THREE.Color(0xffe9b8);
    winMat.emissiveIntensity = .05;
    E.onTOD(function (t) { winMat.emissiveIntensity = t === 'dusk' ? 1.1 : .05; });

    /* ---------- 分区楼宇（混凝土 + 玻璃 InstancedMesh，圆角；分区色相微差破除惨白） ---------- */
    const TINTS = [0xd8d3c8, 0xc9ced6, 0xd2cdc2, 0xc4bfb6, 0xcbd2d8];
    const groups = {}, pickTargets = [];
    const bGeo = E.rbox(1, 1, 1, .04, 1);
    const mtx = new THREE.Matrix4(), pos = new THREE.Vector3(), scl = new THREE.Vector3(), q = new THREE.Quaternion();
    let seedB = 7919;
    function rndB() { seedB = (seedB * 1664525 + 1013904223) % 4294967296; return seedB / 4294967296; }

    DISTRICTS.forEach(function (dd, di) {
      const concreteMat = E.texMat('concrete', { repeatX: 2, repeatY: 5, roughness: .85, color: TINTS[di % TINTS.length] });
      const nGlass = Math.floor(dd.count * (dd.id === 'cbd' ? .55 : .22));
      const nConcrete = dd.count - nGlass;
      const imC = new THREE.InstancedMesh(bGeo, concreteMat, nConcrete);
      const imG = new THREE.InstancedMesh(bGeo, winMat, nGlass);
      let ci = 0, gi = 0;
      for (let i = 0; i < dd.count; i++) {
        const ang = rndB() * Math.PI * 2;
        const rad = dd.inner + Math.sqrt(rndB()) * dd.ring;
        const bw = 5 + rndB() * 7, bd = 5 + rndB() * 7;
        const bh = dd.hMin + Math.pow(rndB(), 1.7) * (dd.hMax - dd.hMin);
        const x = dd.pos[0] + Math.cos(ang) * rad, z = dd.pos[2] + Math.sin(ang) * rad;
        pos.set(x, bh / 2, z); scl.set(bw, bh, bd);
        mtx.compose(pos, q, scl);
        if (i < nConcrete) { imC.setMatrixAt(ci++, mtx); } else { imG.setMatrixAt(gi++, mtx); }
      }
      [imC, imG].forEach(function (im) {
        im.count = im === imC ? ci : gi;
        im.instanceMatrix.needsUpdate = true;
        im.castShadow = im.receiveShadow = true;
      });
      imG.userData.data = imC.userData.data = { name: dd.name, desc: dd.count + ' 栋建筑接入', metrics: [['在线设备', (dd.count * 3.2).toFixed(0), '台']] };
      imG.userData.layer = imC.userData.layer = 'buildings';
      const g = new THREE.Group(); g.add(imC, imG);
      g.userData.dd = dd;
      root.add(g);
      pickTargets.push(imC, imG);
      groups[dd.id] = { group: g, dd: dd };
    });
    const buildings = new THREE.Group();
    DISTRICTS.forEach(function (dd) { buildings.add(groups[dd.id].group); });
    buildings.userData.layer = 'buildings';
    root.add(buildings);

    /* ---------- 树木（树干 + 树冠，实例化，散布草坪与路侧） ---------- */
    const trees = new THREE.Group(); trees.userData.layer = 'buildings';
    const trunkGeo = new THREE.CylinderGeometry(.22, .34, 2.6, 6);
    const crownGeo = new THREE.IcosahedronGeometry(1.7, 1);
    const trunkMat = E.mat({ color: 0x5a4632, roughness: .95 });
    const crownMat = E.mat({ color: 0x3d6b33, roughness: .95, flatShading: true });
    const NT = 140;
    const trunks = new THREE.InstancedMesh(trunkGeo, trunkMat, NT);
    const crowns = new THREE.InstancedMesh(crownGeo, crownMat, NT);
    let ti = 0;
    lawnPatches.forEach(function (p) {
      for (let k = 0; k < NT / lawnPatches.length; k++) {
        const x = p.position.x + (rndB() - .5) * p.geometry.parameters.width * .8;
        const z = p.position.z + (rndB() - .5) * p.geometry.parameters.height * .8;
        const s = .7 + rndB() * .9;
        pos.set(x, 1.3 * s, z); scl.set(1, s, 1); mtx.compose(pos, q, scl);
        trunks.setMatrixAt(ti, mtx);
        pos.set(x, (2.6 + 1.2) * s, z); scl.set(s, s * 1.15, s); mtx.compose(pos, q, scl);
        crowns.setMatrixAt(ti, mtx);
        ti++;
      }
    });
    trunks.count = crowns.count = ti;
    trunks.castShadow = crowns.castShadow = true;
    trees.add(trunks, crowns);
    root.add(trees);

    /* ---------- 标签 / 光柱 / 数据飞线 ---------- */
    const labels = new THREE.Group(); labels.userData.layer = 'labels';
    const beacons = new THREE.Group(); beacons.userData.layer = 'beacon';
    const fly = new THREE.Group(); fly.userData.layer = 'fly';
    const flows = [];
    DISTRICTS.forEach(function (dd) {
      const lb = E.label(dd.name, { accent: '#' + new THREE.Color(dd.color).getHexString(), scale: 1.4 });
      lb.position.set(dd.pos[0], dd.hMax + 22, dd.pos[2]);
      labels.add(lb);
      const bc = E.beaconPillar(2.2, dd.hMax + 14, dd.color);
      bc.position.set(dd.pos[0], (dd.hMax + 14) / 2, dd.pos[2]);
      beacons.add(bc);
      groups[dd.id].bc = bc;
    });
    for (let i = 0; i < DISTRICTS.length; i++) {
      for (let j = i + 1; j < DISTRICTS.length; j++) {
        if (rnd() > .5) continue;
        const a = DISTRICTS[i].pos, b = DISTRICTS[j].pos;
        const mid = new THREE.Vector3((a[0] + b[0]) / 2, 70 + rnd() * 40, (a[2] + b[2]) / 2);
        const cv = new THREE.QuadraticBezierCurve3(
          new THREE.Vector3(a[0], 24, a[2]), mid, new THREE.Vector3(b[0], 24, b[2]));
        const line = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(cv.getPoints(40)),
          new THREE.LineBasicMaterial({ color: 0x9fd8ef, transparent: true, opacity: .16, depthWrite: false }));
        const fl = E.flowLine(cv, { count: 2, size: 2.2, color: 0xa855f7, speed: .3 });
        fly.add(line, fl); flows.push(fl);
      }
    }
    root.add(labels, beacons, fly);

    /* ---------- 交互 ---------- */
    const orbit = E.orbit(E.camera, E.canvas, {
      target: new THREE.Vector3(0, 10, 0), auto: true, speed: .04,
      minDistance: 60, maxDistance: 700
    });
    const pk = E.picker(E.renderer, E.camera, E.canvas);
    pk.setTargets(pickTargets);
    E.canvas.addEventListener('mousemove', pk.onMove);
    E.canvas.addEventListener('click', function () {
      const hit = pk.pick();
      if (hit && hit.obj.userData.data) {
        const dd = hit.obj.parent.userData.dd || (hit.obj.parent.parent && hit.obj.parent.parent.userData.dd);
        if (dd) { bus.emit('focus', { id: dd.id }); ctx.toast('已定位：' + dd.name); }
      }
    });
    bus.on('cmd', function (cmd) { if (cmd === 'reset') orbit.reset(); });
    bus.on('orbit', function (on) { orbit.setAuto(on); });
    bus.on('layer', function (p) { setLayer(p.id, p.on); });
    bus.on('focus', function (p) { focus(String(p.id || '')); });

    function setLayer(id, on) {
      root.traverse(function (o) { if (o.userData && o.userData.layer === id) o.visible = on; });
      if (id === 'roads') cars.visible = lamps.visible = on;
    }
    function focus(id) {
      const g = groups[id]; if (!g) return;
      const p = g.dd.pos;
      orbit.flyTo(new THREE.Vector3(p[0], 12, p[2]), 110, 1.05);
      Object.keys(groups).forEach(function (k) {
        groups[k].bc.visible = true;
        groups[k].bc.material.opacity = k === id ? .95 : .12;
      });
    }

    return {
      orbitRef: orbit,
      update: function (dt, t) {
        driveCars(dt);
        flows.forEach(function (f) { f.update(dt); });
        beacons.children.forEach(function (b) { if (b.update) b.update(dt, t); });
      },
      setLayer: setLayer,
      focus: focus,
      dispose: function () {}
    };
  }
};
