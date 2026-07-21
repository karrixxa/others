// Application orchestrator. Owns the shared store, wires the websocket to the
// renderer / inspector / charts / controls, and keeps the top bar in sync.

import { WSClient } from './websocket.js';
import { NeuronRenderer } from './renderer.js';
import { Inspector } from './inspector.js';
import { Charts } from './charts.js';
import { Controls } from './controls.js';
import { ReceptiveFields } from './receptive.js';
import { Raster } from './raster.js';
import { ChargeChart } from './charge.js';
import { WeightsChart } from './weights.js';
import { CausalStory } from './causal.js';
import { firstResponderLabel, predictionOutputStateLabel, detectPatternLabel } from './labels.js';

const api = {
  async post(path, body) {
    try {
      await fetch(path, {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (e) { console.warn('POST failed', path, e); }
  },
};

const store = {
  topology: null,
  meta: new Map(),          // id -> static meta
  weights: new Map(),       // synapse id -> current weight
  confidence: new Map(),    // synapse id -> current confidence (L2E gates)
  stateById: new Map(),     // id -> latest dynamic neuron state
  patternVectors: {},
  probeVectors: {},
  patternRoles: {},
  // synapse id -> provenance string, recomputed fresh every dynamic message
  // from already-broadcast fields only (dyn.neurons[].spiked and
  // dyn.l2_inhibition.last_delivery/targets) -- never inferred beyond
  // correlating two facts the backend already recorded. Only covers
  // feedforward (ff{i}->{j}) synapses that actually changed THIS step; see
  // weightChangeCause() below.
  weightChangeCause: new Map(),
};

// Provenance for this step's changed feedforward synapses: did the target
// L2E neuron just spike itself (self-spike learning), or was it hit by a
// delivered L2I->L2E loser-depression event THIS step (dyn.l2_inhibition.
// last_delivery.deliver_at === dyn.timestep, and this target's own
// `depressed` count > 0)? Both can be true in the same step (delivery lands
// at the top of step(), before this step's own competition -- see
// Phase13b_Diagnostic_Correction.md); reported as "both" when so, never
// resolved by guessing.
function weightChangeCause(dyn) {
  const cause = new Map();
  if (!dyn.changed_synapses?.length) return cause;
  const spiked = new Set(dyn.neurons.filter(n => n.spiked).map(n => n.id));
  const delivery = dyn.l2_inhibition?.last_delivery;
  const depressedNow = new Set(
    (delivery && delivery.deliver_at === dyn.timestep)
      ? (delivery.targets || []).filter(t => t.depressed > 0).map(t => t.id)
      : []);
  for (const c of dyn.changed_synapses) {
    if (!c.id.startsWith('ff')) continue;   // feedforward L1E->L2E only
    const target = 'L2E' + c.id.split('->')[1];
    const self = spiked.has(target), loser = depressedNow.has(target);
    if (self && loser) cause.set(c.id, 'self-spike learning + L2I loser depression');
    else if (self) cause.set(c.id, 'self-spike learning');
    else if (loser) cause.set(c.id, 'L2I loser depression');
  }
  return cause;
}

const renderer = new NeuronRenderer(document.getElementById('scene'), { onSelect: select });
const inspector = new Inspector(store);
const charts = new Charts(store);
const controls = new Controls(store, renderer, api);
const receptive = new ReceptiveFields(store, api);
const raster = new Raster(store);
const chargeChart = new ChargeChart(store);
const weightsChart = new WeightsChart(store);
const causalStory = new CausalStory(store);

function select(id) { inspector.select(id); renderer.select(id); weightsChart.setTarget(id); }

document.getElementById('fit-view')?.addEventListener('click', () => renderer.fitView());

// ---- FPS (simulation frames received per second) --------------------------
let frameStamps = [];
function tickFps() {
  const now = performance.now();
  frameStamps.push(now);
  while (frameStamps.length && now - frameStamps[0] > 1000) frameStamps.shift();
  return frameStamps.length;
}

// ---- websocket message handling -------------------------------------------
function onMessage(msg) {
  if (msg.type === 'topology') {
    const topo = msg.data;
    store.topology = topo;
    store.meta = new Map(topo.neurons.map(n => [n.id, n]));
    store.weights = new Map(topo.synapses.map(s => [s.id, s.weight ?? 0]));
    store.confidence = new Map(topo.synapses.filter(s => s.confidence != null).map(s => [s.id, s.confidence]));
    store.patternVectors = topo.pattern_vectors || {};
    store.probeVectors = topo.probe_vectors || {};
    store.patternRoles = topo.pattern_roles || {};
    renderer.build(topo);
    charts.buildStatic(topo);
    controls.onTopology(topo);
    receptive.build();
    raster.build(topo);
    chargeChart.build(topo);
    weightsChart.build();
  } else if (msg.type === 'dynamic') {
    const dyn = msg.data;
    store.dynamic = dyn;
    store.stateById = new Map(dyn.neurons.map(n => [n.id, n]));
    for (const c of dyn.changed_synapses || []) store.weights.set(c.id, c.weight);
    for (const c of dyn.changed_confidence || []) store.confidence.set(c.id, c.confidence);
    store.weightChangeCause = weightChangeCause(dyn);
    const fps = tickFps();
    renderer.update(dyn);
    charts.update(dyn, fps);
    receptive.update(dyn);
    raster.update(dyn);
    chargeChart.update(dyn);
    weightsChart.update(dyn);
    causalStory.update(dyn);
    inspector.refresh();   // re-renders if a neuron was already selected
    controls.onDynamic(dyn);
    updateTopbar(dyn, fps);
    updateStatusPanel(dyn);
  }
}

// ---- top bar --------------------------------------------------------------
const el = id => document.getElementById(id);

function updateTopbar(dyn, fps) {
  el('st-status').textContent = dyn.running ? 'Running' : 'Paused';
  el('st-status').style.color = dyn.running ? 'var(--ok)' : 'var(--txt-1)';
  el('st-timestep').textContent = dyn.timestep;
  el('st-speed').textContent = (dyn.speed ?? 0).toFixed(0) + ' /s';
  el('st-winner').textContent = firstResponderLabel(dyn, true);
  el('st-fps').textContent = fps;
  const story = dyn.causal_story;
  const pres = el('st-presentation');
  if (story && pres) {
    const tag = story.role === 'probe' ? 'probe' : story.role;
    pres.textContent = `#${story.presentation_id} ${story.pattern} (${tag})`
      + (story.plasticity_frozen ? ' · frozen' : '');
    pres.style.color = story.plasticity_frozen ? 'var(--inh)' : 'var(--txt-1)';
  }
}

function updateStatusPanel(dyn) {
  const status = dyn.simulator_status || {};
  const ownership = status.ownership || {};
  const pc = status.pc || {};
  const pattern = detectPatternLabel(dyn.input || [], store.patternVectors || {}, store.probeVectors || {});
  const modalOwner = ownership.modal_owner || '—';
  const collisions = (ownership.collisions || [])
    .map(row => `${row.owner}: ${row.patterns.join(', ')}`)
    .join(' · ') || 'none';
  const firstShare = ownership.clean_presentations
    ? `${(100 * (ownership.first_responder_share || 0)).toFixed(1)}%`
    : '—';
  const exactZero = status.exact_zero_feedforward ?? 0;
  const pcLabel = !pc.enabled
    ? 'OFF'
    : `${pc.current_spikes || 0} now · ${pc.spike_history_total || 0} total · max ${(pc.max_activation || 0).toFixed(2)}×thr`;
  const predState = predictionOutputStateLabel(dyn.prediction_column);
  const set = (id, value) => { const node = el(id); if (node) node.textContent = value; };
  set('sim-detected-pattern', pattern);
  set('sim-modal-owner', modalOwner);
  set('sim-collisions', collisions);
  set('sim-first-share', firstShare);
  set('sim-active-l2e', `${status.active_l2e ?? 0} active / ${status.unrecruited_l2e ?? 0} unrecruited`);
  set('sim-pc-maturity', pcLabel);
  set('sim-prediction-state', predState);
  set('sim-exact-zero', String(exactZero));
}

function onStatus(state) {
  const c = el('st-conn');
  c.className = 'conn ' + (state === 'online' ? 'online' : state === 'offline' ? 'offline' : '');
  el('st-conn-label').textContent =
    state === 'online' ? 'connected' : state === 'offline' ? 'disconnected' : 'connecting…';
}

// ---- go -------------------------------------------------------------------
const proto = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WSClient(`${proto}://${location.host}/ws`, { onMessage, onStatus });
ws.connect();
