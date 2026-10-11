// Interface animateur La Capsule V3 : client WebSocket du serveur admin (server.py).
"use strict";

const $ = (id) => document.getElementById(id);
const PIN_KEY = "capsule_admin_pin";
const CALIB_TARGETS = [0, 0.25, 0.5, 0.75, 1];
const CHUTE_STATES = {
  stowed: "Replié", armed: "Armé", active: "Actif", semi_deployed: "Semi-déployé",
  deployed: "Déployé", cut: "Coupé",
};

let ws = null;
let nextId = 1;
const pending = new Map();
let state = {};

// ---- Stockage du PIN (peut être indisponible : navigation privée) -------

function savedPin() {
  try { return localStorage.getItem(PIN_KEY) || ""; } catch { return ""; }
}
function storePin(pin) {
  try { pin ? localStorage.setItem(PIN_KEY, pin) : localStorage.removeItem(PIN_KEY); } catch {}
}

// ---- Connexion ------------------------------------------------------------

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    const pin = savedPin();
    if (pin) authenticate(pin); else showPin();
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "state") { applyState(msg); return; }
    const p = pending.get(msg.reply_to);
    if (p) { pending.delete(msg.reply_to); p(msg); }
  };
  ws.onclose = () => {
    for (const p of pending.values()) p({ ok: false, error: "connexion au serveur perdue" });
    pending.clear();
    applyState({ krpc: false, bridge: false });
    setTimeout(connect, 2000);
  };
}

function send(cmd, params = {}) {
  return new Promise((resolve) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      resolve({ ok: false, error: "serveur injoignable" });
      return;
    }
    const id = nextId++;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, cmd, ...params }));
  });
}

// Commande avec retour visuel : toast d'erreur, et succès si `okText`.
async function run(cmd, params, okText) {
  const r = await send(cmd, params);
  if (!r.ok) toast(r.error || "échec", true);
  else if (okText) toast(typeof okText === "function" ? okText(r) : okText);
  return r;
}

async function authenticate(pin) {
  const r = await send("auth", { pin });
  if (r.ok) {
    storePin(pin);
    $("pin-screen").hidden = true;
    loadSaves();
  } else {
    storePin("");
    showPin(r.error);
  }
}

function showPin(error = "") {
  $("pin-error").textContent = error;
  $("pin-screen").hidden = false;
  $("pin-input").value = "";
  $("pin-input").focus();
}

$("pin-form").addEventListener("submit", (e) => {
  e.preventDefault();
  authenticate($("pin-input").value.trim());
});

// ---- État ---------------------------------------------------------------

function applyState(s) {
  state = s;
  $("dot-ksp").className = "dot " + (s.krpc ? "on" : "err");
  $("dot-bridge").className = "dot " + (s.bridge ? "on" : "err");
  $("vessel").textContent = s.krpc ? (s.vessel || "Hors scène de vol") : (s.error || "KSP injoignable");

  $("btn-map").classList.toggle("active", !!s.camera_map);
  $("btn-revert").disabled = !s.can_revert;

  const navballDown = !!(s.failures && s.failures.navball);
  $("navball-state").textContent = !s.bridge ? "Capsule injoignable" : navballDown ? "EN PANNE" : "Fonctionnelle";
  const nb = $("btn-navball");
  nb.textContent = navballDown ? "RÉPARER" : "DÉCLENCHER";
  nb.classList.toggle("active", navballDown);
  nb.disabled = !s.bridge;

  renderChutes(s.parachutes || []);
}

function renderChutes(chutes) {
  const key = JSON.stringify(chutes);
  if (renderChutes.last === key) return;  // évite de recréer la liste chaque seconde
  renderChutes.last = key;
  const ul = $("chutes");
  ul.innerHTML = "";
  $("btn-chutes-all").disabled = chutes.length === 0;
  if (!chutes.length) {
    ul.innerHTML = '<li class="sub">Aucun parachute</li>';
    return;
  }
  for (const c of chutes) {
    const li = document.createElement("li");
    const label = document.createElement("div");
    label.innerHTML = `<div class="name"></div><div class="sub"></div>`;
    label.children[0].textContent = c.title;
    label.children[1].textContent = CHUTE_STATES[c.state] || c.state;
    const btn = document.createElement("button");
    btn.className = "btn danger";
    btn.textContent = "COUPER";
    btn.disabled = c.state === "cut";
    btn.onclick = () => confirmAction("COUPER LE PARACHUTE",
      `« ${c.title} » sera largué et ne pourra plus servir pendant ce vol.`,
      () => run("parachute_cut", { index: c.index }, "Parachute coupé"));
    li.append(label, btn);
    ul.append(li);
  }
}

// ---- Caméra --------------------------------------------------------------

$("btn-map").onclick = () => run("camera_map");
$("btn-cam-reset").onclick = () => run("camera_reset");
for (const b of document.querySelectorAll("[data-zoom]")) {
  b.onclick = () => run("camera_zoom", { dir: Number(b.dataset.zoom) });
}

(function joystick() {
  const pad = $("joystick"), knob = $("knob");
  const DEAD = 0.15, PERIOD_MS = 100;
  let dx = 0, dy = 0, timer = null, busy = false;

  function setFrom(ev) {
    const r = pad.getBoundingClientRect();
    const radius = r.width / 2 - 32;
    let x = ev.clientX - (r.left + r.width / 2);
    let y = ev.clientY - (r.top + r.height / 2);
    const len = Math.hypot(x, y);
    if (len > radius) { x *= radius / len; y *= radius / len; }
    knob.style.transform = `translate(${x}px, ${y}px)`;
    dx = Math.abs(x / radius) < DEAD ? 0 : x / radius;
    dy = Math.abs(y / radius) < DEAD ? 0 : -y / radius;  // haut = positif
  }

  async function tick() {
    if (busy || (!dx && !dy)) return;
    busy = true;  // pas d'accumulation si le serveur répond lentement
    await send("camera_move", { dx, dy });
    busy = false;
  }

  pad.addEventListener("pointerdown", (ev) => {
    pad.setPointerCapture(ev.pointerId);
    pad.classList.add("dragging");
    setFrom(ev);
    tick();
    timer = setInterval(tick, PERIOD_MS);
  });
  pad.addEventListener("pointermove", (ev) => { if (timer) setFrom(ev); });
  const release = () => {
    clearInterval(timer); timer = null; dx = dy = 0;
    pad.classList.remove("dragging");
    knob.style.transform = "";
  };
  pad.addEventListener("pointerup", release);
  pad.addEventListener("pointercancel", release);
})();

// ---- Science ---------------------------------------------------------------

$("btn-science").onclick = async () => {
  const btn = $("btn-science");
  btn.disabled = true;
  const r = await run("science_all");
  btn.disabled = false;
  if (!r.ok) return;
  $("science-result").textContent = r.total === 0
    ? "Aucune expérience à bord."
    : `${r.ran.length} lancée(s) sur ${r.total}` +
      (r.ran.length ? ` : ${r.ran.join(", ")}` : "") +
      (r.skipped.length ? `. Non disponibles : ${r.skipped.join(", ")}` : "");
};

// ---- Pannes ----------------------------------------------------------------

$("btn-navball").onclick = () => {
  const down = !!(state.failures && state.failures.navball);
  run("failure_set", { name: "navball", active: !down },
    down ? "Navball réparée" : "Navball en panne");
};
$("btn-chutes-all").onclick = () => confirmAction("COUPER TOUS LES PARACHUTES",
  "Tous les parachutes de la fusée seront largués pour ce vol.",
  () => run("parachute_cut", {}, (r) => `${r.cut.length} parachute(s) coupé(s)`));

// ---- Calibration -----------------------------------------------------------

const calib = { points: CALIB_TARGETS.map(() => null), timer: null };

function renderCalib() {
  const ol = $("calib-steps");
  ol.innerHTML = "";
  CALIB_TARGETS.forEach((t, i) => {
    const li = document.createElement("li");
    const pos = document.createElement("span");
    pos.className = "pos";
    pos.textContent = `${t * 100} %`;
    const val = document.createElement("span");
    val.className = "val" + (calib.points[i] !== null ? " done" : "");
    val.textContent = calib.points[i] !== null ? calib.points[i] : "----";
    const btn = document.createElement("button");
    btn.className = "btn ghost";
    btn.textContent = "CAPTURER";
    btn.onclick = async () => {
      const r = await run("calib_sample");
      if (!r.ok) return;
      calib.points[i] = r.average;
      renderCalib();
    };
    li.append(pos, val, btn);
    ol.append(li);
  });
  $("btn-calib-save").disabled = calib.points.some((p) => p === null);
}

async function pollRaw() {
  if (document.hidden || !state.bridge) return;
  const r = await send("calib_sample");
  $("calib-raw").textContent = r.ok ? String(r.live).padStart(4, "0") : "----";
}

$("btn-calib-reset").onclick = () => { calib.points = CALIB_TARGETS.map(() => null); renderCalib(); };
$("btn-calib-save").onclick = () => confirmAction("ENREGISTRER LA CALIBRATION",
  "La nouvelle table remplace l'actuelle et s'applique immédiatement à la manette.",
  async () => {
    const points = CALIB_TARGETS.map((t, i) => [t, calib.points[i]]);
    const r = await run("calib_save", { points }, "Calibration enregistrée");
    if (r.ok) $("btn-calib-reset").onclick();
  });

// Valeur brute en direct uniquement quand la section est visible à l'écran.
new IntersectionObserver((entries) => {
  const visible = entries[0].isIntersecting;
  clearInterval(calib.timer);
  calib.timer = visible ? setInterval(pollRaw, 400) : null;
}).observe($("calib-steps"));

// ---- Mission ---------------------------------------------------------------

$("btn-revert").onclick = () => confirmAction("REVENIR AU LANCEMENT",
  "La mission en cours est abandonnée et la fusée revient sur le pas de tir.",
  () => run("revert", {}, "Retour au lancement"));

async function loadSaves() {
  const r = await send("saves");
  const ul = $("saves");
  ul.innerHTML = "";
  if (!r.ok || !r.saves.length) {
    ul.innerHTML = `<li class="sub">${r.ok ? "Aucune sauvegarde trouvée (vérifier ksp.dir / save_game)" : r.error}</li>`;
    return;
  }
  for (const name of r.saves) {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.className = "name";
    label.textContent = name;
    const btn = document.createElement("button");
    btn.className = "btn danger ghost";
    btn.textContent = "CHARGER";
    btn.onclick = () => confirmAction("CHARGER LA SAUVEGARDE",
      `La mission en cours est abandonnée et « ${name} » est chargée.`,
      () => run("load_save", { name }, "Sauvegarde chargée"));
    li.append(label, btn);
    ul.append(li);
  }
}
$("btn-saves").onclick = loadSaves;

// ---- Confirmation, messages ---------------------------------------------------

function confirmAction(title, text, action) {
  $("confirm-title").textContent = title;
  $("confirm-text").textContent = text;
  $("confirm").hidden = false;
  $("confirm-yes").onclick = () => { $("confirm").hidden = true; action(); };
}
$("confirm-no").onclick = () => { $("confirm").hidden = true; };

let toastTimer = null;
function toast(text, isError = false) {
  const t = $("toast");
  t.textContent = text;
  t.className = "toast" + (isError ? " err" : "");
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, isError ? 4000 : 2000);
}

renderCalib();
connect();
