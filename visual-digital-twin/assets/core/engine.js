/* ============================================================
   DT Engine (realistic) — 写实渲染内核（three r160 ES module）
   物理天空(Preetham) → CubeCamera 背景 + PMREM 材质级 envMap；
   PBR 三件套（构建期内联 data URI）；接触阴影；圆角几何；
   OrbitControls 封装；GLB+Draco 内联加载。
   ---- 加载协议（与 runtime.js 配合）----
   1. 本文件源码以 text/plain 内联在产物里（不触发模块加载），
      runtime 探测 CDN → 注入 importmap → 再用 Blob URL 动态 import 本模块
   2. 成功 → window.__DT_ENGINE_READY__(ctrl)；任何失败 → __DT_ENGINE_FAIL__(err)
   渲染红线（SwiftShader 实测沉淀，勿改回）：
   a. Sky mesh 只进专用 skyScene，绝不进主场景
   b. 不设 scene.environment（全局环境 uniform 令透明面片整批不渲染），
      环境反射走 PBR_MATS 材质级 envMap
   ============================================================ */

(async function () {
  try { await __main(); }
  catch (e) {
    console.error('[DT] 写实引擎加载失败：', e);
    if (window.__DT_ENGINE_FAIL__) window.__DT_ENGINE_FAIL__(String((e && e.message) || e));
  }
})();

async function __main() {
  const THREE = await import('three');
  const { Sky } = await import('three/addons/objects/Sky.js');
  const { RoundedBoxGeometry } = await import('three/addons/geometries/RoundedBoxGeometry.js');
  const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');

  const ctx = window.__DT_ENGINE_CTX__ || {};
  const CFG = ctx.cfg || {};
  const ENV = Object.assign({ timeOfDay: 'day', shadowSize: 2048 }, CFG.env || {});
  const TEX = window.__DT_TEX__ || {};

  /* ---------------- 昼夜光照预设（阳光:天空光 ≈ 5:1，勿两头都高） ---------------- */
  const TOD = {
    day: {
      elevation: 52, azimuth: 128, turbidity: 5.5, rayleigh: 1.6, mie: 0.006, mieG: 0.8,
      sun: 6.5, sunColor: 0xfff3e0, hemi: 0.28, hemiSky: 0xbcd8f5, hemiGround: 0x8a7f6a,
      amb: 0.06, exposure: 0.72, fog: 0xcfe4f5, fogDensity: 0.00042
    },
    dusk: {
      elevation: 7, azimuth: 250, turbidity: 8, rayleigh: 2.6, mie: 0.012, mieG: 0.85,
      sun: 3.2, sunColor: 0xffb070, hemi: 0.16, hemiSky: 0x6f7fa8, hemiGround: 0x4a3f38,
      amb: 0.05, exposure: 0.62, fog: 0xd9a986, fogDensity: 0.00055
    }
  };

  /* ---------------- 渲染器 ---------------- */
  const canvas = ctx.canvas, container = ctx.container;
  const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = TOD[ENV.timeOfDay].exposure;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.5, 6000);

  /* ---------------- 物理天空（专用 skyScene → cube RT → 背景 + PMREM） ---------------- */
  const skyScene = new THREE.Scene();
  const skyDome = new Sky();
  skyDome.scale.setScalar(4000);
  skyScene.add(skyDome);
  const skyCubeRT = new THREE.WebGLCubeRenderTarget(256);
  const skyCubeCam = new THREE.CubeCamera(0.1, 100000, skyCubeRT);
  const pmrem = new THREE.PMREMGenerator(renderer);
  let skyEnvMap = null, skyEnvRT = null;
  const sunDir = new THREE.Vector3();
  const PBR_MATS = [];
  const TOD_HOOKS = [];

  function applyEnvMaps() {
    for (const m of PBR_MATS) {
      if (!m.isMeshStandardMaterial && !m.isMeshPhysicalMaterial) continue;
      if (m.userData.envMapIntensity != null) m.envMapIntensity = m.userData.envMapIntensity;
      else if (m.envMapIntensity == null) m.envMapIntensity = 0.5;
      m.envMap = skyEnvMap;
      m.needsUpdate = true;
    }
  }

  function refreshSky() {
    const P = TOD[timeOfDay] || TOD.day;
    const u = skyDome.material.uniforms;
    u.turbidity.value = P.turbidity;
    u.rayleigh.value = P.rayleigh;
    u.mieCoefficient.value = P.mie;
    u.mieDirectionalG.value = P.mieG;
    const phi = THREE.MathUtils.degToRad(90 - P.elevation);
    const theta = THREE.MathUtils.degToRad(P.azimuth);
    sunDir.setFromSphericalCoords(1, phi, theta);
    u.sunPosition.value.copy(sunDir);
    skyCubeCam.update(renderer, skyScene);
    scene.background = skyCubeRT.texture;
    const rt = pmrem.fromScene(skyScene, 0, 0.1, 100000);
    if (skyEnvRT) skyEnvRT.dispose();
    skyEnvRT = rt; skyEnvMap = rt.texture;
    applyEnvMaps();
  }

  /* ---------------- 光照 ---------------- */
  const sun = new THREE.DirectionalLight(0xfff3e0, TOD.day.sun);
  sun.castShadow = true;
  sun.shadow.mapSize.set(ENV.shadowSize, ENV.shadowSize);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.03;
  scene.add(sun); scene.add(sun.target);
  const hemi = new THREE.HemisphereLight(0xbcd8f5, 0x8a7f6a, TOD.day.hemi);
  scene.add(hemi);
  const amb = new THREE.AmbientLight(0xffffff, TOD.day.amb);
  scene.add(amb);
  const fill = new THREE.DirectionalLight(0xbdd4ee, 0.22);
  fill.position.set(-120, 80, -60);
  scene.add(fill);

  function applyLights() {
    const P = TOD[timeOfDay] || TOD.day;
    sun.intensity = P.sun; sun.color.setHex(P.sunColor);
    sun.position.copy(sunDir).multiplyScalar(600);
    hemi.intensity = P.hemi; hemi.color.setHex(P.hemiSky); hemi.groundColor.setHex(P.hemiGround);
    amb.intensity = P.amb;
    renderer.toneMappingExposure = P.exposure;
    scene.fog = new THREE.FogExp2(P.fog, P.fogDensity);
  }

  let timeOfDay = TOD[ENV.timeOfDay] ? ENV.timeOfDay : 'day';
  function setTimeOfDay(t) {
    if (!TOD[t]) return;
    timeOfDay = t;
    refreshSky(); applyLights();
    TOD_HOOKS.forEach(function (fn) { try { fn(t); } catch (e) { console.warn(e); } });
  }

  /* ---------------- 阴影相机收紧 ---------------- */
  function tuneShadow() {
    const box = new THREE.Box3().setFromObject(root);
    if (box.isEmpty()) return;
    const c = box.getCenter(new THREE.Vector3());
    const radius = box.getSize(new THREE.Vector3()).length() * 0.5;
    sun.position.copy(c).addScaledVector(sunDir, Math.max(300, radius * 2.2));
    sun.target.position.copy(c);
    const s = Math.max(120, radius * 1.05);
    const cam = sun.shadow.camera;
    cam.left = -s; cam.right = s; cam.top = s; cam.bottom = -s;
    cam.near = 10; cam.far = Math.max(1200, radius * 6);
    cam.updateProjectionMatrix();
    if (radius > 150 && ENV.shadowSize <= 2048) {
      sun.shadow.mapSize.set(4096, 4096);
      if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; }
    }
  }

  /* ---------------- 材质 ---------------- */
  function mat(o) {
    o = o || {};
    const m = new THREE.MeshStandardMaterial(o);
    if (o.envMapIntensity != null) m.userData.envMapIntensity = o.envMapIntensity;
    PBR_MATS.push(m);
    if (skyEnvMap) { m.envMap = skyEnvMap; if (m.envMapIntensity == null) m.envMapIntensity = 0.5; }
    return m;
  }

  const texLoader = new THREE.TextureLoader();
  const texCache = {};
  function tex(name, rx, ry, srgb) {
    const key = name + '|' + (rx || 1) + '|' + (ry || 1) + '|' + (srgb ? 1 : 0);
    if (texCache[key]) return texCache[key];
    const t = texLoader.load(TEX[name]);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(rx || 1, ry || 1);
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    texCache[key] = t;
    return t;
  }

  /** PBR 三件套：TEX 里 name 对应 albedo data URI（normal/rough 由构建期派生内联） */
  function texMat(name, o) {
    o = o || {};
    const m = new THREE.MeshStandardMaterial({
      color: o.color != null ? o.color : 0xffffff,
      roughness: 1, metalness: o.metalness || 0
    });
    const rx = o.repeatX || 1, ry = o.repeatY || 1;
    if (TEX[name]) { m.map = tex(name, rx, ry, true); }
    if (TEX[name + '-normal']) {
      m.normalMap = tex(name + '-normal', rx, ry, false);
      const ns = o.normalScale != null ? o.normalScale : 1;
      m.normalScale.set(ns, ns);
    }
    if (TEX[name + '-rough']) {
      m.roughnessMap = tex(name + '-rough', rx, ry, false);
      m.roughness = Math.min(1, (o.roughness != null ? o.roughness : 1) * 2);
    } else if (o.roughness != null) {
      m.roughness = o.roughness;
    }
    if (o.emissive != null) { m.emissive = new THREE.Color(o.emissive); m.emissiveIntensity = o.emissiveIntensity != null ? o.emissiveIntensity : 1; }
    if (o.envMapIntensity != null) m.userData.envMapIntensity = o.envMapIntensity;
    PBR_MATS.push(m);
    if (skyEnvMap) { m.envMap = skyEnvMap; if (m.envMapIntensity == null) m.envMapIntensity = 0.5; }
    return m;
  }

  /* ---------------- 几何 ---------------- */
  function rbox(w, h, d, r, seg) {
    const rr = Math.max(0.001, Math.min(r == null ? 0.12 : r, Math.min(w, h, d) / 2 - 0.001));
    return new RoundedBoxGeometry(w, h, d, seg || 2, rr);
  }

  /** 接触阴影：顶点色 alpha 渐变（SwiftShader 也认） */
  function contactShadow(w, d) {
    const geo = new THREE.PlaneGeometry(1, 1, 12, 12);
    const pos = geo.attributes.position, n = pos.count;
    const col = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
      const x = pos.getX(i), y = pos.getY(i);
      const r = Math.min(1, Math.sqrt(x * x + y * y) * 2);
      col[i * 4] = 0; col[i * 4 + 1] = 0; col[i * 4 + 2] = 0; col[i * 4 + 3] = Math.pow(1 - r, 1.6);
    }
    geo.setAttribute('color', new THREE.BufferAttribute(col, 4));
    const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
      transparent: true, vertexColors: true, depthWrite: false, opacity: 0.85
    }));
    m.rotation.x = -Math.PI / 2;
    m.scale.set(Math.max(1.5, w * 1.15), Math.max(1.5, d * 1.15), 1);
    m.renderOrder = 3;
    return m;
  }

  /* ---------------- 标签 / 光效 ---------------- */
  function label(text, opt) {
    opt = opt || {};
    const fs = opt.fontSize || 26, pad = opt.pad || 12;
    const cv = document.createElement('canvas');
    let c2 = cv.getContext('2d');
    c2.font = '600 ' + fs + 'px "PingFang SC","Microsoft YaHei",system-ui,sans-serif';
    const tw = Math.ceil(c2.measureText(text).width);
    cv.width = Math.ceil(tw + pad * 4); cv.height = Math.ceil(fs * 2.1);
    c2 = cv.getContext('2d');
    const r = 6, w = cv.width, h = cv.height;
    c2.beginPath();
    c2.moveTo(1 + r, 1); c2.lineTo(w - 1 - r, 1); c2.quadraticCurveTo(w - 1, 1, w - 1, 1 + r);
    c2.lineTo(w - 1, h - 1 - r); c2.quadraticCurveTo(w - 1, h - 1, w - 1 - r, h - 1);
    c2.lineTo(1 + r, h - 1); c2.quadraticCurveTo(1, h - 1, 1, h - 1 - r);
    c2.lineTo(1, 1 + r); c2.quadraticCurveTo(1, 1, 1 + r, 1); c2.closePath();
    c2.fillStyle = opt.bg || 'rgba(10,18,30,.78)';
    c2.fill();
    c2.strokeStyle = opt.border || 'rgba(255,255,255,.35)'; c2.lineWidth = 1.5; c2.stroke();
    c2.fillStyle = opt.accent || '#5eead4';
    c2.fillRect(1, h * .24, 3, h * .52);
    c2.font = '600 ' + fs + 'px "PingFang SC","Microsoft YaHei",system-ui,sans-serif';
    c2.fillStyle = opt.color || '#f2f7fb';
    c2.textAlign = 'center'; c2.textBaseline = 'middle';
    c2.fillText(text, w / 2, h / 2 + 1);
    const t = new THREE.CanvasTexture(cv);
    t.colorSpace = THREE.SRGBColorSpace;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
    const scale = opt.scale || 1;
    sp.scale.set(cv.width / 110 * scale, cv.height / 110 * scale, 1);
    return sp;
  }

  /** 竖直光柱（区标）：低饱和渐变，写实场景下做克制的定位标记 */
  function beaconPillar(radius, height, color) {
    const cv = document.createElement('canvas'); cv.width = 2; cv.height = 128;
    const c2 = cv.getContext('2d');
    const g = c2.createLinearGradient(0, 0, 0, 128);
    const col = new THREE.Color(color);
    const rgba = function (a) { return 'rgba(' + Math.round(col.r * 255) + ',' + Math.round(col.g * 255) + ',' + Math.round(col.b * 255) + ',' + a + ')'; };
    g.addColorStop(0, rgba(.0)); g.addColorStop(.15, rgba(.55)); g.addColorStop(1, rgba(.06));
    c2.fillStyle = g; c2.fillRect(0, 0, 2, 128);
    const t = new THREE.CanvasTexture(cv);
    t.colorSpace = THREE.SRGBColorSpace;
    const m = new THREE.Mesh(
      new THREE.CylinderGeometry(radius, radius, height, 12, 1, true),
      new THREE.MeshBasicMaterial({ map: t, transparent: true, opacity: .8, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending })
    );
    m.update = function (dt, tm) { m.material.opacity = .55 + Math.abs(Math.sin(tm * .8)) * .3; };
    return m;
  }

  /** 沿曲线的低饱和流动光点（数据航线），写实场景克制使用 */
  function flowLine(curve, opt) {
    opt = opt || {};
    const count = opt.count || 2, size = opt.size || 1.6, speed = opt.speed || .12;
    const grp = new THREE.Group();
    const geo = new THREE.SphereGeometry(size * .3, 8, 8);
    const m = new THREE.MeshBasicMaterial({ color: opt.color || 0xbfe4ff, transparent: true, opacity: .85, depthWrite: false });
    const items = [];
    for (let i = 0; i < count; i++) {
      const mesh = new THREE.Mesh(geo, m);
      grp.add(mesh); items.push({ mesh: mesh, t: i / count, spd: speed });
    }
    grp.update = function (dt) {
      for (let i = 0; i < items.length; i++) {
        const it = items[i];
        it.t += dt * it.spd; if (it.t > 1) it.t -= 1;
        it.mesh.position.copy(curve.getPointAt(Math.max(.0001, Math.min(.9999, it.t))));
      }
    };
    return grp;
  }

  /** 扩散扫描环（港口/园区扫描），普通混合低透明度 */
  function pulseRing(radius, color, opt) {
    opt = opt || {};
    const grp = new THREE.Group();
    const rings = [];
    for (let i = 0; i < (opt.count || 2); i++) {
      const mesh = new THREE.Mesh(
        new THREE.RingGeometry(radius * .96, radius, 72),
        new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: .3, side: THREE.DoubleSide, depthWrite: false })
      );
      mesh.rotation.x = -Math.PI / 2;
      grp.add(mesh); rings.push({ m: mesh, t: i / (opt.count || 2) });
    }
    grp.update = function (dt) {
      for (const r of rings) {
        r.t += dt * (opt.speed || .2); if (r.t > 1) r.t -= 1;
        const s = .12 + r.t * 1.5;
        r.m.scale.set(s, s, s);
        r.m.material.opacity = .32 * (1 - r.t);
      }
    };
    return grp;
  }

  /* ---------------- 轨道控制器封装（官方 OrbitControls + flyTo 补间） ---------------- */
  function orbit(camera, dom, o) {
    o = o || {};
    const controls = new OrbitControls(camera, dom);
    controls.target.copy(o.target || new THREE.Vector3());
    controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.autoRotate = o.auto !== false;
    controls.autoRotateSpeed = (o.speed || 0.045) * 9.55;
    controls.minDistance = o.minDistance || 20;
    controls.maxDistance = o.maxDistance || 1200;
    controls.maxPolarAngle = o.maxPolar != null ? o.maxPolar : 1.5;
    controls.minPolarAngle = o.minPolar != null ? o.minPolar : 0.1;
    dom.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    let tween = null;
    const home = {
      pos: camera.position.clone(), target: (o.target || new THREE.Vector3()).clone()
    };
    const st = {
      controls: controls,
      update: function (dt) {
        if (tween) {
          tween.k = Math.min(1, tween.k + dt / tween.dur);
          const e = tween.k < .5 ? 2 * tween.k * tween.k : 1 - Math.pow(-2 * tween.k + 2, 2) / 2;
          camera.position.lerpVectors(tween.p0, tween.p1, e);
          controls.target.lerpVectors(tween.t0, tween.t1, e);
          if (tween.k >= 1) tween = null;
        }
        controls.update();
      },
      setAuto: function (on) { controls.autoRotate = on; },
      flyTo: function (v, radius, phi, theta) {
        controls.autoRotate = false;
        const sph = new THREE.Spherical(radius || camera.position.distanceTo(v), phi != null ? phi : 1.05, theta != null ? theta : Math.random() * 6.28);
        const p1 = new THREE.Vector3().setFromSpherical(sph).add(v);
        tween = { k: 0, dur: 1.4, p0: camera.position.clone(), p1: p1, t0: controls.target.clone(), t1: v.clone() };
      },
      reset: function () {
        controls.autoRotate = o.auto !== false;
        tween = { k: 0, dur: 1.2, p0: camera.position.clone(), p1: home.pos.clone(), t0: controls.target.clone(), t1: home.target.clone() };
      },
      dispose: function () { controls.dispose(); }
    };
    return st;
  }

  /* ---------------- 射线拾取 ---------------- */
  function picker(renderer, camera, dom) {
    const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), last = { x: -1, y: -1 };
    let targets = [];
    return {
      setTargets: function (t) { targets = t; },
      onMove: function (e) {
        const r = dom.getBoundingClientRect();
        last.x = e.clientX - r.left; last.y = e.clientY - r.top;
        mouse.x = (last.x / r.width) * 2 - 1;
        mouse.y = -(last.y / r.height) * 2 + 1;
      },
      pick: function () {
        if (!targets.length) return null;
        ray.setFromCamera(mouse, camera);
        const hits = ray.intersectObjects(targets, false);
        for (const h of hits) {
          if (h.object.visible && (h.object.userData.data || h.object.userData.focusId))
            return { obj: h.object, data: h.object.userData.data, point: h.point };
        }
        return null;
      },
      screen: function () { return last; }
    };
  }

  /* ---------------- GLB 模型（内联 data URI + Draco 内联 decoder） ---------------- */
  async function loadModels(list, onEach) {
    if (!list || !list.length) return;
    const URIS = window.__DT_MODELS__ || {};
    const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
    const manager = new THREE.LoadingManager();
    const gltfLoader = new GLTFLoader(manager);
    const DRACO = window.__DT_DRACO__;
    if (DRACO && DRACO.wrapper && DRACO.wasm) {
      const { DRACOLoader } = await import('three/addons/loaders/DRACOLoader.js');
      const draco = new DRACOLoader(manager);
      draco.setDecoderConfig({ type: 'js' });
      const blobUrls = {};
      manager.setURLModifier(function (url) {
        if (url === 'draco_wasm_wrapper.js') return blobUrls.wrapper || url;
        if (url === 'draco_decoder.wasm' || url === 'draco_decoder.js') return blobUrls.decoder || url;
        return url;
      });
      blobUrls.wrapper = URL.createObjectURL(new Blob([DRACO.wrapper], { type: 'application/javascript' }));
      blobUrls.decoder = URL.createObjectURL(new Blob([DRACO.wasm], { type: 'application/wasm' }));
      gltfLoader.setDRACOLoader(draco);
    }
    for (const def of list) {
      try {
        const uri = URIS[def.url] || def.url;
        const gltf = await gltfLoader.loadAsync(uri);
        const obj = gltf.scene;
        obj.traverse(function (o) {
          if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; }
        });
        const g = new THREE.Group();
        const s = def.scale != null ? def.scale : 1;
        obj.scale.setScalar(s);
        if (def.rotation) obj.rotation.y = THREE.MathUtils.degToRad(def.rotation);
        g.add(obj);
        if (def.position) g.position.set(def.position[0], def.position[1] || 0, def.position[2] || 0);
        const box = new THREE.Box3().setFromObject(obj);
        const size = box.getSize(new THREE.Vector3());
        const cs = contactShadow(Math.max(size.x, 2), Math.max(size.z, 2));
        cs.position.y = -g.position.y + 0.1;
        g.add(cs);
        if (def.label !== false && def.name) {
          const lb = label(def.name, { scale: .9 });
          lb.position.set(0, size.y + 3, 0);
          g.add(lb);
        }
        g.userData.data = { name: def.name, desc: def.desc || '', metrics: def.metrics || [] };
        g.userData.focusId = def.id;
        root.add(g);
        if (onEach) onEach(g, def);
      } catch (e) {
        console.warn('[DT] 模型加载失败，回退占位：', def.url, e);
        const fb = def.fallback || { type: 'box', size: [4, 4, 4] };
        const sz = fb.size || [4, 4, 4];
        const m = new THREE.Mesh(rbox(sz[0], sz[1], sz[2], .15), mat({ color: 0x8b93a1, roughness: .85 }));
        m.position.set(def.position ? def.position[0] : 0, (def.position ? def.position[1] || 0 : 0) + sz[1] / 2, def.position ? def.position[2] || 0 : 0);
        m.castShadow = m.receiveShadow = true;
        m.userData.data = { name: def.name, desc: '占位体（模型加载失败）', metrics: [] };
        m.userData.focusId = def.id;
        root.add(m);
        if (onEach) onEach(m, def);
      }
    }
  }

  /* ---------------- 场景根 / 尺寸 ---------------- */
  const root = new THREE.Group();
  scene.add(root);

  /* ---------------- 引擎 API ---------------- */
  const E = {
    THREE: THREE, renderer: renderer, scene: scene, camera: camera, root: root,
    canvas: canvas, container: container, cfg: CFG, bus: ctx.bus, toast: ctx.toast,
    timeOfDay: timeOfDay, setTimeOfDay: setTimeOfDay, onTOD: function (fn) { TOD_HOOKS.push(fn); },
    refreshSky: refreshSky, tuneShadow: tuneShadow,
    mat: mat, texMat: texMat, tex: tex,
    rbox: rbox, contactShadow: contactShadow,
    label: label, beaconPillar: beaconPillar, flowLine: flowLine, pulseRing: pulseRing,
    orbit: orbit, picker: picker, loadModels: loadModels
  };

  /* ---------------- 启动场景 ---------------- */
  const spec = window.__DT_SCENE_SPEC__;
  if (!spec) throw new Error('缺少场景 spec（window.__DT_SCENE_SPEC__）');
  camera.position.set(spec.camera.pos[0], spec.camera.pos[1], spec.camera.pos[2]);
  refreshSky(); applyLights();

  const ctrl = await spec.init(E, ctx);
  tuneShadow();

  function resize() {
    const r = canvas.getBoundingClientRect();
    if (!r.width || !r.height) return;
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / r.height;
    camera.updateProjectionMatrix();
  }
  resize();
  if (window.ResizeObserver) new ResizeObserver(resize).observe(canvas);
  window.addEventListener('resize', resize);

  const clock = new THREE.Clock();
  let raf = 0, fps = 60;
  function loop() {
    const dt = Math.min(clock.getDelta(), .05), t = clock.elapsedTime;
    fps = Math.round(fps * .92 + (1 / Math.max(dt, .001)) * .08);
    if (orbitRef) orbitRef.update(dt);
    if (ctrl && ctrl.update) ctrl.update(dt, t);
    renderer.render(scene, camera);
    raf = requestAnimationFrame(loop);
  }
  let orbitRef = ctrl && ctrl.orbitRef ? ctrl.orbitRef : null;
  raf = requestAnimationFrame(loop);

  window.__DT_MODE__ = '3d';
  window.__DT_CTRL__ = {
    stats: function () { return { fps: fps, faces: renderer.info.render.triangles }; },
    setLayer: ctrl.setLayer || function () {},
    focus: ctrl.focus || function () {},
    dispose: function () {
      cancelAnimationFrame(raf);
      if (ctrl.dispose) ctrl.dispose();
      if (orbitRef) orbitRef.dispose();
      renderer.dispose();
    }
  };
  if (window.__DT_ENGINE_READY__) window.__DT_ENGINE_READY__(window.__DT_CTRL__);
}
