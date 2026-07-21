// Pure label helpers (Phase 14). No DOM dependency -- kept in their own
// module so they're directly testable (see test_phase14_logic.mjs).

// "First responder" (dyn.winner) is null both when no presentation response
// has occurred yet AND when the first physical L2E threshold crossing was an
// ambiguous same-step tie (backend: self.winner stays None for the whole
// presentation on a tie -- see causal_story.same_step_tie, which is recorded
// even during the tie). Distinguish the two cases here rather than showing
// the same generic dash for both.
export function firstResponderLabel(dyn, short = false) {
  if (dyn.winner) return dyn.winner;
  if (dyn.causal_story?.same_step_tie) return short ? 'Ambiguous' : 'Ambiguous first response';
  return '—';
}

export function predictionOutputStateLabel(predCol) {
  if (!predCol?.enabled) return 'OFF';
  if (predCol.output_delivery_enabled && predCol.persistent_conductance_enabled) return 'persistent';
  if (predCol.output_delivery_enabled) return 'instantaneous';
  return 'shadow';
}

export function detectPatternLabel(input = [], patternVectors = {}, probeVectors = {}) {
  const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
  for (const [name, vec] of Object.entries(patternVectors)) if (same(input, vec)) return name;
  for (const [name, vec] of Object.entries(probeVectors)) if (same(input, vec)) return name;
  return 'manual';
}
