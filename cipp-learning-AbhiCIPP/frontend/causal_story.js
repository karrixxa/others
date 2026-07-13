// Causal Story -- a bottom-panel tab that turns "stare at the raster and
// reconstruct what happened" into a plain readout, using ONLY fields the
// engine already exposes over the websocket (dyn.neurons[].spiked, dyn.winner,
// dyn.autocycle, dyn.emitted). Nothing here is invented: if a field isn't in
// the dynamic payload, the row says "(none yet)" rather than guessing.
//
// Per-presentation tracking resets whenever dyn.autocycle.pattern changes
// (covers both the auto-cycle harness and manual pattern switches).

export class CausalStory {
  constructor(store) {
    this.store = store;
    this.el = document.getElementById('story-fields');
    this.presentation = 0;
    this._lastPattern = null;
    this._reset();
  }

  _reset() {
    this.firstSpiker = null;
    this.earliestSet = new Set();
    this.l2iStep = null;
    this.inhibitionStep = null;
    this.winnersSeen = new Set();
    this.startTimestep = null;
  }

  // Called on a fresh topology (e.g. after /api/reset) so stale counts from a
  // previous run don't linger under a new pattern set.
  build() {
    this.presentation = 0;
    this._lastPattern = null;
    this._reset();
  }

  update(dyn) {
    if (!dyn) return;
    const pattern = dyn.autocycle?.pattern ?? 'manual';
    if (pattern !== this._lastPattern) {
      this._lastPattern = pattern;
      this.presentation++;
      this._reset();
      this.startTimestep = dyn.timestep;
    }
    const relStep = this.startTimestep != null ? dyn.timestep - this.startTimestep : 0;
    for (const n of dyn.neurons || []) {
      if (!n.spiked) continue;
      if (n.id.startsWith('L2E')) {
        if (this.firstSpiker == null) this.firstSpiker = n.id;
        this.earliestSet.add(n.id);
      } else if (n.id === 'L2I' && this.l2iStep == null) {
        this.l2iStep = relStep;
      }
    }
    if (this.inhibitionStep == null && (dyn.emitted || []).some(s => s.startsWith('inh->'))) {
      this.inhibitionStep = relStep;
    }
    if (dyn.winner) this.winnersSeen.add(dyn.winner);
    this._render(dyn);
  }

  _render(dyn) {
    if (!this.el) return;
    const ac = dyn.autocycle || {};
    const rows = [
      ['Pattern', ac.pattern ?? '—'],
      ['Presentation #', String(this.presentation)],
      ['First physical L2E spiker', this.firstSpiker ?? '(none yet)'],
      ['Earliest response set', this.earliestSet.size ? [...this.earliestSet].join(', ') : '(none yet)'],
      ['Selected competition winner', dyn.winner ?? '(none this step)'],
      ['L2I spike step (this presentation)', this.l2iStep ?? '(not yet)'],
      ['Inhibition delivery step (this presentation)', this.inhibitionStep ?? '(not yet)'],
      ["Pattern's current modal owner", ac.last_winner ?? '(none yet)'],
      ['Recognition consistency (streak / target)', `${ac.streak ?? 0} / ${ac.target ?? '—'}`],
      ['Sustained round-robin this presentation?',
        this.winnersSeen.size > 1 ? `yes (${[...this.winnersSeen].join(', ')})` : 'no'],
    ];
    this.el.innerHTML = rows.map(([k, v]) =>
      `<div class="story-row"><span class="story-key">${k}</span><span class="story-val">${v}</span></div>`
    ).join('');
  }
}
