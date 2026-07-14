// Right-sidebar neuron inspector.  Reads the shared store (static meta +
// current weights + latest dynamic state) and renders detail cards for the
// selected neuron.
//
// Bug fix: render() used to return silently when stateById was empty (race
// between click and first dynamic message, or paused simulation).  Now it
// shows a loading placeholder and retries via requestAnimationFrame so the
// panel always self-populates as soon as data arrives.

export class Inspector {
  constructor(store) {
    this.store = store;
    this.id = null;
    this.empty = document.getElementById('insp-empty');
    this.body = document.getElementById('insp-body');
  }

  select(id) {
    this.id = id;
    this.empty.hidden = true;
    this.body.hidden = false;
    this.render();
    // If data wasn't available yet, schedule a single retry once the browser
    // paints the next frame (handles first-load race and paused simulations).
    if (!this.store.stateById.get(id)) {
      requestAnimationFrame(() => { if (this.id === id) this.render(); });
    }
  }

  refresh() { if (this.id) this.render(); }

  render() {
    const s = this.store;
    const meta = s.meta.get(this.id);
    if (!meta) return;   // topology not received yet

    const state = s.stateById.get(this.id);
    if (!state) {
      this.body.innerHTML = '<div style="padding:1rem;color:var(--txt-2);font-size:12px">Waiting for simulation data…</div>';
      return;
    }

    const incoming = [], outgoing = [];
    for (const syn of (s.topology?.synapses ?? [])) {
      const w = s.weights.get(syn.id) ?? syn.weight ?? 0;
      const conf = s.confidence.get(syn.id) ?? syn.confidence ?? null;
      // Distance/influence/effective-transmission (feedforward synapses only;
      // static per topology load -- see backend _delivery_diagnostics).
      const dist = syn.distance ?? null, infl = syn.influence ?? null, eff = syn.effective ?? null;
      if (syn.target === this.id) incoming.push({ ...syn, w, conf, dist, infl, eff, other: syn.source });
      if (syn.source === this.id) outgoing.push({ ...syn, w, conf, dist, infl, eff, other: syn.target });
    }
    const strongest = [...incoming, ...outgoing].sort((a, b) => Math.abs(b.w) - Math.abs(a.w)).slice(0, 4);
    const col = meta.type === 'E' ? 'var(--exc)' : 'var(--inh)';
    const chargeBarPct = Math.max(0, Math.min(1, state.activation)) * 100;
    // Phase 3: legacy_distance_compat_active means the distance/influence/
    // effective numbers below are a TEMPORARY placeholder pinned to the
    // legacy reference geometry, NOT computed from this neuron's visible
    // (possibly jittered) position -- see backend geometry descriptor.
    const compatActive = !!s.topology?.geometry?.legacy_distance_compat_active;

    this.body.innerHTML = `
      <div class="insp-head">
        <div class="insp-orb" style="background:${col};color:${col}"></div>
        <div>
          <div class="insp-id">${this.id}</div>
          <div class="insp-tags">
            <span class="tag">${meta.layer}</span>
            <span class="tag">${meta.type === 'E' ? 'excitatory' : 'inhibitory'}</span>
            ${state.assembly ? `<span class="tag" style="color:var(--win)">assembly</span>` : ''}
          </div>
        </div>
      </div>
      <div class="insp-cards">
        ${card('Threshold', meta.threshold.toFixed(2))}
        ${state.budget != null ? card('Budget usage', `
          <div style="display:flex;align-items:center;gap:8px">
            <span style="font-variant-numeric:tabular-nums">${state.budget_used.toFixed(3)} / ${state.budget.toFixed(2)}</span>
            <div style="flex:1;height:6px;background:var(--bg-3);border-radius:3px;overflow:hidden">
              <div style="height:100%;width:${Math.max(0, Math.min(1, state.budget_used / state.budget)) * 100}%;background:var(--ff);border-radius:3px;transition:width .1s"></div>
            </div>
          </div>`) : ''}
        ${card('Charge', `
          <div style="display:flex;align-items:center;gap:8px">
            <span style="font-variant-numeric:tabular-nums">${state.potential.toFixed(3)}</span>
            <div style="flex:1;height:6px;background:var(--bg-3);border-radius:3px;overflow:hidden">
              <div style="height:100%;width:${chargeBarPct}%;background:${col};border-radius:3px;transition:width .1s"></div>
            </div>
            <span style="color:var(--txt-2);font-size:11px">${(state.activation * 100).toFixed(0)}%</span>
          </div>`)}
        ${card('Spike', `<span class="firing-badge ${state.spiked ? 'yes' : 'no'}">${state.spiked ? 'SPIKE' : 'idle'}</span>`, '', true)}
        ${card('Firing freq', (state.freq * 100).toFixed(1) + '%', bar(state.freq))}
        ${card('Refractory', state.refractory + ' steps')}
        ${compatActive ? `<div class="icard full">
            <div class="lbl">Geometry</div>
            <div class="val sm" style="color:var(--inh)">legacy-distance compat active</div>
            <p style="margin:4px 0 0;font-size:10.5px;color:var(--txt-2)">Positions shown are the
              new seeded geometry, but distance/influence/effective below are TEMPORARILY pinned
              to the legacy reference layout, not calculated from these coordinates.</p>
          </div>` : ''}
        ${synCard('Strongest connections', strongest, this.id, compatActive)}
        ${synCard(`Incoming (${incoming.length})`, incoming, this.id, compatActive)}
        ${synCard(`Outgoing (${outgoing.length})`, outgoing, this.id, compatActive)}
      </div>`;
  }
}

function card(lbl, val, extra = '', small = false) {
  return `<div class="icard">
    <div class="lbl">${lbl}</div>
    <div class="val ${small ? 'sm' : ''}">${val}</div>${extra}</div>`;
}
function bar(x) {
  const pct = Math.max(0, Math.min(1, x)) * 100;
  return `<div class="bar"><i style="width:${pct}%"></i></div>`;
}
function synCard(title, list, self, compatActive = false) {
  if (!list.length) return `<div class="icard full"><div class="lbl">${title}</div><div class="val sm" style="color:var(--txt-2)">none</div></div>`;
  // Render every synapse in the list. Callers that want a summary (e.g. the
  // "Strongest connections" card) pre-slice their list; the Incoming/Outgoing
  // cards pass the full set and their titles show the true count, so the rows
  // shown must match that count rather than being capped here.
  const rows = list.map(sy => {
    // Structural L2I->L2E competitive reset: unweighted event, no learned
    // magnitude -- show a fixed "reset" chip instead of a weight bar/value.
    if (sy.kind === 'reset_inhibition') {
      return `<div class="syn-row">
        <span class="name">${sy.other}</span>
        <span class="wbar"></span>
        <span class="wv" style="color:var(--in)" title="unweighted hard-reset event">reset</span></div>`;
    }
    const mag = Math.min(1, Math.abs(sy.w));
    const pos = sy.w >= 0;
    const width = (mag * 50).toFixed(0);
    const color = pos ? 'var(--ff)' : 'var(--in)';
    const style = pos ? `left:50%;width:${width}%;background:${color}` : `right:50%;width:${width}%;background:${color}`;
    // Confidence (trust in the gate) shown alongside the weight (gate size) when
    // the synapse carries one -- these are separate quantities in confidence mode.
    const conf = (sy.conf != null)
      ? `<span class="wv" title="confidence" style="color:var(--txt-2)">c ${sy.conf.toFixed(2)}</span>` : '';
    // Distance/influence/effective transmission (feedforward only; see
    // backend SimulationEngine._delivery_diagnostics -- brief SS7's required
    // per-connection fields, previously absent end-to-end).
    // compatActive: this synapse's distance/influence/effective are pinned to
    // the legacy reference geometry (Phase 3 temporary shim), NOT computed
    // from the coordinates actually shown -- label it, never present it as
    // if it were.
    const delivery = (sy.dist != null)
      ? `<span class="wv" title="${compatActive ? 'LEGACY-COMPAT (pinned, not from the visible coordinates): ' : 'engine '}distance -> influence -> effective transmission" style="color:${compatActive ? 'var(--inh)' : 'var(--txt-2)'}">${compatActive ? '⚠ ' : ''}d ${sy.dist.toFixed(2)} · g ${sy.infl.toFixed(2)} · eff ${sy.eff.toFixed(1)}</span>`
      : '';
    return `<div class="syn-row">
      <span class="name">${sy.other}</span>
      <span class="wbar"><i style="${style}"></i></span>
      <span class="wv">${sy.w >= 0 ? '+' : ''}${sy.w.toFixed(3)}</span>${conf}${delivery}</div>`;
  }).join('');
  return `<div class="icard full"><div class="lbl">${title}</div><div class="syn-list">${rows}</div></div>`;
}
