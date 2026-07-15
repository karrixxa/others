// Full-screen spike raster. Two modes, both reading the SAME recorded spike
// events (dyn.neurons[].spiked) and the SAME per-step activation history
// (dyn.neurons[].activation) the separate Charge/time view (charge.js) also
// reads -- no second simulator, no frontend-side spike inference, ever:
//
//   - DISCRETE (default, "showCharge" off): the original spikes-only lanes --
//     if a neuron did not spike at a timestep, its lane shows nothing there.
//   - COMBINED ("showCharge" on, restoring the older "spikes + charge buildup"
//     view): a dim charge bar rises toward a dashed threshold guide, and an
//     actual spike is a bright full-height mark -- ported from charge.js's own
//     rendering logic (same CHARGE_CAP, same colors/opacity), not reinvented.
//
// PERFORMANCE: the canvas is sized to the VIEWPORT, not the whole history. A
// spacer gives the scroll container its virtual width, and only the visible time
// window is drawn (virtualized), so the backing store stays small. Draws are
// coalesced to one per animation frame.

const MARGIN = 66;        // pinned left gutter: id label + rate bar
const AXIS = 16;          // top axis strip
const HISTORY = 1500;     // timesteps retained
const CHARGE_CAP = 2.0;   // V/theta at the top of a lane's charge zone (same as charge.js)

export class Raster {
  constructor(store) {
    this.store = store;
    this.overlay = document.getElementById('raster-overlay');
    this.scroll = document.getElementById('raster-scroll');
    this.spacer = document.getElementById('raster-spacer');
    this.canvas = document.getElementById('raster-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.tooltip = document.getElementById('raster-tooltip');
    this.order = [];
    this.spike = [];       // Uint8Array per timestep: 1 = spiked
    this.charge = [];      // Float32Array per timestep: activation (V/theta) -- same source as charge.js
    this.inhibited = [];   // Uint8Array per timestep: L2I hard-reset/competitive-reset reached this target
    this.times = [];
    this.rate = new Map();
    // Presentation boundaries: {t, pattern, role} pushed whenever the backend's
    // causal_story.presentation_id changes (read, never computed here -- see
    // update()).
    this.boundaries = [];
    this._lastPresId = null;
    // First-response markers (Phase 14): {t, ids, ambiguous} recorded once per
    // presentation, the moment causal_story.first_spike_t is first observed
    // for that presentation -- ids is causal_story.earliest_response_set when
    // ambiguous (the exact recorded tied set), else [first_spiker]. Nothing
    // here is inferred: both fields are read directly off the backend's own
    // presentation tracking.
    this.firstResponses = [];
    this._firstMarkedThisPresentation = false;

    // Per-population lane toggles (Phase 14) -- replaces the old single
    // showL1 boolean with independent L1E/L1I/L2E/L2I visibility.
    this.showL1E = true; this.showL1I = true; this.showL2E = true; this.showL2I = true;
    // View toggles (Phase 14), all local rendering state.
    this.showCharge = false;         // discrete-only is the preserved default
    this.hideSilentLanes = true;
    this.showBoundaries = true;
    this.showInhibitionMarkers = true;
    this.showFirstResponse = true;

    this.colW = 6;
    this.follow = true;
    this.built = false;
    this._raf = 0;
    this._cw = this._ch = 0;
    this._hoverCell = null;   // {lane, col} while hovering, for the tooltip

    document.querySelector('.tab[data-tab="raster"]')?.addEventListener('click', () => this.open());
    document.getElementById('raster-close')?.addEventListener('click', () => this.close());
    document.getElementById('raster-zoom-in')?.addEventListener('click', () => this._zoom(1.5));
    document.getElementById('raster-zoom-out')?.addEventListener('click', () => this._zoom(1 / 1.5));

    this._wireOptions();

    this.scroll?.addEventListener('scroll', () => {
      const s = this.scroll;
      this.follow = s.scrollLeft + s.clientWidth >= s.scrollWidth - 6;
      this._schedule();
    });
    this.scroll?.addEventListener('wheel', (e) => this._wheelZoom(e), { passive: false });
    this.scroll?.addEventListener('mousemove', (e) => this._onHover(e));
    this.scroll?.addEventListener('mouseleave', () => this._hideTooltip());
    window.addEventListener('resize', () => this._schedule());
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && this._open()) this.close(); });
  }

  // Wires the raster's own options drawer (collapsible, lives in the overlay's
  // toolbar since the overlay covers the sidebar -- see index.html). Every
  // toggle here is local rendering state only; none of it touches the backend.
  _wireOptions() {
    const BIND_PROP = {
      'raster-show-charge': 'showCharge', 'raster-hide-silent': 'hideSilentLanes',
      'raster-show-boundaries': 'showBoundaries', 'raster-show-inhibition': 'showInhibitionMarkers',
      'raster-show-first-response': 'showFirstResponse',
      'raster-l1e': 'showL1E', 'raster-l1i': 'showL1I', 'raster-l2e': 'showL2E', 'raster-l2i': 'showL2I',
    };
    for (const [id, prop] of Object.entries(BIND_PROP)) {
      const el = document.getElementById(id);
      if (!el) continue;
      el.checked = this[prop];
      el.addEventListener('change', () => { this[prop] = el.checked; this._schedule(); });
    }
    document.getElementById('raster-options-toggle')?.addEventListener('click', (e) => {
      document.getElementById('raster-options')?.classList.toggle('open');
      e.currentTarget.classList.toggle('active-toggle');
    });
  }

  _open() { return this.overlay && !this.overlay.hidden; }
  _schedule() {
    if (this._raf || !this._open()) return;
    this._raf = requestAnimationFrame(() => { this._raf = 0; this._draw(); });
  }

  build(topo) {
    this.order = (topo?.neurons ?? []).map(n => ({ id: n.id, type: n.type, layer: n.layer, group: n.layer + n.type }));
    this.index = new Map(this.order.map((n, i) => [n.id, i]));
    this.spike = []; this.charge = []; this.inhibited = []; this.times = [];
    this.boundaries = []; this._lastPresId = null;
    this.firstResponses = []; this._firstMarkedThisPresentation = false;
    this.built = true;
  }

  update(dyn) {
    if (!this.built || !dyn || !dyn.neurons) return;
    const nN = this.order.length;
    const spk = new Uint8Array(nN), chg = new Float32Array(nN), inh = new Uint8Array(nN);
    for (const n of dyn.neurons) {
      const i = this.index.get(n.id);
      if (i == null) continue;
      if (n.spiked) spk[i] = 1;
      chg[i] = n.activation ?? 0;
    }
    // Structural L2I->L2E competitive reset (reset->{j}); same reading as
    // charge.js -- no learned magnitude, just a delivered-event marker.
    for (const edge of dyn.emitted || []) {
      if (!edge.startsWith('reset->')) continue;
      const i = this.index.get(`L2E${edge.slice(7)}`);
      if (i != null) inh[i] = 1;
    }
    this.spike.push(spk); this.charge.push(chg); this.inhibited.push(inh); this.times.push(dyn.timestep);
    while (this.spike.length > HISTORY) {
      this.spike.shift(); this.charge.shift(); this.inhibited.shift(); this.times.shift();
    }
    this.rate = new Map(dyn.neurons.map(n => [n.id, n.freq ?? 0]));

    // Presentation boundary: the backend's own presentation_id changed, so a new
    // named pattern/probe started at this timestep -- record it for the marker
    // below. Purely reactive to already-computed backend state.
    const story = dyn.causal_story;
    if (story && story.presentation_id !== this._lastPresId) {
      this._lastPresId = story.presentation_id;
      this.boundaries.push({ t: dyn.timestep, pattern: story.pattern, role: story.role });
      if (this.boundaries.length > 200) this.boundaries.shift();
      this._firstMarkedThisPresentation = false;
    }
    // First-response marker: record ONCE per presentation, the instant the
    // backend's own first_spike_t becomes non-null for the CURRENT
    // presentation. earliest_response_set is the exact recorded tied set
    // (brief SS9/Phase 6) -- used verbatim on an ambiguous tie, never
    // re-derived.
    if (story && !this._firstMarkedThisPresentation && story.first_spike_t != null) {
      this._firstMarkedThisPresentation = true;
      const ids = story.same_step_tie ? (story.earliest_response_set || []) : [story.first_spiker];
      this.firstResponses.push({ t: story.first_spike_t, ids, ambiguous: !!story.same_step_tie });
      if (this.firstResponses.length > 200) this.firstResponses.shift();
    }
    this._schedule();
  }

  // Column index for an absolute timestep, given the current rolling buffer.
  _colForT(t) { return this.times.length ? t - this.times[0] : -1; }

  open() { this.overlay.hidden = false; this.follow = true; this._cw = this._ch = 0; this._draw(); }
  close() { this.overlay.hidden = true; this._hideTooltip(); }

  _zoom(f) {
    this._anchor = this.follow ? null : (this.scroll.scrollLeft + this.scroll.clientWidth / 2 - MARGIN) / this.colW;
    this.colW = Math.max(2, Math.min(40, this.colW * f));
    this._draw();
  }

  // Cursor-anchored zoom on a vertical wheel; shift+wheel or a horizontal wheel
  // (trackpad) falls through to normal timeline panning.
  _wheelZoom(e) {
    if (!this._open()) return;
    if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
    e.preventDefault();
    const mx = e.clientX - this.scroll.getBoundingClientRect().left;   // cursor x in viewport
    const col = (this.scroll.scrollLeft + Math.max(mx, MARGIN) - MARGIN) / this.colW;
    const next = Math.max(2, Math.min(40, this.colW * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    if (next === this.colW) return;
    this.colW = next;
    this.follow = false;                    // anchored to the cursor, not the live edge
    this._anchor = col; this._anchorPx = mx;
    this._draw();
  }

  _laneVisible(n) {
    if (n.group === 'L1E') return this.showL1E;
    if (n.group === 'L1I') return this.showL1I;
    if (n.group === 'L2E') return this.showL2E;
    if (n.group === 'L2I') return this.showL2I;
    return true;
  }

  _lanes() {
    let lanes = this.order.filter(n => this._laneVisible(n));
    if (this.hideSilentLanes && this.spike.length) {
      lanes = lanes.filter(n => {
        const idx = this.index.get(n.id);
        for (let c = 0; c < this.spike.length; c++) if (this.spike[c][idx]) return true;
        return false;
      });
    }
    return lanes;
  }

  // -------------------------------------------------------------- hover
  _onHover(e) {
    if (!this._open() || !this.built || !this.tooltip) return;
    const rect = this.scroll.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const lanes = this._lastLanes || [];
    const n = lanes.length;
    if (mx < MARGIN || my < AXIS || !n) { this._hideTooltip(); return; }
    const laneH = this._lastLaneH || 0;
    const i = Math.floor((my - AXIS) / laneH);
    const col = Math.floor((this.scroll.scrollLeft + mx - MARGIN) / this.colW);
    if (i < 0 || i >= n || col < 0 || col >= this.spike.length) { this._hideTooltip(); return; }
    const lane = lanes[i];
    const idx = this.index.get(lane.id);
    const t = this.times[col];
    const a = this.charge[col][idx];
    const spiked = !!this.spike[col][idx];
    this.tooltip.textContent = `${lane.id} · t=${t} · V/θ=${a.toFixed(3)}${spiked ? ' · SPIKE' : ''}`;
    this.tooltip.style.left = (e.clientX + 12) + 'px';
    this.tooltip.style.top = (e.clientY + 12) + 'px';
    this.tooltip.hidden = false;
  }

  _hideTooltip() { if (this.tooltip) this.tooltip.hidden = true; }

  _draw() {
    if (!this._open() || !this.built) return;
    const lanes = this._lanes();
    this._lastLanes = lanes;
    const n = lanes.length;
    if (!n) return;
    const vw = this.scroll.clientWidth, vh = this.scroll.clientHeight;
    if (vw < 2 || vh < 2) return;
    const cols = this.spike.length;
    this.spacer.style.width = (MARGIN + cols * this.colW) + 'px';

    if (this._anchor != null) {
      const px = this._anchorPx != null ? this._anchorPx : this.scroll.clientWidth / 2;
      const S = this._anchor * this.colW + MARGIN - px;
      this.scroll.scrollLeft = Math.max(0, Math.min(S, this.scroll.scrollWidth - vw));
      this._anchor = this._anchorPx = null;
    } else if (this.follow) {
      this.scroll.scrollLeft = this.scroll.scrollWidth;
    }

    const dpr = window.devicePixelRatio || 1;
    if (this._cw !== vw || this._ch !== vh) {
      this.canvas.style.width = vw + 'px'; this.canvas.style.height = vh + 'px';
      this.canvas.width = Math.round(vw * dpr); this.canvas.height = Math.round(vh * dpr);
      this._cw = vw; this._ch = vh;
    }
    const ctx = this.ctx;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, vw, vh);

    const css = getComputedStyle(document.documentElement);
    const cExc = css.getPropertyValue('--exc').trim() || '#5eead4';
    const cInh = css.getPropertyValue('--inh').trim() || '#f0788c';
    const cLine = css.getPropertyValue('--line').trim() || '#242b3a';
    const cTxt = css.getPropertyValue('--txt-1').trim() || '#c7d0e0';
    const cMut = css.getPropertyValue('--txt-2').trim() || '#5f6b82';
    const cWin = css.getPropertyValue('--win').trim() || '#ffce5c';

    const laneH = (vh - AXIS) / n;
    this._lastLaneH = laneH;
    const y0 = AXIS;
    const barW = Math.max(1.5, this.colW - 1);
    const zone = laneH * 0.82;
    const thrFrac = 1 / CHARGE_CAP;
    const scrollX = this.scroll.scrollLeft;
    const cFrom = Math.max(0, Math.floor((scrollX - MARGIN) / this.colW) - 1);
    const cTo = Math.min(cols, Math.ceil((scrollX - MARGIN + vw) / this.colW) + 1);
    const xOf = (c) => MARGIN + (c * this.colW - scrollX);
    const tickH = Math.min(laneH - 2, Math.max(3, laneH * 0.6));

    // Group stripes + separators.
    let gi = 0;
    for (let i = 0; i < n; i++) {
      const g = lanes[i].group, prev = i ? lanes[i - 1].group : null;
      if (g !== prev) {
        gi++;
        let j = i; while (j < n && lanes[j].group === g) j++;
        ctx.fillStyle = (gi % 2) ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.05)';
        ctx.fillRect(0, y0 + i * laneH, vw, (j - i) * laneH);
        ctx.strokeStyle = cLine; ctx.beginPath();
        ctx.moveTo(0, y0 + i * laneH + .5); ctx.lineTo(vw, y0 + i * laneH + .5); ctx.stroke();
      }
      // Combined mode: dashed threshold guide per lane (ported from charge.js).
      if (this.showCharge) {
        const baseY = y0 + (i + 1) * laneH - 1;
        const ty = Math.round(baseY - thrFrac * zone) + .5;
        ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.setLineDash([3, 3]); ctx.beginPath();
        ctx.moveTo(MARGIN, ty); ctx.lineTo(vw, ty); ctx.stroke(); ctx.setLineDash([]);
      }
    }

    // Combined mode: dim charge bars (ported from charge.js -- same source
    // data, same CHARGE_CAP, same 0.30 alpha), drawn behind the spike ticks.
    if (this.showCharge) {
      ctx.globalAlpha = 0.30;
      for (let i = 0; i < n; i++) {
        const idx = this.index.get(lanes[i].id);
        ctx.fillStyle = lanes[i].type === 'E' ? cExc : cInh;
        const baseY = y0 + (i + 1) * laneH - 1;
        for (let c = cFrom; c < cTo; c++) {
          if (this.spike[c][idx]) continue;
          const a = this.charge[c][idx];
          if (a <= 0.02) continue;
          ctx.fillRect(xOf(c), baseY - Math.min(a / CHARGE_CAP, 1) * zone, barW, Math.min(a / CHARGE_CAP, 1) * zone);
        }
      }
      ctx.globalAlpha = 1;
    }

    // Spikes: discrete mode draws a mid-lane tick; combined mode draws a
    // charge.js-style full-height bright peak instead.
    for (let i = 0; i < n; i++) {
      const idx = this.index.get(lanes[i].id);
      ctx.fillStyle = lanes[i].type === 'E' ? cExc : cInh;
      if (this.showCharge) {
        const laneTop = y0 + i * laneH + 1;
        for (let c = cFrom; c < cTo; c++)
          if (this.spike[c][idx]) ctx.fillRect(xOf(c), laneTop, barW, laneH - 2);
      } else {
        const yc = y0 + i * laneH + (laneH - tickH) / 2;
        for (let c = cFrom; c < cTo; c++)
          if (this.spike[c][idx]) ctx.fillRect(xOf(c), yc, barW, tickH);
      }
    }

    // Inhibition/reset markers (ported from charge.js): red tick where a
    // delivered L2I->L2E discharge reached this target this step.
    if (this.showInhibitionMarkers) {
      for (let i = 0; i < n; i++) {
        const idx = this.index.get(lanes[i].id);
        const laneTop = y0 + i * laneH + 1;
        ctx.fillStyle = cInh;
        for (let c = cFrom; c < cTo; c++) {
          if (!this.inhibited[c][idx]) continue;
          ctx.fillRect(xOf(c), laneTop + Math.max(5, laneH * 0.22), barW,
                       Math.max(2, Math.min(4, laneH * 0.18)));
        }
      }
    }

    // First-response markers (Phase 14): filled dot = the recorded
    // first_spiker; hollow ring on every member of earliest_response_set =
    // an ambiguous same-step tie (backend-recorded set, not re-derived).
    if (this.showFirstResponse) {
      const laneIndexOf = new Map(lanes.map((l, i) => [l.id, i]));
      for (const fr of this.firstResponses) {
        const c = this._colForT(fr.t);
        if (c < cFrom || c >= cTo) continue;
        const cx = xOf(c) + barW / 2;
        for (const id of fr.ids) {
          const li = laneIndexOf.get(id);
          if (li == null) continue;
          const cy = y0 + li * laneH + laneH / 2;
          ctx.beginPath();
          ctx.arc(cx, cy, Math.max(2.5, Math.min(5, laneH * 0.3)), 0, Math.PI * 2);
          if (fr.ambiguous) {
            ctx.strokeStyle = cWin; ctx.lineWidth = 1.4; ctx.stroke();
          } else {
            ctx.fillStyle = cWin; ctx.fill();
          }
        }
      }
    }

    // Presentation boundaries: one vertical marker + label per named pattern/
    // probe switch (backend-computed presentation_id, see update()). A probe
    // gets a dashed amber line; a training pattern a solid teal line.
    if (this.showBoundaries) {
      for (const b of this.boundaries) {
        const c = this._colForT(b.t);
        if (c < cFrom || c >= cTo) continue;
        const x = xOf(c) + 0.5;
        ctx.strokeStyle = b.role === 'probe' ? cInh : cWin;
        ctx.setLineDash(b.role === 'probe' ? [4, 3] : []);
        ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, vh); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = ctx.strokeStyle;
        ctx.font = '9px ui-monospace, monospace'; ctx.textBaseline = 'top';
        ctx.fillText(`${b.pattern}${b.role === 'probe' ? ' (probe)' : ''}`, x + 3, y0 + 1);
      }
    }

    // Pinned gutter: id labels + firing-rate bars + divider.
    ctx.clearRect(0, AXIS, MARGIN, vh - AXIS);
    const labelPx = Math.max(8, Math.min(11, laneH - 4));
    ctx.textBaseline = 'middle';
    for (let i = 0; i < n; i++) {
      const cy = y0 + (i + 0.5) * laneH;
      ctx.font = `${labelPx}px ui-monospace, monospace`;
      ctx.fillStyle = cTxt; ctx.fillText(lanes[i].id, 5, cy);
      const f = Math.max(0, Math.min(1, this.rate.get(lanes[i].id) ?? 0));
      ctx.fillStyle = lanes[i].type === 'E' ? cExc : cInh; ctx.globalAlpha = 0.5;
      ctx.fillRect(MARGIN - 15, cy - 1.5, 12 * f, 3); ctx.globalAlpha = 1;
    }
    ctx.strokeStyle = cLine; ctx.beginPath(); ctx.moveTo(MARGIN + .5, 0); ctx.lineTo(MARGIN + .5, vh); ctx.stroke();
    ctx.clearRect(MARGIN, 0, vw - MARGIN, AXIS);
    ctx.fillStyle = cMut; ctx.font = '10px ui-monospace, monospace'; ctx.textBaseline = 'top';
    const modeLabel = this.showCharge
      ? 'spikes + charge buildup · dashed = threshold' : 'spikes only';
    if (cols) ctx.fillText(`${modeLabel} · ${cols} steps · ${this.colW.toFixed(0)} px/step · newest →`, MARGIN + 6, 3);
  }
}
