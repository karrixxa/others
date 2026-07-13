// Full-screen spike raster: every neuron gets its own labeled lane, stacked on a
// shared time axis. Discrete spike ticks are drawn in front; a dim charge-buildup
// fill (V/theta, the same activation value the separate Charge-over-time view
// uses) is drawn behind each lane so accumulation toward threshold, resets, and
// inhibition discharges are visible on the SAME timeline as the spikes, without
// switching tabs. Toggle with "Show charge".
//
// PERFORMANCE: the canvas is sized to the VIEWPORT, not the whole history. A
// spacer gives the scroll container its virtual width, and only the visible time
// window is drawn (virtualized), so the backing store stays small. Draws are
// coalesced to one per animation frame.

const MARGIN = 66;        // pinned left gutter: id label + rate bar
const AXIS = 28;          // top strip: summary plus pattern labels
const HISTORY = 1500;     // timesteps retained
const CHARGE_CAP = 2.0;   // V/theta at the top of a lane's charge zone (matches charge.js)

export class Raster {
  constructor(store, opts = {}) {
    this.store = store;
    this.onSelect = opts.onSelect || null;
    this.overlay = document.getElementById('raster-overlay');
    this.scroll = document.getElementById('raster-scroll');
    this.spacer = document.getElementById('raster-spacer');
    this.canvas = document.getElementById('raster-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.order = [];
    this.spike = [];       // Uint8Array per timestep: 1 = spiked
    this.charge = [];      // Float32Array per timestep: activation (V/theta)
    this.times = [];
    this.patterns = [];    // active input-pattern name per timestep
    this.rate = new Map();
    this.showL1 = true;
    // Most neurons are silent for a held 3-pixel pattern. Collapse those empty
    // rows by default so the meaningful spikes are not separated by large gaps;
    // the checkbox can restore the complete topology whenever needed.
    this.hideSilent = true;
    this.showCharge = true;
    this.colW = 6;
    this.follow = true;
    this.built = false;
    this._raf = 0;
    this._cw = this._ch = 0;
    this._laneRects = [];   // [{id, y, h}] for the currently drawn gutter, for click-to-select

    document.querySelector('.tab[data-tab="raster"]')?.addEventListener('click', () => this.open());
    document.getElementById('raster-close')?.addEventListener('click', () => this.close());
    document.getElementById('raster-zoom-in')?.addEventListener('click', () => this._zoom(1.5));
    document.getElementById('raster-zoom-out')?.addEventListener('click', () => this._zoom(1 / 1.5));
    const l1 = document.getElementById('raster-l1');
    l1?.addEventListener('change', () => { this.showL1 = l1.checked; this._schedule(); });
    const quiet = document.getElementById('raster-hide-silent');
    quiet?.addEventListener('change', () => { this.hideSilent = quiet.checked; this._schedule(); });
    const charge = document.getElementById('raster-show-charge');
    charge?.addEventListener('change', () => { this.showCharge = charge.checked; this._schedule(); });
    this.canvas.addEventListener('click', (e) => this._onClick(e));
    this.tooltip = document.getElementById('raster-tooltip');
    this.canvas.addEventListener('mousemove', (e) => this._onHover(e));
    this.canvas.addEventListener('mouseleave', () => { if (this.tooltip) this.tooltip.hidden = true; });
    this.scroll?.addEventListener('scroll', () => {
      const s = this.scroll;
      this.follow = s.scrollLeft + s.clientWidth >= s.scrollWidth - 6;
      this._schedule();
    });
    this.scroll?.addEventListener('wheel', (e) => this._wheelZoom(e), { passive: false });
    window.addEventListener('resize', () => this._schedule());
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && this._open()) this.close(); });
  }

  _open() { return this.overlay && !this.overlay.hidden; }
  _schedule() {
    if (this._raf || !this._open()) return;
    this._raf = requestAnimationFrame(() => { this._raf = 0; this._draw(); });
  }

  build(topo) {
    this.order = (topo?.neurons ?? []).map(n => ({ id: n.id, type: n.type, group: n.layer + n.type }));
    this.index = new Map(this.order.map((n, i) => [n.id, i]));
    this.spike = []; this.charge = []; this.times = []; this.patterns = [];
    this.built = true;
  }

  update(dyn) {
    if (!this.built || !dyn || !dyn.neurons) return;
    const spk = new Uint8Array(this.order.length);
    const chg = new Float32Array(this.order.length);
    for (const n of dyn.neurons) {
      const i = this.index.get(n.id);
      if (i == null) continue;
      if (n.spiked) spk[i] = 1;
      chg[i] = n.activation ?? 0;
    }
    this.spike.push(spk);
    this.charge.push(chg);
    this.times.push(dyn.timestep);
    this.patterns.push(dyn.autocycle?.pattern ?? 'manual');
    const patternLabel = document.getElementById('raster-current-pattern');
    if (patternLabel) patternLabel.textContent = this.patterns[this.patterns.length - 1];
    while (this.spike.length > HISTORY) {
      this.spike.shift(); this.charge.shift(); this.times.shift(); this.patterns.shift();
    }
    this.rate = new Map(dyn.neurons.map(n => [n.id, n.freq ?? 0]));
    this._schedule();
  }

  open() { this.overlay.hidden = false; this.follow = true; this._cw = this._ch = 0; this._draw(); }
  close() { this.overlay.hidden = true; }

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

  _lanes() {
    let lanes = this.showL1 ? this.order : this.order.filter(n => !n.group.startsWith('L1'));
    if (!this.hideSilent || !this.spike.length) return lanes;
    return lanes.filter(n => {
      const idx = this.index.get(n.id);
      return this.spike.some(frame => frame[idx]);
    });
  }

  _draw() {
    if (!this._open() || !this.built) return;
    const lanes = this._lanes();
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
    const cAccent = css.getPropertyValue('--accent').trim() || '#5eead4';

    const laneH = (vh - AXIS) / n;
    const y0 = AXIS;
    const barW = Math.max(1.5, this.colW - 1);
    const scrollX = this.scroll.scrollLeft;
    const cFrom = Math.max(0, Math.floor((scrollX - MARGIN) / this.colW) - 1);
    const cTo = Math.min(cols, Math.ceil((scrollX - MARGIN + vw) / this.colW) + 1);
    const xOf = (c) => MARGIN + (c * this.colW - scrollX);
    const tickH = Math.min(laneH - 2, Math.max(3, laneH * 0.6));

    // Light time grid every 25 recorded steps, with the engine timestep shown in
    // the axis strip. This remains useful when a single pattern is held and there
    // are therefore no pattern-change boundaries in the visible window.
    ctx.font = '9px ui-monospace, monospace';
    ctx.textBaseline = 'top';
    for (let c = cFrom; c < cTo; c++) {
      const t = this.times[c];
      if (t == null || t % 25 !== 0) continue;
      const x = xOf(c) + 0.5;
      ctx.strokeStyle = cLine;
      ctx.globalAlpha = 0.55;
      ctx.beginPath(); ctx.moveTo(x, AXIS); ctx.lineTo(x, vh); ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillStyle = cMut;
      ctx.fillText(String(t), x + 2, 14);
    }

    // Presentation boundaries come from the engine's active pattern. This
    // captures both manual pattern changes and auto-cycle visits without a
    // second UI-side clock.
    ctx.font = '9px ui-monospace, monospace';
    ctx.textBaseline = 'top';
    for (let c = cFrom; c < cTo; c++) {
      const changed = c === 0 || this.patterns[c] !== this.patterns[c - 1];
      if (!changed) continue;
      const x = xOf(c) + 0.5;
      ctx.strokeStyle = cAccent;
      ctx.globalAlpha = 0.5;
      ctx.beginPath(); ctx.moveTo(x, AXIS); ctx.lineTo(x, vh); ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillStyle = cAccent;
      ctx.fillText(this.patterns[c] || 'pattern', x + 3, 14);
    }

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
    }

    // Charge buildup (dim fill, same activation values as the Charge-over-time
    // view) drawn BEHIND the spike ticks, on the identical time/lane geometry --
    // so accumulation, resets, and inhibition discharges read on the same
    // timeline as the discrete spikes instead of a separate tab.
    if (this.showCharge) {
      const zone = laneH * 0.82;
      const thrFrac = 1 / CHARGE_CAP;
      for (let i = 0; i < n; i++) {
        const idx = this.index.get(lanes[i].id);
        const baseY = y0 + (i + 1) * laneH - 1;
        ctx.strokeStyle = 'rgba(255,255,255,0.10)'; ctx.setLineDash([3, 3]);
        const ty = Math.round(baseY - thrFrac * zone) + .5;
        ctx.beginPath(); ctx.moveTo(MARGIN, ty); ctx.lineTo(vw, ty); ctx.stroke(); ctx.setLineDash([]);
        ctx.fillStyle = lanes[i].type === 'E' ? cExc : cInh;
        ctx.globalAlpha = 0.22;
        for (let c = cFrom; c < cTo; c++) {
          if (this.spike[c][idx]) continue;
          const a = this.charge[c][idx];
          if (a <= 0.02) continue;
          const h = Math.min(a / CHARGE_CAP, 1) * zone;
          ctx.fillRect(xOf(c), baseY - h, barW, h);
        }
        ctx.globalAlpha = 1;
      }
    }

    // Spikes (discrete marks), lane-outer so fillStyle is set once per lane.
    for (let i = 0; i < n; i++) {
      const idx = this.index.get(lanes[i].id);
      ctx.fillStyle = lanes[i].type === 'E' ? cExc : cInh;
      const yc = y0 + i * laneH + (laneH - tickH) / 2;
      for (let c = cFrom; c < cTo; c++) if (this.spike[c][idx]) ctx.fillRect(xOf(c), yc, barW, tickH);
    }

    // Pinned gutter: id labels + firing-rate bars + divider.
    ctx.clearRect(0, AXIS, MARGIN, vh - AXIS);
    const labelPx = Math.max(8, Math.min(11, laneH - 4));
    ctx.textBaseline = 'middle';
    this._laneRects = [];
    for (let i = 0; i < n; i++) {
      const cy = y0 + (i + 0.5) * laneH;
      ctx.font = `${labelPx}px ui-monospace, monospace`;
      ctx.fillStyle = cTxt; ctx.fillText(lanes[i].id, 5, cy);
      const f = Math.max(0, Math.min(1, this.rate.get(lanes[i].id) ?? 0));
      ctx.fillStyle = lanes[i].type === 'E' ? cExc : cInh; ctx.globalAlpha = 0.5;
      ctx.fillRect(MARGIN - 15, cy - 1.5, 12 * f, 3); ctx.globalAlpha = 1;
      this._laneRects.push({ id: lanes[i].id, y: y0 + i * laneH, h: laneH });
    }
    ctx.strokeStyle = cLine; ctx.beginPath(); ctx.moveTo(MARGIN + .5, 0); ctx.lineTo(MARGIN + .5, vh); ctx.stroke();
    ctx.clearRect(MARGIN, 0, vw - MARGIN, 13);
    ctx.fillStyle = cMut; ctx.font = '10px ui-monospace, monospace'; ctx.textBaseline = 'top';
    const chargeNote = this.showCharge ? 'spikes + charge (dim fill, dashed = threshold)' : 'spikes only';
    if (cols) ctx.fillText(`${chargeNote} · ${cols} steps · ${this.colW.toFixed(0)} px/step · newest →`, MARGIN + 6, 3);
  }

  // Clicking a lane's id label (in the pinned gutter) selects that neuron
  // elsewhere in the dashboard (3D view, inspector, and -- for an L2E -- the
  // Weights-over-time chart), so you can jump from "this lane looks
  // interesting" straight to its weight trajectory without hunting for it.
  // Hover readout: reports the exact V/theta value (and spike/no-spike) for
  // whichever neuron lane and timestep column sit under the cursor, so you
  // don't have to eyeball fill height against the dashed threshold line.
  _onHover(e) {
    if (!this.tooltip || !this._laneRects.length || !this.spike.length) return;
    const rect = this.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    if (x < MARGIN) { this.tooltip.hidden = true; return; }
    const lane = this._laneRects.find(r => y >= r.y && y < r.y + r.h);
    if (!lane) { this.tooltip.hidden = true; return; }
    const scrollX = this.scroll.scrollLeft;
    const c = Math.round((x - MARGIN + scrollX) / this.colW);
    if (c < 0 || c >= this.spike.length) { this.tooltip.hidden = true; return; }
    const idx = this.index.get(lane.id);
    const t = this.times[c];
    const a = this.charge[c][idx];
    const spiked = this.spike[c][idx];
    this.tooltip.hidden = false;
    this.tooltip.textContent = `${lane.id} · t=${t} · V/θ=${a.toFixed(3)}${spiked ? ' · SPIKE' : ''}`;
    const left = Math.min(x + 12, this.scroll.clientWidth - this.tooltip.offsetWidth - 8);
    this.tooltip.style.left = `${Math.max(MARGIN, left)}px`;
    this.tooltip.style.top = `${Math.max(0, y - 24)}px`;
  }

  _onClick(e) {
    if (!this.onSelect || !this._laneRects.length) return;
    const rect = this.canvas.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const x = e.clientX - rect.left;
    if (x > MARGIN) return;   // clicks over the timeline itself are not lane selection
    const hit = this._laneRects.find(r => y >= r.y && y < r.y + r.h);
    if (hit) this.onSelect(hit.id);
  }
}
