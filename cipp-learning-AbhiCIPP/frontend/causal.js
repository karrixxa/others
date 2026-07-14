// Causal Story tab: a pure renderer of the backend's own presentation tracking
// (dyn.causal_story -- see SimulationEngine._start_presentation/_track_presentation).
// Every field here is read directly off that object. This module computes
// nothing about the simulation itself -- no first-spike detection, no tie
// detection, no source attribution -- it only formats what the engine already
// decided from real, already-occurred physical events.

export class CausalStory {
  constructor(store) {
    this.store = store;
    this.current = document.getElementById('causal-current');
    this.history = document.getElementById('causal-history');
  }

  update(dyn) {
    if (!this.current || !this.history) return;
    const s = dyn.causal_story;
    if (!s) return;

    this.current.innerHTML = [
      tile('Presentation', `#${s.presentation_id}`),
      tile('Pattern', s.pattern, s.role === 'probe' ? 'var(--inh)' : 'var(--accent)'),
      tile('Role', s.role, s.role === 'probe' ? 'var(--inh)' : 'var(--accent)'),
      tile('Plasticity', s.plasticity_frozen ? 'FROZEN' : 'learning', s.plasticity_frozen ? 'var(--inh)' : 'var(--ok)'),
      tile('First L2E responder', s.first_spiker ?? '—'),
      tile('First-spike step', s.first_spike_t ?? '—'),
      tile('Same-step tie', s.same_step_tie ? 'yes' : 'no', s.same_step_tie ? 'var(--win)' : null),
      tile('First L1I source', s.l1i_first_source ?? '—'),
      tile('First L1I step', s.l1i_first_t ?? '—'),
      tile('L2I threshold source', s.l2i_first_source ?? '—'),
      tile('L2I threshold step', s.l2i_first_t ?? '—'),
    ].join('');

    this.history.innerHTML = (s.history || []).slice().reverse().map(row => `
      <div class="causal-row">
        <span class="cr-pattern">${row.pattern}</span>
        <span class="cr-role ${row.role}">${row.role}</span>
        <span class="cr-dim">#${row.id} · t${row.start_t}-${row.end_t}</span>
        <span>first: <b>${row.first_spiker ?? '—'}</b>${row.first_spike_t != null ? ` @t${row.first_spike_t}` : ''}</span>
        ${row.same_step_tie ? '<span class="cr-tie">tie</span>' : ''}
        <span class="cr-dim">L1I: ${row.l1i_first_source ?? '—'}</span>
        <span class="cr-dim">L2I: ${row.l2i_first_source ?? '—'}</span>
      </div>`).join('') || '<p class="cr-dim" style="color:var(--txt-2);font-size:11px">no completed presentations yet</p>';
  }
}

function tile(label, value, color) {
  return `<div class="icard">
    <div class="lbl">${label}</div>
    <div class="val sm"${color ? ` style="color:${color}"` : ''}>${value}</div>
  </div>`;
}
