// Focused tests for Phase 14's UI-observability pure logic (View Controls
// filter mapping, First-responder/Ambiguous labeling). No DOM, no three.js,
// no new dependency -- these modules are deliberately dependency-free (see
// edge_filters.js/labels.js) so they run under Node's own built-in test
// runner: `node --test frontend/test_phase14_logic.mjs`.
//
// This is the practical shape of "add focused tests" for this codebase: the
// frontend has no build step, no test framework, and every other module is
// tightly coupled to the DOM or three.js's browser-only import map, so this
// covers what CAN be tested in isolation rather than force-fitting a browser
// test harness the project doesn't otherwise have.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { layerKey, edgeKey } from './edge_filters.js';
import { firstResponderLabel } from './labels.js';

test('layerKey maps layer+type to the View Controls filter key', () => {
  assert.equal(layerKey('L1', 'E'), 'l1e');
  assert.equal(layerKey('L1', 'I'), 'l1i');
  assert.equal(layerKey('L2', 'E'), 'l2e');
  assert.equal(layerKey('L2', 'I'), 'l2i');
});

test('edgeKey maps every backend synapse kind to its edge filter key', () => {
  // backend/simulation.py:1390-1406 is the source of truth for these five
  // kinds; a sixth/unknown kind must not silently match a real filter.
  assert.equal(edgeKey('feedforward'), 'edgeFeedforward');
  assert.equal(edgeKey('excitation'), 'edgeL2eL2i');
  assert.equal(edgeKey('reset_inhibition'), 'edgeL2iL2e');
  assert.equal(edgeKey('feedback'), 'edgeL2eL1i');
  assert.equal(edgeKey('inhibition'), 'edgeL1iL1e');
  assert.equal(edgeKey('nonsense'), null);
});

test('firstResponderLabel returns the winner id when one exists', () => {
  const dyn = { winner: 'L2E3', causal_story: { same_step_tie: false } };
  assert.equal(firstResponderLabel(dyn), 'L2E3');
  assert.equal(firstResponderLabel(dyn, true), 'L2E3');
});

test('firstResponderLabel distinguishes an ambiguous tie from no-responder-yet', () => {
  const tied = { winner: null, causal_story: { same_step_tie: true } };
  assert.equal(firstResponderLabel(tied), 'Ambiguous first response');
  assert.equal(firstResponderLabel(tied, true), 'Ambiguous');

  const none = { winner: null, causal_story: { same_step_tie: false } };
  assert.equal(firstResponderLabel(none), '—');

  const noStory = { winner: null };
  assert.equal(firstResponderLabel(noStory), '—');
});
