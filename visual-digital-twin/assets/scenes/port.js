/* ============================================================
   Scene: port (realistic) — 港口物流 · 写实版
   天空反射海面 + 混凝土码头 + 4 台岸桥(cr1-cr4) + 集装箱堆场
   + 靠泊船舶 + 集卡流转 + 远洋航线
   图层（对齐 templates/config/port.json）：sea/yard/crane/ship/route/truck
   ============================================================ */
window.__DT_SCENE_SPEC__ = {
  id: 'port', name: '智慧港口 / 物流枢纽（写实）',
  camera: { pos: [130, 85, 170], target: [0, 6, 0] },
  textures: ['concrete', 'ground', 'asphalt'],

  iso: function () {
    return [
      { type: 'block', id: 'quay',  name: '码头岸线', color: 0x22d3ee, x: 0,  z: 0,   w: 46, d: 90, h: 4 },
      { type: 'block', id: 'yardA', name: 'A区重箱堆场', color: 0x3b82f6, x: -55, z: -18, w: 34, d: 40, h: 8 },
      { type: 'block', id: 'yardB', name: 'B区空箱堆场', color: 0x2dd4bf, x: -55, z: 30,  w: 30, d: 30, h: 6 },
      { type: 'block', id: 'ship',  name: '在泊船舶', color: 0xfbbf24, x: 34, z: -6,  w: 22, d: 70, h: 10 }
    ];
  },

  init: async function (E, ctx) {
    const THREE = E.THREE, bus = ctx.bus;
    const root = E.root;

    let seed = 13571;
    function rnd() { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }

    /* ---------- 海面（sea）：天空反射 + 微波光 ---------- */
    const sea = new THREE.Mesh(
      new THREE.PlaneGeometry(2200, 2200),
      E.mat({ color: 0x0e3d58, roughness: .1, metalness: 0, envMapIntensity: 1.35 })
    );
    sea.rotation.x = -Math.PI / 2;
    sea.position.y = -0.5;
    sea.userData.layer = 'sea';
    root.add(sea);
    // 岸线浪沫：码头边一条细白带
    const foam = new THREE.Mesh(new THREE.PlaneGeometry(60, 96), new THREE.MeshBasicMaterial({ color: 0xdfeef5, transparent: true, opacity: .14, depthWrite: false }));
    foam.rotation.x = -Math.PI / 2;
    foam.position.set(31, -0.42, 0);
    foam.userData.layer = 'sea';
    root.add(foam);

    /* ---------- 码头平台（混凝土） ---------- */
    const quay = new THREE.Group();
    const deck = new THREE.Mesh(new THREE.BoxGeometry(50, 3.2, 120), E.texMat('concrete', { repeatX: 5, repeatY: 12, roughness: .8, color: 0xc0c5ca }));
    deck.position.set(5, 1.1, 0);
    deck.castShadow = deck.receiveShadow = true;
    quay.add(deck);
    // 后方堆场地面
    const back = new THREE.Mesh(new THREE.PlaneGeometry(220, 220), E.texMat('ground', { repeatX: 6, repeatY: 6, roughness: .95, color: 0x99a296 }));
    back.rotation.x = -Math.PI / 2;
    back.position.set(-90, -0.02, 0);
    back.receiveShadow = true;
    quay.add(back);
    const apron = new THREE.Mesh(new THREE.PlaneGeometry(150, 130), E.texMat('concrete', { repeatX: 12, repeatY: 11, roughness: .85, color: 0xb6bbc1 }));
    apron.rotation.x = -Math.PI / 2;
    apron.position.set(-45, 0.01, 0);
    apron.receiveShadow = true;
    quay.add(apron);
    // 系船柱
    for (let z = -52; z <= 52; z += 14) {
      const bollard = new THREE.Mesh(new THREE.CylinderGeometry(.5, .6, 1.1, 10), E.mat({ color: 0x2e343b, roughness: .6, metalness: .4 }));
      bollard.position.set(28, 3.3, z);
      bollard.castShadow = true;
      quay.add(bollard);
    }
    root.add(quay);

    /* ---------- 岸桥 ×4（crane，cr1-cr4 实体） ---------- */
    const cranes = new THREE.Group(); cranes.userData.layer = 'crane';
    const craneMat = E.mat({ color: 0x1f6f8b, roughness: .45, metalness: .55 });
    const craneMat2 = E.mat({ color: 0x175063, roughness: .5, metalness: .5 });
    const CRANES = [
      { id: 'cr1', z: -36 }, { id: 'cr2', z: -12 }, { id: 'cr3', z: 12 }, { id: 'cr4', z: 36 }
    ];
    const cranePick = [], trolleys = [];
    CRANES.forEach(function (c) {
      const g = new THREE.Group();
      g.position.set(14, 2.7, c.z);
      const legGeo = new THREE.BoxGeometry(1.6, 34, 1.6);
      [[-4, 7], [-4, -7], [16, 7], [16, -7]].forEach(function (lp) {
        const leg = new THREE.Mesh(legGeo, craneMat);
        leg.position.set(lp[0], 17, lp[1]);
        leg.castShadow = true;
        g.add(leg);
      });
      // 门框横梁 + 后拉杆
      const beam = new THREE.Mesh(new THREE.BoxGeometry(24, 1.8, 2.2), craneMat);
      beam.position.set(6, 33, 0); beam.castShadow = true;
      g.add(beam);
      // 前大梁（伸向海侧，微翘）
      const boom = new THREE.Mesh(new THREE.BoxGeometry(46, 1.6, 2.0), craneMat);
      boom.position.set(22, 36.5, 0); boom.rotation.z = -.06; boom.castShadow = true;
      g.add(boom);
      // 机器房 + A 型主桅 + 前大梁拉杆（岸桥轮廓的关键）
      const house = new THREE.Mesh(E.rbox(7, 4.5, 6, .2), craneMat2);
      house.position.set(-2, 36.8, 0); house.castShadow = true;
      g.add(house);
      const mast = new THREE.Mesh(new THREE.BoxGeometry(1.8, 16, 1.8), craneMat2);
      mast.position.set(2, 44, 0); mast.castShadow = true;
      g.add(mast);
      // 拉杆：主桅顶 → 前大梁前端（几何对齐：长度/角度按两端点求出）
      const a = new THREE.Vector3(2, 52, 0), b = new THREE.Vector3(44, 37.2, 0);
      const tieLen = a.distanceTo(b);
      const tie = new THREE.Mesh(new THREE.CylinderGeometry(.16, .16, tieLen, 6), craneMat2);
      tie.position.copy(a).add(b).multiplyScalar(.5);
      tie.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
      g.add(tie);
      // 后拉杆：主桅顶 → 机器房后
      const tie2 = new THREE.Mesh(new THREE.CylinderGeometry(.14, .14, 14, 6), craneMat2);
      tie2.position.set(0, 46.5, 0);
      tie2.rotation.z = 1.2;
      g.add(tie2);
      // 小车 + 吊具（沿前大梁动画）
      const trolley = new THREE.Group();
      const tc = new THREE.Mesh(E.rbox(2.4, 1.6, 3, .1), craneMat2);
      const cable = new THREE.Mesh(new THREE.CylinderGeometry(.06, .06, 10, 4), E.mat({ color: 0x111418, roughness: .8 }));
      cable.position.y = -6;
      const spreader = new THREE.Mesh(new THREE.BoxGeometry(3.2, .5, 1.4), E.mat({ color: 0xd8a013, roughness: .5, metalness: .4 }));
      spreader.position.y = -11;
      trolley.add(tc, cable, spreader);
      trolley.position.set(18, 35.6, 0);
      g.add(trolley);
      trolleys.push({ t: trolley, phase: rnd() * 6.28, base: g.position.y });
      g.userData.focusId = c.id;
      g.userData.data = { name: '岸桥 ' + c.id.slice(2) + '#', desc: '外伸距 55m · 起升 40m', metrics: [['额定', 65, 't'], ['效率', 32, '箱/h']] };
      cranePick.push(boom);
      cranes.add(g);
    });
    root.add(cranes);

    /* ---------- 在泊船舶（ship） ---------- */
    const ships = new THREE.Group(); ships.userData.layer = 'ship';
    const shipGroup = new THREE.Group();
    const hullMat = E.mat({ color: 0x1d3a52, roughness: .55, metalness: .3 });
    const hull = new THREE.Mesh(E.rbox(20, 8, 64, 1.6), hullMat);
    hull.position.set(44, 1.2, -6);
    hull.castShadow = true;
    // 球鼻艏近似：船头收窄楔块
    const bow = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 9.6, 14, 4), hullMat);
    bow.rotation.x = Math.PI / 2; bow.rotation.y = Math.PI / 4;
    bow.scale.set(1.05, 1, .55);
    bow.position.set(44, 1.2, -44);
    bow.castShadow = true;
    const deckhouse = new THREE.Mesh(E.rbox(12, 10, 8, .4), E.mat({ color: 0xe8edf2, roughness: .5 }));
    deckhouse.position.set(44, 10.5, 22);
    deckhouse.castShadow = true;
    const bridge = new THREE.Mesh(new THREE.BoxGeometry(13, 1.2, 9), E.mat({ color: 0x35414d, roughness: .5 }));
    bridge.position.set(44, 16.4, 22);
    ships.add(hull, bow, deckhouse, bridge);
    // 甲板集装箱
    const contColors = [0x8c2f39, 0x27536b, 0x3f6f4f, 0x6e7a85, 0xb06f2e];
    for (let i = 0; i < 24; i++) {
      const box = new THREE.Mesh(E.rbox(2.5, 2.6, 6.2, .12), E.mat({ color: contColors[i % contColors.length], roughness: .55, metalness: .3 }));
      const row = Math.floor(i / 8);
      box.position.set(43.4 + (i % 2) * 2.8, 5.5 + row * 2.7, -32 + (i % 8) * 7.4);
      box.castShadow = true;
      ships.add(box);
    }
    ships.add(shipGroup);
    root.add(ships);

    /* ---------- 集装箱堆场（yard）：龙门架间成排堆叠 ---------- */
    const yard = new THREE.Group(); yard.userData.layer = 'yard';
    const contGeo = E.rbox(2.5, 2.6, 6.2, .1, 1);
    const YARD_BLOCKS = [
      { x: -38, z: -30, rows: 4, name: 'A区重箱堆场' },
      { x: -38, z: 6,  rows: 4, name: 'A区中转堆场' },
      { x: -72, z: -30, rows: 3, name: 'B区空箱堆场' },
      { x: -72, z: 6,  rows: 3, name: 'C区冷藏堆场' }
    ];
    YARD_BLOCKS.forEach(function (B) {
      const perRow = 10;
      const count = B.rows * perRow * 3.2 | 0;
      // 每块一个 InstancedMesh：颜色用 instanceColor（混灰降饱和，避免玩具感）
      const im = new THREE.InstancedMesh(contGeo, E.mat({ color: 0xffffff, roughness: .55, metalness: .3 }), count);
      const mtx = new THREE.Matrix4(), pos = new THREE.Vector3(), q = new THREE.Quaternion(), scl = new THREE.Vector3(1, 1, 1);
      const col = new THREE.Color(), grey = new THREE.Color(0x8a8f94);
      let i = 0;
      for (let r = 0; r < B.rows && i < count; r++) {
        for (let k = 0; k < perRow && i < count; k++) {
          const stack = 2 + Math.floor(rnd() * 3);   // 2-4 层，堆场应有体量
          for (let s = 0; s < stack && i < count; s++) {
            pos.set(B.x + r * 2.9, 1.4 + s * 2.7, B.z - 28 + k * 7.4);
            mtx.compose(pos, q, scl);
            im.setMatrixAt(i, mtx);
            col.setHex(contColors[Math.floor(rnd() * contColors.length)]).lerp(grey, .3);
            im.setColorAt(i, col);
            i++;
          }
        }
      }
      im.count = i;
      im.instanceMatrix.needsUpdate = true;
      if (im.instanceColor) im.instanceColor.needsUpdate = true;
      im.castShadow = im.receiveShadow = true;
      im.userData.data = { name: B.name, desc: '堆存能力 ' + (B.rows * 40) + ' TEU', metrics: [['占用', 60 + Math.floor(rnd() * 30), '%']] };
      yard.add(im);
      // 龙门架轨道梁
      const rail1 = new THREE.Mesh(new THREE.BoxGeometry(1, .8, 64), E.mat({ color: 0x3a424b, roughness: .5, metalness: .5 }));
      rail1.position.set(B.x - 5, .5, B.z + 4);
      const rail2 = rail1.clone(); rail2.position.x = B.x + B.rows * 2.9 + 3;
      yard.add(rail1, rail2);
    });
    root.add(yard);

    /* ---------- 集卡（truck）：码头 ↔ 堆场 ---------- */
    const trucks = new THREE.Group(); trucks.userData.layer = 'truck';
    const cabMat = E.mat({ color: 0xc24318, roughness: .4, metalness: .4 });
    for (let i = 0; i < 6; i++) {
      const g = new THREE.Group();
      const cab = new THREE.Mesh(E.rbox(2.4, 2.6, 2.4, .2), cabMat);
      cab.position.set(0, 1.9, 0); cab.castShadow = true;
      const chassis = new THREE.Mesh(new THREE.BoxGeometry(7.5, .5, 2.2), E.mat({ color: 0x2a2f36, roughness: .7 }));
      chassis.position.set(-2.6, .9, 0);
      const cont = new THREE.Mesh(E.rbox(6.2, 2.6, 2.4, .12), E.mat({ color: contColors[i % contColors.length], roughness: .55, metalness: .3 }));
      cont.position.set(-3.2, 2.5, 0); cont.castShadow = true;
      g.add(cab, chassis, cont);
      g.userData.t = i / 6;
      g.userData.speed = .04 + rnd() * .015;
      g.userData.flip = i % 2 === 1;
      trucks.add(g);
    }
    root.add(trucks);
    // 集卡路径：岸桥下 → 水平 → 堆场（矩形环）
    function driveTrucks(dt) {
      trucks.children.forEach(function (g, i) {
        const u = g.userData;
        u.t += dt * u.speed; if (u.t > 1) u.t -= 1;
        // 环线参数化：码头前沿 x=20 → 堆场巷道
        const zLane = -30 + i * 12;
        const seg = u.t * 4, f = seg % 1;
        let x, z, ry;
        if (seg < 1) { x = 22 - f * 40; z = zLane; ry = Math.PI / 2; }                       // 岸侧→堆场
        else if (seg < 2) { x = -18; z = zLane + f * 22 * (u.flip ? -1 : 1); ry = u.flip ? Math.PI : 0; } // 巷道内
        else if (seg < 3) { x = -18 + f * 40; z = zLane + 22 * (u.flip ? -1 : 1); ry = -Math.PI / 2; }    // 堆场→岸侧
        else { x = 22; z = zLane + 22 * (u.flip ? -1 : 1) - f * 22 * (u.flip ? -1 : 1); ry = u.flip ? 0 : Math.PI; }
        g.position.set(x, 0, z);
        g.rotation.y = ry;
      });
    }

    /* ---------- 远洋航线（route） ---------- */
    const route = new THREE.Group(); route.userData.layer = 'route';
    const flows = [];
    [[-500, -260, .09], [-460, 300, .07], [520, -180, .08]].forEach(function (R, i) {
      const cv = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(60, 2, -60 + i * 40),
        new THREE.Vector3(R[0] * .5, 26, R[1] * .5),
        new THREE.Vector3(R[0], 2, R[1]));
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(cv.getPoints(48)),
        new THREE.LineBasicMaterial({ color: 0x9fd8ef, transparent: true, opacity: .15, depthWrite: false }));
      const fl = E.flowLine(cv, { count: 2, size: 2.6, color: 0xffd166, speed: R[2] });
      route.add(line, fl); flows.push(fl);
    });
    root.add(route);

    /* ---------- 标签 ---------- */
    const labels = new THREE.Group(); labels.userData.layer = 'labels';
    [
      { t: '码头岸线 · 泊位 A/B', p: [10, 16, 0] },
      { t: '重箱堆场 A区', p: [-38, 16, -30] },
      { t: '空箱堆场 B区', p: [-72, 13, -30] },
      { t: '在泊轮「沪航 12」', p: [44, 24, -6] }
    ].forEach(function (L) {
      const lb = E.label(L.t, { scale: 1.2 });
      lb.position.set(L.p[0], L.p[1], L.p[2]);
      labels.add(lb);
    });
    root.add(labels);

    /* ---------- 交互 ---------- */
    const orbit = E.orbit(E.camera, E.canvas, {
      target: new THREE.Vector3(0, 6, 0), auto: true, speed: .035,
      minDistance: 50, maxDistance: 600
    });
    const pk = E.picker(E.renderer, E.camera, E.canvas);
    pk.setTargets(cranePick);
    E.canvas.addEventListener('mousemove', pk.onMove);
    E.canvas.addEventListener('click', function () {
      const hit = pk.pick();
      if (hit && hit.object.userData.focusId) {
        bus.emit('focus', { id: hit.object.userData.focusId });
        ctx.toast('已定位：' + hit.object.userData.data.name);
      } else if (hit && hit.object.userData.data) {
        ctx.toast(hit.object.userData.data.name + ' · ' + (hit.object.userData.data.desc || ''));
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
      const c = CRANES.find(function (x) { return x.id === id; });
      if (c) {
        orbit.flyTo(new THREE.Vector3(16, 14, c.z), 78, 1.08);
        return;
      }
      const spots = {
        yard: { v: [-50, 6, -10], r: 150 }, ship: { v: [44, 8, -6], r: 110 },
        quay: { v: [10, 4, 0], r: 140 }, sea: { v: [80, 0, 0], r: 200 }
      };
      const s = spots[id];
      if (s) orbit.flyTo(new THREE.Vector3(s.v[0], s.v[1], s.v[2]), s.r, 1.05);
    }

    return {
      orbitRef: orbit,
      update: function (dt, t) {
        driveTrucks(dt);
        flows.forEach(function (f) { f.update(dt); });
        // 小车往返 + 船体微摇
        trolleys.forEach(function (tr) {
          const k = (Math.sin(t * .25 + tr.phase) + 1) / 2;
          tr.t.position.x = 40 - k * 44;
          tr.t.children[1].position.y = -6 - Math.sin(t * .5 + tr.phase) * .8;
        });
        ships.position.y = Math.sin(t * .6) * .18;
      },
      setLayer: setLayer,
      focus: focus,
      dispose: function () {}
    };
  }
};
