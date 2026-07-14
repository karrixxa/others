// Full-screen spike raster: every neuron gets its own labeled lane, stacked on a
// shared time axis. Marks are DISCRETE SPIKES ONLY -- no charge/membrane trace
// (that lives in the separate Charge-over-time view). If a neuron did not spike
// at a timestep, its lane shows nothing there.
//
// PERFORMANCE: the canvas is sized to the VIEWPORT, not the whole history. A
// spacer gives the scroll container its virtual width, and only the visible time
// window is drawn (virtualized), so the backing store stays small. Draws are
// coalesced to one per animation frame.

const MARGIN = 66;        // pinned left gutter: id label + rate bar
const AXIS = 16;          // top axis strip
const HISTORY = 1500;     // timesteps retained

export class Raster {
  constructor(store) {
    this.store = store;
    this.overlay = document.getElementById('raster-overlay');
    this.scroll = document.getElementById('raster-scroll');
    this.spacer = document.getElementById('raster-spacer');
    this.canvas = document.getElementById('raster-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.order = [];
    this.spike = [];       // Uint8Array per timestep: 1 = spiked
    this.times = [];
    this.rate = new Map();
    // Presentation boundaries: {t, pattern, role} pushed whenever the backend's
    // causal_story.presentation_id changes (read, never computed here -- see
    // update()). Column index is derived from t - times[0] since timesteps are
    // contiguous, so old boundaries fall out of view automatically as the
    // rolling history shifts.
    this.boundaries = [];
    this._lastPresId = null;
    this.showL1 = true;
    this.colW = 6;
    this.follow = true;
    this.built = false;
    this._raf = 0;
    this._cw = this._ch = 0;

    document.querySelector('.tab[data-tab="raster"]')?.addEventListener('click', () => this.open());
    document.getElementById('raster-close')?.addEventListener('click', () => this.close());
    document.getElementById('raster-zoom-in')?.addEventListener('click', () => this._zoom(1.5));
    document.getElementById('raster-zoom-out')?.addEventListener('click', () => this._zoom(1 / 1.5));
    const l1 = document.getElementById('raster-l1');
    l1?.addEventListener('change', () => { this.showL1 = l1.checked; this._schedule(); });
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
    this.spike = []; this.times = []; this.boundaries = []; this._lastPresId = null;
    this.built = true;
  }

  update(dyn) {
    if (!this.built || !dyn || !dyn.neurons) return;
    const spk = new Uint8Array(this.order.length);
    for (const n of dyn.neurons) {
      const i = this.index.get(n.id);
      if (i != null && n.spiked) spk[i] = 1;
    }
    this.spike.push(spk); this.times.push(dyn.timestep);
    while (this.spike.length > HISTORY) { this.spike.shift(); this.times.shift(); }
    this.rate = new Map(dyn.neurons.map(n => [n.id, n.freq ?? 0]));
    // Presentation boundary: the backend's own presentation_id changed, so a new
    // named pattern/probe started at this timestep -- record it for the marker
    // below. Purely reactive to already-computed backend state.
    const story = dyn.causal_story;
    if (story && story.presentation_id !== this._lastPresId) {
      this._lastPresId = story.presentation_id;
      this.boundaries.push({ t: dyn.timestep, pattern: story.pattern, role: story.role });
      if (this.boundaries.length > 200) this.boundaries.shift();
    }
    this._schedule();
  }

  // Column index for an absolute timestep, given the current rolling buffer.
  _colForT(t) { return this.times.length ? t - this.times[0] : -1; }

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

  _lanes() { return this.showL1 ? this.order : this.order.filter(n => !n.group.startsWith('L1')); }

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

    const laneH = (vh - AXIS) / n;
    const y0 = AXIS;
    const barW = Math.max(1.5, this.colW - 1);
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
    }

    // Spikes (discrete marks), lane-outer so fillStyle is set once per lane.
    for (let i = 0; i < n; i++) {
      const idx = this.index.get(lanes[i].id);
      ctx.fillStyle = lanes[i].type === 'E' ? cExc : cInh;
      const yc = y0 + i * laneH + (laneH - tickH) / 2;
      for (let c = cFrom; c < cTo; c++) if (this.spike[c][idx]) ctx.fillRect(xOf(c), yc, barW, tickH);
    }

    // Presentation boundaries: one vertical marker + label per named pattern/
    // probe switch (backend-computed presentation_id, see update()). A probe
    // gets a dashed amber line; a training pattern a solid teal line.
    const cWin = getComputedStyle(document.documentElement).getPropertyValue('--win').trim() || '#ffce5c';
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
    if (cols) ctx.fillText(`spikes only · ${cols} steps · ${this.colW.toFixed(0)} px/step · newest →`, MARGIN + 6, 3);
  }
}
