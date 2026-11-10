/* ============================================================
   Scene: refinery (realistic) — 炼油厂 / 石化基地 · 写实版
   参照实景照片布局：中央常减压塔群 + 奶油色大烟囱(烟气) + 黑色烟囱
   + 右侧球罐区 + 浮顶罐区 + 跨路管廊 + 厂前办公楼 + 行道树
   图层：towers/tanks/pipes/smoke/trees/labels
   实体：t1 常压塔 / t2 减压塔 / t3 液化气球罐区 / t4 储罐区 / t5 加氢装置
   ============================================================ */
window.__DT_SCENE_SPEC__ = {
  id: 'refinery', name: '炼油厂 / 石化基地（写实）',
  camera: { pos: [110, 78, 130], target: [0, 10, 0] },
  textures: ['ground', 'concrete', 'asphalt', 'tank', 'wallsteel', 'lawn'],

  iso: function () {
    return [
      { type: 'block', id: 't1', name: '常压塔', color: 0x94a3b8, x: -12, z: -18, w: 9, d: 9, h: 34 },
      { type: 'block', id: 't2', name: '减压塔', color: 0x94a3b8, x: 0, z: -24, w: 10, d: 10, h: 26 },
      { type: 'block', id: 't5', name: '加氢精制装置', color: 0x2dd4bf, x: -34, z: 6, w: 12, d: 10, h: 18 },
      { type: 'block', id: 't3', name: '液化气球罐区', color: 0xe2e8f0, x: 46, z: -20, w: 30, d: 26, h: 14 },
      { type: 'block', id: 't4', name: '成品储罐区', color: 0xf8fafc, x: 44, z: 26, w: 30, d: 20, h: 13 },
      { type: 'block', id: 'stack', name: '动力烟囱', color: 0xd9c9a3, x: -38, z: -30, w: 7, d: 7, h: 58 },
      { type: 'block', id: 'office', name: '综合办公楼', color: 0x60a5fa, x: -45, z: 34, w: 20, d: 14, h: 13 }
    ];
  },

  init: async function (E, ctx) {
    const THREE = E.THREE, bus = ctx.bus;
    const root = E.root;

    /* ---------- 地面：厂区混凝土 + 外围 + 环路 ---------- */
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(420, 420), E.texMat('ground', { repeatX: 7, repeatY: 7, roughness: .95, color: 0x8fa08a }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.05;
    ground.receiveShadow = true;
    root.add(ground);
    const yard = new THREE.Mesh(new THREE.PlaneGeometry(230, 210), E.texMat('concrete', { repeatX: 18, repeatY: 16, roughness: .82, color: 0xb9bdc2 }));
    yard.rotation.x = -Math.PI / 2; yard.position.y = 0.03;
    yard.receiveShadow = true;
    root.add(yard);
    const loop = new THREE.Mesh(new THREE.RingGeometry(112, 121, 64), E.texMat('asphalt', { repeatX: 22, repeatY: 2, roughness: .9 }));
    loop.rotation.x = -Math.PI / 2; loop.position.y = 0.05;
    root.add(loop);
    if (loop.material.map) { loop.material.map = loop.material.map.clone(); loop.material.map.repeat.set(26, 2); loop.material.map.needsUpdate = true; }

    /* ---------- 主干道（纵向贯穿，同照片）+ 横向道路 ---------- */
    const roadGrp = new THREE.Group(); roadGrp.userData.layer = 'trees';
    const roadMat = E.texMat('asphalt', { repeatX: 2, repeatY: 30, roughness: .92, color: 0x4a4f55 });
    function strip(w, d, x, z) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), roadMat);
      m.rotation.x = -Math.PI / 2; m.position.set(x, .06, z);
      m.receiveShadow = true;
      return m;
    }
    roadGrp.add(strip(11, 200, 18, 0));
    roadGrp.add(strip(160, 9, 6, 34));
    roadGrp.add(strip(120, 8, -46, -2));
    // 车道虚线
    const dashMat = E.mat({ color: 0xd8dde2, roughness: .6 });
    for (let z = -95; z <= 95; z += 10) {
      const dash = new THREE.Mesh(new THREE.PlaneGeometry(.5, 4.5), dashMat);
      dash.rotation.x = -Math.PI / 2; dash.position.set(18, .08, z);
      roadGrp.add(dash);
    }
    root.add(roadGrp);

    let seed = 9107;
    function rnd() { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }

    const pick = [];
    const statusBeacons = {};
    function beacon(parent, id, x, z, h, status) {
      const c = status === 'alarm' ? 0xfb7185 : status === 'warn' ? 0xfbbf24 : 0x34d399;
      const bc = E.beaconPillar(2.4, h, c);
      bc.position.set(x, h / 2, z);
      bc.material.opacity = status === 'normal' ? .26 : .8;
      parent.add(bc);
      statusBeacons[id] = bc;
    }

    /* ---------- 常减压装置区（towers / t1 t2） ---------- */
    const towers = new THREE.Group(); towers.userData.layer = 'towers';
    const steelMat = E.mat({ color: 0x8d97a3, roughness: .4, metalness: .65 });
    const towerTex = E.texMat('tank', { repeatX: 4, repeatY: 5, roughness: .42, metalness: .55, color: 0xcfd6dd });
    function makeTower(id, name, x, z, r, h, status) {
      const g = new THREE.Group();
      const body = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 24), towerTex);
      body.position.set(x, h / 2, z);
      body.castShadow = body.receiveShadow = true;
      const top = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 10, 0, Math.PI * 2, 0, Math.PI / 2), towerTex);
      top.position.set(x, h, z);
      top.castShadow = true;
      const base = new THREE.Mesh(new THREE.CylinderGeometry(r + .6, r + .8, 1, 24), E.mat({ color: 0x6b7280, roughness: .8 }));
      base.position.set(x, .5, z);
      base.receiveShadow = true;
      g.add(body, top, base);
      // 塔身平台圈
      for (let i = 1; i <= Math.floor(h / 8); i++) {
        const ring = new THREE.Mesh(new THREE.CylinderGeometry(r + .9, r + .9, .35, 24), steelMat);
        ring.position.set(x, i * 8, z);
        g.add(ring);
      }
      // 顶部小管
      const tip = new THREE.Mesh(new THREE.CylinderGeometry(.35, .35, 4, 8), steelMat);
      tip.position.set(x, h + r * .5 + 2, z);
      g.add(tip);
      g.userData.focusId = id;
      g.userData.data = { name: name, desc: '运行中 · 塔顶温度/压力正常', metrics: [['塔高', h, 'm'], ['直径', r * 2, 'm']] };
      towers.add(g);
      pick.push(body);
      return g;
    }
    makeTower('t1', '常压塔', -12, -18, 4, 34, 'normal');
    makeTower('t2', '减压塔', 0, -26, 4.6, 26, 'normal');
    makeTower('t2b', '初馏塔', -26, -12, 2.2, 17, 'normal');
    makeTower('t2c', '稳定塔', -3, -7, 2.4, 19, 'normal');
    // 塔群钢构架（精馏框架，同照片中央钢架）
    const frame = new THREE.Group();
    const fx = 9, fz = -16, fw = 22, fd = 16, fh = 24;
    [[fx - fw / 2, fz - fd / 2], [fx + fw / 2, fz - fd / 2], [fx - fw / 2, fz + fd / 2], [fx + fw / 2, fz + fd / 2]].forEach(function (p) {
      const col = new THREE.Mesh(new THREE.BoxGeometry(.8, fh, .8), steelMat);
      col.position.set(p[0], fh / 2, p[1]);
      col.castShadow = true;
      frame.add(col);
    });
    for (let y = 6; y <= fh; y += 6) {
      [[fx, fz - fd / 2, fw, .6], [fx, fz + fd / 2, fw, .6]].forEach(function (b) {
        const bm = new THREE.Mesh(new THREE.BoxGeometry(b[2], .5, b[3]), steelMat);
        bm.position.set(b[0], y, b[1]);
        bm.castShadow = true;
        frame.add(bm);
      });
    }
    // 框架内的换热器/反应器小塔
    for (let i = 0; i < 3; i++) {
      const mini = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, 12 + i * 3, 16), towerTex);
      mini.position.set(fx - 6 + i * 6, (12 + i * 3) / 2 + 2, fz);
      mini.castShadow = true;
      frame.add(mini);
    }
    towers.add(frame);
    // 装置区接触阴影
    const cs1 = E.contactShadow(46, 34);
    cs1.position.set(-8, .07, -18);
    towers.add(cs1);
    root.add(towers);

    /* ---------- 加氢精制装置（t5） ---------- */
    const hydro = new THREE.Group(); hydro.userData.layer = 'towers';
    const reactor = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 2.6, 21, 20), towerTex);
    reactor.position.set(-38, 10.5, 8);
    reactor.castShadow = true;
    const drum = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 9, 18), towerTex);
    drum.rotation.z = Math.PI / 2;
    drum.position.set(-30, 3.4, 12);
    drum.castShadow = true;
    const hydBase = new THREE.Mesh(new THREE.BoxGeometry(18, 1, 14), E.mat({ color: 0x7d8694, roughness: .8 }));
    hydBase.position.set(-33, .5, 9);
    hydBase.receiveShadow = true;
    reactor.userData.focusId = 't5';
    reactor.userData.data = { name: '加氢精制装置', desc: '反应温度偏高，已提示班组关注', metrics: [['反应器高', 21, 'm'], ['设计压力', 15.2, 'MPa']] };
    hydro.add(reactor, drum, hydBase);
    beacon(hydro, 't5', -38, 8, 32, 'warn');
    pick.push(reactor);
    root.add(hydro);

    /* ---------- 烟囱（奶油色大烟囱 + 黑色烟囱） ---------- */
    const stacks = new THREE.Group(); stacks.userData.layer = 'smoke';
    const stackMain = new THREE.Mesh(new THREE.CylinderGeometry(2.8, 3.8, 58, 20), E.texMat('concrete', { repeatX: 3, repeatY: 8, roughness: .85, color: 0xd9c9a3 }));
    stackMain.position.set(-38, 29, -32);
    stackMain.castShadow = true;
    const stackBand = new THREE.Mesh(new THREE.CylinderGeometry(2.95, 2.95, 4, 20), E.mat({ color: 0xb45a5a, roughness: .7 }));
    stackBand.position.set(-38, 52, -32);
    stacks.add(stackMain, stackBand);
    const stackDark = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 3.0, 48, 20), E.texMat('wallsteel', { repeatX: 3, repeatY: 6, roughness: .7, metalness: .3, color: 0x3a3f45 }));
    stackDark.position.set(30, 24, -44);
    stackDark.castShadow = true;
    stacks.add(stackDark);
    root.add(stacks);

    /* ---------- 烟气（烟囱口 sprite，缓升扩散） ---------- */
    const smokes = new THREE.Group(); smokes.userData.layer = 'smoke';
    const smokeTex = (function () {
      const cv = document.createElement('canvas'); cv.width = cv.height = 128;
      const c2 = cv.getContext('2d');
      const gr = c2.createRadialGradient(64, 64, 8, 64, 64, 62);
      gr.addColorStop(0, 'rgba(245,247,250,.85)');
      gr.addColorStop(.5, 'rgba(235,240,245,.38)');
      gr.addColorStop(1, 'rgba(235,240,245,0)');
      c2.fillStyle = gr; c2.fillRect(0, 0, 128, 128);
      const t = new THREE.CanvasTexture(cv);
      t.colorSpace = THREE.SRGBColorSpace;
      return t;
    })();
    for (let i = 0; i < 10; i++) {
      const sm = new THREE.Sprite(new THREE.SpriteMaterial({ map: smokeTex, transparent: true, opacity: .5, depthWrite: false }));
      sm.position.set(-38 + (rnd() - .5) * 3, 60 + i * 4.2, -32 + (rnd() - .5) * 3);
      sm.scale.setScalar(8 + i * 1.6);
      sm.userData = { v: .028 + rnd() * .012, base: 60 + i * 4.2, drift: (rnd() - .5) * .5 };
      smokes.add(sm);
    }
    root.add(smokes);

    /* ---------- 液化气球罐区（t3，右侧球罐，同照片） ---------- */
    const tanks = new THREE.Group(); tanks.userData.layer = 'tanks';
    const sphereTex = E.texMat('tank', { repeatX: 3, repeatY: 2, roughness: .35, metalness: .25, color: 0xf4f7fa });
    const SPHERES = [
      { x: 38, z: -26 }, { x: 54, z: -26 }, { x: 38, z: -12 }, { x: 54, z: -12 }
    ];
    SPHERES.forEach(function (s, i) {
      const g = new THREE.Group();
      const R = 6;
      const ball = new THREE.Mesh(new THREE.SphereGeometry(R, 28, 18), sphereTex);
      ball.position.set(s.x, R + 6, s.z);
      ball.castShadow = ball.receiveShadow = true;
      g.add(ball);
      // 支腿
      for (let k = 0; k < 5; k++) {
        const ang = (k / 5) * Math.PI * 2;
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(.45, .45, 6.4, 8), steelMat);
        leg.position.set(s.x + Math.cos(ang) * R * .62, 3.2, s.z + Math.sin(ang) * R * .62);
        leg.castShadow = true;
        g.add(leg);
      }
      const pad = new THREE.Mesh(new THREE.CylinderGeometry(R + 2.4, R + 2.8, .6, 24), E.mat({ color: 0x8a929c, roughness: .9 }));
      pad.position.set(s.x, .3, s.z);
      pad.receiveShadow = true;
      g.add(pad);
      const id = 't3';
      ball.userData.focusId = id;
      ball.userData.data = { name: '液化气球罐区 · ' + (i + 1) + '#球罐', desc: i === 1 ? '液位 91%，达到警戒线' : '运行中', metrics: [['容积', 1000, 'm³'], ['液位', i === 1 ? 91 : 62 + i * 6, '%']] };
      tanks.add(g);
      pick.push(ball);
    });
    beacon(tanks, 't3', 46, -19, 26, 'alarm');
    root.add(tanks);

    /* ---------- 成品储罐区（t4，浮顶罐，同照片右侧白罐） ---------- */
    const TANKS4 = [
      { x: 36, z: 22 }, { x: 48, z: 22 }, { x: 60, z: 22 }, { x: 42, z: 34 }, { x: 56, z: 34 }
    ];
    const vtankTex = E.texMat('tank', { repeatX: 4, repeatY: 2, roughness: .45, metalness: .3, color: 0xf2f5f8 });
    TANKS4.forEach(function (t, i) {
      const g = new THREE.Group();
      const h = 12;
      const body = new THREE.Mesh(new THREE.CylinderGeometry(5, 5, h, 24), vtankTex);
      body.position.set(t.x, h / 2, t.z);
      body.castShadow = body.receiveShadow = true;
      const roof = new THREE.Mesh(new THREE.SphereGeometry(5, 24, 8, 0, Math.PI * 2, 0, Math.PI / 2), vtankTex);
      roof.position.set(t.x, h, t.z);
      roof.scale.y = .35;
      roof.castShadow = true;
      const rim = new THREE.Mesh(new THREE.TorusGeometry(5.05, .18, 8, 32), steelMat);
      rim.rotation.x = Math.PI / 2;
      rim.position.set(t.x, h + .3, t.z);
      const ladder = new THREE.Mesh(new THREE.BoxGeometry(.5, h + 2, .18), E.mat({ color: 0x2a3138, roughness: .6, metalness: .5 }));
      ladder.position.set(t.x + 5.2, (h + 2) / 2, t.z);
      g.add(body, roof, rim, ladder);
      body.userData.focusId = 't4';
      body.userData.data = { name: '成品储罐区 · ' + (i + 1) + '#罐', desc: '运行中 · 液位/温度正常', metrics: [['罐高', h, 'm'], ['直径', 10, 'm']] };
      tanks.add(g);
      pick.push(body);
    });
    beacon(tanks, 't4', 48, 28, 24, 'normal');
    const cs2 = E.contactShadow(38, 22);
    cs2.position.set(48, .07, 28);
    tanks.add(cs2);
    root.add(tanks);

    /* ---------- 管廊（pipes）：装置区 ↔ 罐区，跨主干道 ---------- */
    const pipes = new THREE.Group(); pipes.userData.layer = 'pipes';
    const pipeMat = E.mat({ color: 0x9aa3ad, roughness: .35, metalness: .7 });
    function pipe(x1, y1, z1, x2, y2, z2, r) {
      const v1 = new THREE.Vector3(x1, y1, z1), v2 = new THREE.Vector3(x2, y2, z2);
      const len = v1.distanceTo(v2);
      const seg = new THREE.Mesh(new THREE.CylinderGeometry(r || .26, r || .26, len, 10), pipeMat);
      seg.position.copy(v1).add(v2).multiplyScalar(.5);
      seg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v2.clone().sub(v1).normalize());
      seg.castShadow = true;
      pipes.add(seg);
    }
    // 管廊一：装置区 → 球罐区（跨主干道）
    const rackY = 6.4;
    pipe(-14, rackY, -4, 40, rackY, -4, .34);
    pipe(-14, rackY, -1.2, 40, rackY, -1.2, .26);
    pipe(-14, rackY, 1.6, 40, rackY, 1.6, .2);
    for (let x = -10; x <= 38; x += 8) {
      const post = new THREE.Mesh(new THREE.BoxGeometry(.7, rackY, 4.4), E.mat({ color: 0x59626d, roughness: .6, metalness: .5 }));
      post.position.set(x, rackY / 2, -1.2);
      post.castShadow = true;
      pipes.add(post);
    }
    pipe(40, rackY, -4, 38, rackY, -24, .3);
    pipe(40, rackY, 1.6, 42, rackY, 20, .26);
    // 管廊二：装置区 → 加氢装置
    pipe(-26, rackY, 2, -38, rackY, 8, .26);
    pipe(-12, rackY, -18, -12, rackY, 6, .28);
    // 塔顶气管
    pipe(-12, 35, -18, -3, 35, -18, .18);
    pipe(-3, 35, -18, -3, 20, -7, .18);
    root.add(pipes);

    /* ---------- 厂前区办公楼（左侧蓝白建筑，同照片） ---------- */
    const office = new THREE.Group(); office.userData.layer = 'trees';
    function windowTexture() {
      const cv = document.createElement('canvas'); cv.width = 64; cv.height = 64;
      const c2 = cv.getContext('2d');
      c2.fillStyle = '#33445a'; c2.fillRect(0, 0, 64, 64);
      for (let y = 4; y < 60; y += 9) for (let x = 3; x < 60; x += 8) {
        c2.fillStyle = Math.random() > .3 ? 'rgba(150,200,240,.6)' : 'rgba(20,28,40,.95)';
        c2.fillRect(x, y, 5.4, 5.6);
      }
      const t = new THREE.CanvasTexture(cv);
      t.colorSpace = THREE.SRGBColorSpace;
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      return t;
    }
    const ofWin = windowTexture();
    const officeMat = E.mat({ color: 0xffffff, roughness: .22, metalness: .45 });
    officeMat.map = ofWin; officeMat.emissiveMap = ofWin;
    officeMat.emissive = new THREE.Color(0xffe9b8);
    officeMat.emissiveIntensity = .05;
    E.onTOD(function (t) { officeMat.emissiveIntensity = t === 'dusk' ? 1.0 : .05; });
    const ob1 = new THREE.Mesh(E.rbox(22, 13, 13, .3), officeMat);
    ob1.position.set(-48, 6.5, 36);
    ob1.castShadow = ob1.receiveShadow = true;
    const ob2 = new THREE.Mesh(E.rbox(15, 9, 10, .25), officeMat);
    ob2.position.set(-48, 4.5, 52);
    ob2.castShadow = ob2.receiveShadow = true;
    office.add(ob1, ob2);
    // 中央控制室小楼
    const ctrl = new THREE.Mesh(E.rbox(10, 6, 8, .2), E.mat({ color: 0xdfe7ee, roughness: .5 }));
    ctrl.position.set(-30, 3, 46);
    ctrl.castShadow = ctrl.receiveShadow = true;
    office.add(ctrl);
    root.add(office);

    /* ---------- 草坪 + 行道树 ---------- */
    const green = new THREE.Group(); green.userData.layer = 'trees';
    const lawnMat = E.texMat('lawn', { repeatX: 5, repeatY: 4, roughness: .95 });
    [[-48, 40, 44, 34], [-20, 56, 34, 16]].forEach(function (p) {
      const lp = new THREE.Mesh(new THREE.PlaneGeometry(p[2], p[3]), lawnMat);
      lp.rotation.x = -Math.PI / 2; lp.position.set(p[0], .04, p[1]);
      lp.receiveShadow = true;
      green.add(lp);
    });
    const trunkGeo = new THREE.CylinderGeometry(.22, .34, 2.6, 6);
    const crownGeo = new THREE.IcosahedronGeometry(1.7, 1);
    const trunkMat = E.mat({ color: 0x5a4632, roughness: .95 });
    const crownMat = E.mat({ color: 0x3f7036, roughness: .95, flatShading: true });
    const treeSpots = [];
    for (let z = -70; z <= 80; z += 11) { treeSpots.push([12.2, z]); treeSpots.push([23.8, z]); }
    for (let x = -80; x <= 80; x += 11) { treeSpots.push([x, 38.8]); treeSpots.push([x, 29.2]); }
    const NT = treeSpots.length;
    const trunks = new THREE.InstancedMesh(trunkGeo, trunkMat, NT);
    const crowns = new THREE.InstancedMesh(crownGeo, crownMat, NT);
    const pos = new THREE.Vector3(), scl = new THREE.Vector3(), q = new THREE.Quaternion(), mtx = new THREE.Matrix4();
    treeSpots.forEach(function (p, i) {
      const s = .75 + rnd() * .7;
      pos.set(p[0], 1.3 * s, p[1]); scl.set(1, s, 1); mtx.compose(pos, q, scl);
      trunks.setMatrixAt(i, mtx);
      pos.set(p[0], (2.6 + 1.1) * s, p[1]); scl.set(s, s * 1.15, s); mtx.compose(pos, q, scl);
      crowns.setMatrixAt(i, mtx);
    });
    trunks.castShadow = crowns.castShadow = true;
    green.add(trunks, crowns);
    root.add(green);

    /* ---------- 标签 ---------- */
    const labels = new THREE.Group(); labels.userData.layer = 'labels';
    [
      { t: '常减压蒸馏装置', p: [-8, 46, -20] },
      { t: '液化气球罐区', p: [46, 26, -19] },
      { t: '成品储罐区', p: [48, 22, 28] },
      { t: '动力烟囱', p: [-38, 66, -32] },
      { t: '综合办公楼', p: [-48, 20, 42] },
      { t: '加氢精制装置', p: [-36, 30, 9] }
    ].forEach(function (L) {
      const lb = E.label(L.t, { scale: 1.2 });
      lb.position.set(L.p[0], L.p[1], L.p[2]);
      labels.add(lb);
    });
    root.add(labels);

    /* ---------- 交互 ---------- */
    const orbit = E.orbit(E.camera, E.canvas, {
      target: new THREE.Vector3(0, 10, 0), auto: true, speed: .033,
      minDistance: 45, maxDistance: 440
    });
    const pk = E.picker(E.renderer, E.camera, E.canvas);
    pk.setTargets(pick);
    E.canvas.addEventListener('mousemove', pk.onMove);
    E.canvas.addEventListener('click', function () {
      const hit = pk.pick();
      if (hit && hit.obj.userData && hit.obj.userData.focusId) {
        bus.emit('focus', { id: hit.obj.userData.focusId });
        ctx.toast('已定位：' + hit.obj.userData.data.name);
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
      const spots = {
        t1: { v: [-12, 14, -18], r: 62 },
        t2: { v: [0, 12, -26], r: 58 },
        t3: { v: [46, 10, -19], r: 66 },
        t4: { v: [48, 8, 28], r: 62 },
        t5: { v: [-36, 10, 9], r: 52 },
        stack: { v: [-38, 26, -32], r: 70 },
        office: { v: [-48, 7, 42], r: 62 }
      };
      const s = spots[id];
      if (!s) return;
      orbit.flyTo(new THREE.Vector3(s.v[0], s.v[1], s.v[2]), s.r, 1.05);
      if (statusBeacons[id]) {
        Object.keys(statusBeacons).forEach(function (k) {
          statusBeacons[k].material.opacity = k === id ? 1 : (k === 't3' || k === 't5' ? .8 : .26);
        });
      }
    }

    return {
      orbitRef: orbit,
      update: function (dt, t) {
        smokes.children.forEach(function (sm) {
          const u = sm.userData;
          sm.position.y += u.v * dt * 60 * .016 + u.v;
          sm.position.x += u.drift * dt * .12;
          const k = (sm.position.y - u.base) / 26;
          sm.material.opacity = Math.max(0, .5 - k * .5);
          if (sm.position.y > u.base + 26) {
            sm.position.y = u.base;
            sm.position.x = -38 + (rnd() - .5) * 3;
            sm.scale.setScalar(8);
          } else {
            sm.scale.multiplyScalar(1 + dt * .05);
          }
        });
        towers.children.forEach(function (c) { if (c.update) c.update(dt, t); });
        tanks.children.forEach(function (c) { if (c.update) c.update(dt, t); });
        hydro.children.forEach(function (c) { if (c.update) c.update(dt, t); });
      },
      setLayer: setLayer,
      focus: focus,
      dispose: function () {}
    };
  }
};
