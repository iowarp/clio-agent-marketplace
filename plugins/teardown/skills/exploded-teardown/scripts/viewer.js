// Interactive exploded-view viewer for a teardown spec built by build_teardown.py.
// The page's boot script resolves the three.js imports and sets window.__TEARDOWN__.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const { meta, buffer } = window.__TEARDOWN__;
const SAMPLES = meta.parts.find((p) => p.motion)?.motion.angle.length || 1;

const MATERIALS = {
  steel: { color: '#a9adb3', metalness: 1, roughness: 0.34 },
  aluminium: { color: '#c9ccd1', metalness: 1, roughness: 0.42 },
  'cast-iron': { color: '#5b5e62', metalness: 0.75, roughness: 0.62 },
  brass: { color: '#cfa24a', metalness: 1, roughness: 0.32 },
  copper: { color: '#c4774a', metalness: 1, roughness: 0.3 },
  gold: { color: '#e3b54e', metalness: 1, roughness: 0.22 },
  chrome: { color: '#e4e6ea', metalness: 1, roughness: 0.08 },
  plastic: { color: '#3a3f45', metalness: 0, roughness: 0.48, clearcoat: 0.15 },
  rubber: { color: '#232527', metalness: 0, roughness: 0.88 },
  glass: { color: '#dfeef2', metalness: 0, roughness: 0.04, transmission: 1, thickness: 2, ior: 1.5 },
  pcb: { color: '#1f6b45', metalness: 0.05, roughness: 0.5 },
  ceramic: { color: '#efece4', metalness: 0, roughness: 0.3, clearcoat: 0.4 },
  wood: { color: '#a87a4f', metalness: 0, roughness: 0.7 },
  painted: { color: '#7d8a96', metalness: 0.1, roughness: 0.4, clearcoat: 0.3 },
};

// ---------- page chrome ----------
const $ = (tag, cls, parent, text) => {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  if (parent) parent.appendChild(el);
  return el;
};
document.getElementById('td-loading')?.remove();
document.documentElement.style.setProperty('--td-accent', meta.accent);
document.documentElement.style.setProperty('--td-bg', meta.background);
const app = $('div', 'td-app', document.body);
const stage = $('div', 'td-stage', app);
const header = $('header', 'td-header', app);
$('div', 'td-eyebrow', header, 'Teardown · exploded view');
$('h1', 'td-title', header, meta.title);
if (meta.subtitle) $('p', 'td-subtitle', header, meta.subtitle);
const chips = $('div', 'td-chips', app);
const panel = $('aside', 'td-panel', app);
const stepCard = $('section', 'td-card td-step', panel);
const infoCard = $('section', 'td-card td-info', panel);
const listCard = $('section', 'td-card td-list', panel);
const bar = $('div', 'td-bar', app);
const footer = $('footer', 'td-footer', app);
const overlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
overlay.setAttribute('class', 'td-leaders');
app.appendChild(overlay);
const labelLayer = $('div', 'td-labels', app);
const tooltip = $('div', 'td-tooltip', app);
tooltip.hidden = true;

// ---------- renderer and scene ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping ?? THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;
stage.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(meta.background);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.85;

const root = new THREE.Group();
root.rotation.x = -Math.PI / 2; // the spec is Z up; three.js is Y up
scene.add(root);

const camera = new THREE.PerspectiveCamera(32, 1, 0.5, 100000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

// ---------- parts ----------
const subsystemColor = {};
const palette = ['#2f6f73', '#7a5c99', '#b5803a', '#4d7a3a', '#9a4b4b', '#3f5f9a', '#6b6b6b'];
meta.subsystems.forEach((s, i) => { subsystemColor[s.id] = s.color || palette[i % palette.length]; });

const parts = meta.parts.map((p) => {
  const g = new THREE.BufferGeometry();
  const n = p.mesh.vertices;
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buffer, p.mesh.positions, n * 3), 3));
  g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(buffer, p.mesh.normals, n * 3), 3, true));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer, p.mesh.indices, p.mesh.triangles * 3), 1));
  g.computeBoundingBox();
  g.computeBoundingSphere();
  const preset = MATERIALS[p.material] || MATERIALS.plastic;
  const color = p.color || (p.accent ? meta.accent : preset.color);
  const material = new THREE.MeshPhysicalMaterial({ ...preset, color, side: THREE.FrontSide });
  const mesh = new THREE.Mesh(g, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(g, 32),
    new THREE.LineBasicMaterial({ color: '#1d2125', transparent: true, opacity: 0.28 }),
  );
  mesh.add(edges);
  const motionNode = new THREE.Group();
  motionNode.add(mesh);
  const explodeNode = new THREE.Group();
  explodeNode.add(motionNode);
  root.add(explodeNode);
  const centre = g.boundingBox.getCenter(new THREE.Vector3());
  mesh.userData.part = p.id;
  return { spec: p, mesh, edges, material, motionNode, explodeNode, centre, baseColor: new THREE.Color(color), baseOpacity: preset.transmission ? 0.6 : 1 };
});
const byId = Object.fromEntries(parts.map((p) => [p.spec.id, p]));

// ---------- state ----------
const input = meta.input;
const state = {
  explode: 0, explodeTarget: 0, input: input ? input.default : 0, inputTarget: null,
  playing: false, step: -1, tour: false, xray: false, section: false, labels: false,
  hidden: new Set(), focus: new Set(), selected: null, ui: true, edges: true,
};

function stageOffset(p, e) {
  const local = Math.min(1, Math.max(0, e * meta.stages - p.explode.order));
  const s = local * local * (3 - 2 * local);
  const d = p.explode.distance * s;
  return [p.explode.direction[0] * d, p.explode.direction[1] * d, p.explode.direction[2] * d];
}

function sampleMotion(m, u) {
  const span = input.max - input.min;
  let t = (u - input.min) / span;
  if (input.periodic) t = ((t % 1) + 1) % 1;
  t = Math.min(1, Math.max(0, t)) * (SAMPLES - 1);
  const i = Math.min(SAMPLES - 2, Math.floor(t));
  const f = t - i;
  const lerp = (a, b) => a + (b - a) * f;
  return {
    angle: lerp(m.angle[i], m.angle[i + 1]),
    translate: [0, 1, 2].map((k) => lerp(m.translate[i][k], m.translate[i + 1][k])),
  };
}

const axisVec = new THREE.Vector3();
function place() {
  for (const p of parts) {
    const o = stageOffset(p.spec, state.explode);
    const pv = p.spec.pivot;
    p.explodeNode.position.set(pv[0] + o[0], pv[1] + o[1], pv[2] + o[2]);
    if (p.spec.motion && input) {
      const m = sampleMotion(p.spec.motion, state.input);
      axisVec.set(...p.spec.motion.axis).normalize();
      p.motionNode.quaternion.setFromAxisAngle(axisVec, THREE.MathUtils.degToRad(m.angle));
      p.motionNode.position.set(...m.translate);
    }
  }
}

// ---------- framing, light and ground ----------
function assemblyBox(e) {
  const saved = state.explode;
  state.explode = e;
  place();
  root.updateMatrixWorld(true);
  const box = new THREE.Box3();
  for (const p of parts) if (!state.hidden.has(p.spec.id)) box.expandByObject(p.mesh);
  state.explode = saved;
  place();
  return box.isEmpty() ? new THREE.Box3(new THREE.Vector3(-1, -1, -1), new THREE.Vector3(1, 1, 1)) : box;
}
const fullBox = assemblyBox(1).union(assemblyBox(0));
const size = fullBox.getSize(new THREE.Vector3());
const radius = Math.max(size.length() / 2, 1);

const key = new THREE.DirectionalLight('#fff4e8', 2.2);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.bias = -0.0004;
key.shadow.normalBias = radius * 0.002;
const sc = key.shadow.camera;
sc.left = sc.bottom = -radius * 1.4;
sc.right = sc.top = radius * 1.4;
sc.near = radius * 0.1;
sc.far = radius * 8;
scene.add(key, key.target);
const rim = new THREE.DirectionalLight('#dbe8ff', 0.7);
scene.add(rim);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(radius * 12, radius * 12), new THREE.ShadowMaterial({ opacity: 0.16 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);
const centre = fullBox.getCenter(new THREE.Vector3());
ground.position.set(centre.x, fullBox.min.y - radius * 0.02, centre.z);
key.position.set(centre.x - radius * 1.2, centre.y + radius * 3, centre.z + radius * 1.6);
key.target.position.copy(centre);
rim.position.set(centre.x + radius * 2, centre.y + radius, centre.z - radius * 2.5);

const VIEWS = { iso: [1, -1.45, 0.95], front: [0, -1, 0.12], side: [1, 0, 0.12], top: [0.001, -0.02, 1], back: [-0.8, 1.2, 0.6] };
const camDir = meta.camera && Array.isArray(meta.camera.direction) ? meta.camera.direction : VIEWS[meta.camera && meta.camera.view] || VIEWS.iso;
let fly = null;
function viewTarget(name) {
  const d = Array.isArray(name) ? name : VIEWS[name] || camDir;
  const dir = new THREE.Vector3(d[0], d[2], -d[1]).normalize(); // Z up to Y up
  const box = assemblyBox(Math.max(state.explodeTarget, 0.0001));
  const c = box.getCenter(new THREE.Vector3());
  const r = Math.max(box.getSize(new THREE.Vector3()).length() / 2, 1);
  const fov = THREE.MathUtils.degToRad(camera.fov);
  const fit = Math.max(r / Math.sin(fov / 2), r / Math.sin(Math.atan(Math.tan(fov / 2) * camera.aspect))) * 0.92;
  return { pos: c.clone().add(dir.multiplyScalar(fit)), target: c };
}
function setView(name, instant = false) {
  const t = viewTarget(name);
  if (instant) { camera.position.copy(t.pos); controls.target.copy(t.target); fly = null; }
  else fly = { from: camera.position.clone(), fromT: controls.target.clone(), ...t, t: 0 };
}

// ---------- look: x-ray, focus, section, visibility ----------
const sectionPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), centre.x);
const anyCutaway = parts.some((p) => p.spec.cutaway);
function applyLook() {
  const focus = new Set(state.focus);
  if (state.selected) focus.add(state.selected);
  for (const p of parts) {
    const id = p.spec.id;
    const visible = !state.hidden.has(p.spec.subsystem) && !state.hidden.has(id);
    p.explodeNode.visible = visible;
    const focused = focus.size === 0 || focus.has(id);
    const ghost = state.xray ? !focus.has(id) : !focused;
    const m = p.material;
    const opacity = ghost ? (state.xray ? 0.14 : 0.22) : p.baseOpacity;
    m.transparent = opacity < 1;
    m.opacity = opacity;
    m.depthWrite = opacity >= 1;
    const cut = state.section && (!anyCutaway || p.spec.cutaway);
    m.clippingPlanes = cut ? [sectionPlane] : [];
    m.side = cut || ghost ? THREE.DoubleSide : THREE.FrontSide;
    m.emissive.set(id === hovered ? '#3a2a20' : '#000000');
    m.needsUpdate = true;
    p.edges.visible = state.edges;
    p.edges.material.opacity = ghost ? 0.1 : 0.28;
    p.edges.material.clippingPlanes = m.clippingPlanes;
    p.mesh.castShadow = !ghost;
  }
  renderList();
  renderInfo();
  renderChips();
  syncBar();
}

// ---------- panels ----------
function renderChips() {
  chips.replaceChildren();
  if (meta.subsystems.length < 2) return;
  for (const s of meta.subsystems) {
    const b = $('button', 'td-chip' + (state.hidden.has(s.id) ? ' off' : ''), chips);
    $('span', 'td-swatch', b).style.background = subsystemColor[s.id];
    b.append(s.name);
    b.title = 'Click to show or hide; double-click to see only this';
    b.onclick = () => { state.hidden.has(s.id) ? state.hidden.delete(s.id) : state.hidden.add(s.id); applyLook(); };
    b.ondblclick = () => {
      state.hidden = new Set(meta.subsystems.filter((x) => x.id !== s.id).map((x) => x.id));
      applyLook();
    };
  }
}
function renderList() {
  listCard.replaceChildren();
  $('div', 'td-label', listCard, `Parts · ${parts.length}`);
  const list = $('div', 'td-parts', listCard);
  for (const s of meta.subsystems) {
    const members = parts.filter((p) => p.spec.subsystem === s.id);
    if (!members.length) continue;
    const head = $('div', 'td-group', list);
    $('span', 'td-swatch', head).style.background = subsystemColor[s.id];
    head.append(s.name);
    for (const p of members) {
      const row = $('button', 'td-part' + (state.selected === p.spec.id ? ' on' : ''), list, p.spec.name);
      row.onclick = () => select(state.selected === p.spec.id ? null : p.spec.id);
      row.onmouseenter = () => hover(p.spec.id);
      row.onmouseleave = () => hover(null);
    }
  }
}
function renderInfo() {
  infoCard.replaceChildren();
  const p = state.selected && byId[state.selected];
  infoCard.hidden = !p;
  if (!p) return;
  const sub = meta.subsystems.find((s) => s.id === p.spec.subsystem);
  $('div', 'td-label', infoCard, `${sub ? sub.name : ''} · ${p.spec.material}`);
  $('h3', 'td-info-title', infoCard, p.spec.name);
  if (p.spec.note) $('p', 'td-text', infoCard, p.spec.note);
  const close = $('button', 'td-btn td-small', infoCard, 'Close');
  close.onclick = () => select(null);
}
function renderStep() {
  stepCard.replaceChildren();
  const steps = meta.steps;
  if (!steps.length) {
    $('div', 'td-label', stepCard, 'How it works');
    $('p', 'td-text', stepCard, meta.summary || 'Drag the explode slider to take it apart. Click a part to read what it does.');
  } else {
    const i = Math.max(0, state.step);
    const s = steps[i];
    $('div', 'td-label', stepCard, state.step < 0 ? `Overview · ${steps.length} steps` : `${String(i + 1).padStart(2, '0')} / ${String(steps.length).padStart(2, '0')}`);
    $('h2', 'td-step-title', stepCard, state.step < 0 ? meta.title : s.title);
    $('p', 'td-text', stepCard, state.step < 0 ? meta.summary || s.text : s.text);
    const row = $('div', 'td-row', stepCard);
    const prev = $('button', 'td-btn', row, 'Back');
    prev.onclick = () => goStep(Math.max(0, state.step - 1));
    const next = $('button', 'td-btn td-primary', row, state.step < 0 ? 'Start the tour' : 'Next');
    next.onclick = () => goStep((state.step + 1) % steps.length);
    const tour = $('button', 'td-btn' + (state.tour ? ' on' : ''), row, state.tour ? 'Stop tour' : 'Auto tour');
    tour.onclick = () => { state.tour = !state.tour; tourClock = 0; if (state.tour && state.step < 0) goStep(0); renderStep(); };
  }
}
function goStep(i) {
  const s = meta.steps[i];
  if (!s) return;
  state.step = i;
  state.explodeTarget = s.explode;
  if (typeof s.input === 'number' && input) { state.inputTarget = s.input; state.playing = false; }
  state.focus = new Set(s.focus);
  state.section = s.section;
  state.selected = null;
  if (s.view) setView(s.view);
  renderStep();
  applyLook();
}

// ---------- bottom bar ----------
const explodeRow = $('label', 'td-slider', bar);
$('span', 'td-label', explodeRow, 'Assembled');
const explodeInput = $('input', '', explodeRow);
Object.assign(explodeInput, { type: 'range', min: 0, max: 1, step: 0.001, value: 0 });
$('span', 'td-label', explodeRow, 'Exploded');
explodeInput.oninput = () => { state.explodeTarget = +explodeInput.value; state.explode = state.explodeTarget; };
let inputSlider = null;
let inputValue = null;
let playBtn = null;
if (input) {
  const row = $('label', 'td-slider', bar);
  playBtn = $('button', 'td-btn td-primary', row, 'Play');
  playBtn.onclick = (ev) => { ev.preventDefault(); state.playing = !state.playing; state.inputTarget = null; syncBar(); };
  $('span', 'td-label', row, input.name);
  inputSlider = $('input', '', row);
  Object.assign(inputSlider, { type: 'range', min: input.min, max: input.max, step: (input.max - input.min) / 720, value: state.input });
  inputSlider.oninput = () => { state.playing = false; state.inputTarget = null; state.input = +inputSlider.value; syncBar(); };
  inputValue = $('span', 'td-value', row);
}
const toggles = $('div', 'td-row', bar);
const toggle = (label, keyName, title) => {
  const b = $('button', 'td-btn', toggles, label);
  b.title = title;
  b.dataset.key = keyName;
  b.onclick = () => { state[keyName] = !state[keyName]; applyLook(); };
  return b;
};
toggle('X-ray', 'xray', 'See through everything but the part in focus (X)');
toggle('Section', 'section', 'Cut the assembly open down the middle (S)');
toggle('Labels', 'labels', 'Name every part (L)');
const views = $('div', 'td-row', bar);
for (const v of ['iso', 'front', 'side', 'top']) {
  const b = $('button', 'td-btn td-small', views, v === 'iso' ? '3/4' : v[0].toUpperCase() + v.slice(1));
  b.onclick = () => setView(v);
}
const reset = $('button', 'td-btn td-small', views, 'Reset');
reset.onclick = () => {
  Object.assign(state, { explodeTarget: 0, xray: false, section: false, labels: false, step: -1, tour: false, selected: null, playing: false });
  state.focus = new Set();
  state.hidden = new Set();
  setView(camDir);
  renderStep();
  applyLook();
};
function syncBar() {
  explodeInput.value = state.explode;
  if (inputSlider) {
    inputSlider.value = state.input;
    inputValue.textContent = `${state.input.toFixed(1)} ${input.unit}`;
    playBtn.textContent = state.playing ? 'Pause' : 'Play';
  }
  for (const b of toggles.children) b.classList.toggle('on', !!state[b.dataset.key]);
}

const src = meta.source || {};
const srcText = $('span', '', footer);
if (src.name) {
  srcText.append('Dimensions: ');
  if (src.url) { const a = $('a', '', srcText, src.name); a.href = src.url; a.target = '_blank'; a.rel = 'noopener'; }
  else srcText.append(src.name);
  if (src.estimated) srcText.append(` · estimated: ${src.estimated}`);
}
const credit = $('span', '', footer, 'Built with CLIO · viewer approach after ');
const up = $('a', '', credit, 'elvarofficial/teardown');
up.href = 'https://github.com/elvarofficial/teardown';
up.target = '_blank';
credit.append(' (MIT) · three.js (MIT)');

// ---------- picking, hover, labels ----------
const ray = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let hovered = null;
function pick(ev) {
  const r = renderer.domElement.getBoundingClientRect();
  pointer.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(pointer, camera);
  const meshes = parts.filter((p) => p.explodeNode.visible && p.material.opacity > 0.5).map((p) => p.mesh);
  const hit = ray.intersectObjects(meshes, false)[0];
  return hit ? hit.object.userData.part : null;
}
function hover(id) {
  if (hovered === id) return;
  hovered = id;
  for (const p of parts) p.material.emissive.set(p.spec.id === id ? '#3a2a20' : '#000000');
}
function select(id) {
  state.selected = id;
  applyLook();
}
let downAt = null;
renderer.domElement.addEventListener('pointerdown', (ev) => { downAt = [ev.clientX, ev.clientY]; });
renderer.domElement.addEventListener('pointermove', (ev) => {
  const id = pick(ev);
  hover(id);
  tooltip.hidden = !id;
  if (id) { tooltip.textContent = byId[id].spec.name; tooltip.style.left = `${ev.clientX + 14}px`; tooltip.style.top = `${ev.clientY + 12}px`; }
});
renderer.domElement.addEventListener('pointerleave', () => { hover(null); tooltip.hidden = true; });
renderer.domElement.addEventListener('pointerup', (ev) => {
  if (downAt && Math.hypot(ev.clientX - downAt[0], ev.clientY - downAt[1]) < 5) select(pick(ev));
  downAt = null;
});

const labelEls = new Map();
const tmp = new THREE.Vector3();
function drawLabels() {
  const want = state.labels
    ? parts.filter((p) => p.explodeNode.visible)
    : parts.filter((p) => p.explodeNode.visible && (p.spec.id === state.selected || state.focus.has(p.spec.id)));
  const shown = want.length > 40 ? want.slice(0, 40) : want;
  const r = renderer.domElement.getBoundingClientRect();
  const cx = r.left + r.width / 2;
  const items = shown.map((p) => {
    tmp.copy(p.centre);
    p.mesh.localToWorld(tmp);
    tmp.project(camera);
    return { p, x: r.left + ((tmp.x + 1) / 2) * r.width, y: r.top + ((1 - tmp.y) / 2) * r.height, z: tmp.z };
  }).filter((it) => it.z < 1);
  const left = items.filter((it) => it.x < cx).sort((a, b) => a.y - b.y);
  const right = items.filter((it) => it.x >= cx).sort((a, b) => a.y - b.y);
  const lines = [];
  const used = new Set();
  for (const [side, group] of [[-1, left], [1, right]]) {
    let last = -Infinity;
    for (const it of group) {
      const ly = Math.max(it.y - 26, last + 24);
      last = ly;
      const lx = it.x + side * 70;
      let el = labelEls.get(it.p.spec.id);
      if (!el) { el = $('div', 'td-tag', labelLayer, it.p.spec.name); labelEls.set(it.p.spec.id, el); }
      el.style.left = `${lx}px`;
      el.style.top = `${ly}px`;
      el.style.transform = side < 0 ? 'translate(-100%, -50%)' : 'translate(0, -50%)';
      el.hidden = false;
      used.add(it.p.spec.id);
      lines.push(`M${it.x},${it.y} L${lx},${ly}`);
    }
  }
  for (const [id, el] of labelEls) if (!used.has(id)) el.hidden = true;
  overlay.innerHTML = lines.length ? `<path d="${lines.join(' ')}" /><g>${items.map((it) => `<circle cx="${it.x}" cy="${it.y}" r="3" />`).join('')}</g>` : '';
}

// ---------- keyboard and hash state ----------
window.addEventListener('keydown', (ev) => {
  if (ev.target instanceof HTMLInputElement && ev.key !== ' ') return;
  if (ev.key === ' ' && input) { ev.preventDefault(); state.playing = !state.playing; syncBar(); }
  else if (ev.key === 'e' || ev.key === 'E') state.explodeTarget = state.explodeTarget > 0.5 ? 0 : 1;
  else if (ev.key === 'x' || ev.key === 'X') { state.xray = !state.xray; applyLook(); }
  else if (ev.key === 's' || ev.key === 'S') { state.section = !state.section; applyLook(); }
  else if (ev.key === 'l' || ev.key === 'L') { state.labels = !state.labels; applyLook(); }
  else if (ev.key === 'ArrowRight' && meta.steps.length) goStep((state.step + 1) % meta.steps.length);
  else if (ev.key === 'ArrowLeft' && meta.steps.length) goStep(Math.max(0, state.step - 1));
});

function applyState(params) {
  const num = (k) => (params.has(k) && params.get(k) !== '' && !Number.isNaN(+params.get(k)) ? +params.get(k) : null);
  const flag = (k) => params.has(k) && params.get(k) !== '0' && params.get(k) !== 'false';
  if (num('step') !== null) goStep(Math.round(num('step')) - 1);
  if (num('explode') !== null) { state.explodeTarget = Math.min(1, Math.max(0, num('explode'))); state.explode = state.explodeTarget; }
  if (num('input') !== null && input) { state.input = num('input'); state.inputTarget = null; }
  for (const k of ['xray', 'section', 'labels', 'edges']) if (params.has(k)) state[k] = flag(k);
  if (params.has('play')) state.playing = flag('play');
  if (params.has('tour')) { state.tour = flag('tour'); if (state.tour && state.step < 0) goStep(0); }
  if (params.has('part')) state.selected = byId[params.get('part')] ? params.get('part') : null;
  if (params.has('hide')) state.hidden = new Set(params.get('hide').split(',').filter(Boolean));
  if (params.has('ui')) { state.ui = flag('ui'); app.classList.toggle('td-clean', !state.ui); }
  place();
  setView(params.get('view') || camDir, true);
  renderStep();
  applyLook();
}
window.addEventListener('hashchange', () => applyState(new URLSearchParams(location.hash.slice(1))));

window.teardown = {
  set(values) { applyState(new URLSearchParams(Object.entries(values).map(([k, v]) => [k, String(v)]))); },
  state() { return { explode: state.explode, input: state.input, step: state.step + 1, xray: state.xray, section: state.section, labels: state.labels, selected: state.selected }; },
  parts: meta.parts.map((p) => ({ id: p.id, name: p.name, subsystem: p.subsystem })),
};

// ---------- loop ----------
function resize() {
  const w = stage.clientWidth || window.innerWidth;
  const h = stage.clientHeight || window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();
applyState(new URLSearchParams(location.hash.slice(1)));

let lastTime = performance.now();
let tourClock = 0;
let frames = 0;
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
renderer.setAnimationLoop((now) => {
  const dt = Math.min(0.05, (now - lastTime) / 1000);
  lastTime = now;
  const k = 1 - Math.exp(-dt * 6);
  if (Math.abs(state.explodeTarget - state.explode) > 1e-4) state.explode += (state.explodeTarget - state.explode) * k;
  else state.explode = state.explodeTarget;
  if (input) {
    const span = input.max - input.min;
    if (state.playing) {
      state.input += (span / input.seconds) * dt;
      if (state.input > input.max) state.input = input.periodic ? input.min + ((state.input - input.min) % span) : input.max;
      if (!input.periodic && state.input >= input.max) state.playing = false;
    } else if (state.inputTarget !== null) {
      state.input += (state.inputTarget - state.input) * k;
      if (Math.abs(state.inputTarget - state.input) < span * 1e-4) { state.input = state.inputTarget; state.inputTarget = null; }
    }
  }
  if (state.tour && meta.steps.length) {
    tourClock += dt;
    if (tourClock > 6.5) { tourClock = 0; goStep((state.step + 1) % meta.steps.length); }
  }
  if (fly) {
    fly.t = Math.min(1, fly.t + dt / 1.1);
    const e = ease(fly.t);
    camera.position.lerpVectors(fly.from, fly.pos, e);
    controls.target.lerpVectors(fly.fromT, fly.target, e);
    if (fly.t >= 1) fly = null;
  }
  place();
  controls.update();
  renderer.render(scene, camera);
  drawLabels();
  if (frames % 6 === 0) syncBar();
  frames += 1;
  if (frames === 3) document.body.dataset.ready = '1';
});
