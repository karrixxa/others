// Input Weights overview -- a bottom-panel tab (not a full-screen overlay).
// Two things a single-neuron Weights-over-time chart can't show at a glance:
//
//   1. A heatmap of every L1E->L2E feedforward weight (rows = pixels 0-8,
//      columns = L2E neurons), so you can compare receptive fields across all
//      neurons in one view instead of clicking through them one at a time.
//   2. A resource-budget bar per L2E neuron, straight from the engine's own
//      dynamic_state() (n.budget / n.budget_used) -- when the active learning
//      rule doesn't use a budget (e.g. the current signed-spike default),
//      these fields are null and the row is simply omitted, not faked.

const N_PIX = 9;

export class InputWeightsOverview {
  constructor(store) {
    this.store = store;
    this.heatmapEl = document.getElementById('iw-heatmap');
    this.budgetsEl = document.getElementById('iw-budgets');
    this.nOut = 0;
    this.cells = [];   // [pixel][j] -> {el, span}
    this.built = false;
  }

  build() {
    this.nOut = (this.store.topology?.neurons || [])
      .filter(n => n.layer === 'L2' && n.type === 'E').length;
    if (!this.heatmapEl || !this.nOut) return;
    this.heatmapEl.innerHTML = '';
    this.heatmapEl.style.gridTemplateColumns = `34px repeat(${this.nOut}, 1fr)`;
    // Column header row.
    const header = document.createElement('div');
    header.className = 'iw-row';
    header.style.gridTemplateColumns = `34px repeat(${this.nOut}, 1fr)`;
    header.appendChild(document.createElement('div'));
    for (let j = 0; j < this.nOut; j++) {
      const h = document.createElement('div');
      h.className = 'iw-collabel';
      h.textContent = `L2E${j}`;
      header.appendChild(h);
    }
    this.heatmapEl.appendChild(header);
    this.cells = Array.from({ length: N_PIX }, () => []);
    for (let i = 0; i < N_PIX; i++) {
      const row = document.createElement('div');
      row.className = 'iw-row';
      row.style.gridTemplateColumns = `34px repeat(${this.nOut}, 1fr)`;
      const label = document.createElement('div');
      label.className = 'iw-rowlabel';
      label.textContent = `px ${i}`;
      row.appendChild(label);
      for (let j = 0; j < this.nOut; j++) {
        const cell = document.createElement('div');
        cell.className = 'iw-cell';
        const span = document.createElement('span');
        cell.appendChild(span);
        row.appendChild(cell);
        this.cells[i].push({ el: cell, span });
      }
      this.heatmapEl.appendChild(row);
    }
    this.built = true;
  }

  update(dyn) {
    if (!this.built) this.build();
    if (!this.built) return;
    const s = this.store;
    const cap = (s.topology?.params?.threshold_l2) || 1;
    for (let i = 0; i < N_PIX; i++) {
      for (let j = 0; j < this.nOut; j++) {
        const w = s.weights.get(`ff${i}->${j}`) ?? 0;
        const v = Math.max(0, Math.min(1, w / cap));
        const { el, span } = this.cells[i][j];
        el.style.background = v > 0.01 ? `rgba(94,234,212,${(0.08 + 0.92 * v).toFixed(3)})` : 'transparent';
        span.textContent = v >= 0.005 ? v.toFixed(2) : '';
      }
    }

    if (!this.budgetsEl) return;
    this.budgetsEl.innerHTML = '';
    for (let j = 0; j < this.nOut; j++) {
      const st = s.stateById.get(`L2E${j}`);
      if (!st || st.budget == null || st.budget_used == null) continue;
      const frac = st.budget > 0 ? Math.max(0, Math.min(1, st.budget_used / st.budget)) : 0;
      const row = document.createElement('div');
      row.className = 'iw-budget-row';
      row.innerHTML = `<span class="iw-budget-label">L2E${j}</span>
        <span class="iw-budget-track"><span class="iw-budget-fill" style="width:${(frac * 100).toFixed(1)}%"></span></span>
        <span class="iw-budget-value">${st.budget_used.toFixed(2)} / ${st.budget.toFixed(2)}</span>`;
      this.budgetsEl.appendChild(row);
    }
    if (!this.budgetsEl.children.length) {
      this.budgetsEl.innerHTML = '<div class="iw-budget-row">No per-neuron resource budget exposed by the active learning rule (budget/budget_used are null) -- nothing to show.</div>';
    }
  }
}
