// Pure mapping helpers for the View Controls visibility filters (Phase 14).
// No DOM/three.js dependency -- kept in their own module so they're directly
// testable (see test_phase14_logic.mjs) without needing a browser or the
// three.js import map renderer.js otherwise requires.

// layer ('L1'|'L2') + type ('E'|'I') -> the filter key that gates that
// population's visibility in NeuronRenderer.filters (e.g. 'L1','E' -> 'l1e').
export function layerKey(layer, type) {
  return (layer + type).toLowerCase();
}

// Synapse `kind` -> the filter key that gates that edge category.
// backend/simulation.py:1390-1406 is the source of truth for kind assignment:
//   feedforward       L1E -> L2E
//   excitation         L2E -> L2I
//   reset_inhibition   L2I -> L2E
//   feedback           L2E -> L1I
//   inhibition         L1I -> L1E
export function edgeKey(kind) {
  switch (kind) {
    case 'feedforward': return 'edgeFeedforward';
    case 'excitation': return 'edgeL2eL2i';
    case 'reset_inhibition': return 'edgeL2iL2e';
    case 'feedback': return 'edgeL2eL1i';
    case 'inhibition': return 'edgeL1iL1e';
    default: return null;
  }
}
