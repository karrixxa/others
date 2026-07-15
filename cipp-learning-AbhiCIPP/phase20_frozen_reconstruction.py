"""
Phase 20 -- Frozen reconstruction (measurement only; adapted to the
corrected S_i/PCi/Ii local-coincidence architecture, Phase18b_Lecture14_
Local_Coincidence_Architecture_Contract.md).

The original Phase 20 spec (written against an earlier, superseded
decoder->L1E-replay topology) asked to cue one L2E/decoder and measure
reconstruction INTO L1E. That replay path does not exist in the corrected
architecture by design -- the diagram shows Pi->Ii->inhibition-of-Si, never
Pi->excitatory-replay-into-Si (Phase 18b's contract, Part 7). "The P grid
itself is the reconstructed pattern": reconstruction is measured directly
at the PCi population -- which PCi actually fire when one R_j is cued with
plasticity frozen and all external input removed.

Protocol:
  1. Train normally (prediction_column_enabled=True) with the equal-
     interleaved 20-step schedule for many cycles, letting R_j->PCi
     feedback weights develop under real physical coincidence.
  2. Identify each pattern's OWNER L2E (the one that fired most during that
     pattern's presentations).
  3. Freeze plasticity, zero external input, then CUE one L2E_j via an
     explicit experimental control (force its potential above threshold so
     it fires through the ordinary check_threshold()/fire() path -- never a
     software pass-through of PCi's state).
  4. Measure which PCi fire over the following steps: precision/recall
     against the pattern's true active-pixel set, center (pixel 4) vs
     peripheral reported SEPARATELY, persistence/decay after the cue stops,
     and confirm L2E's own potential is completely unaffected by any PCi
     activity (PCi has zero output wiring in this phase -- shadow only).

Controls: no cue; correct-owner cue; wrong-owner cue (a different pattern's
owner); shuffled-decoder cue (permute the learned R_j->PCi weights across
pixels before cueing, to confirm reconstruction quality is a property of
the LEARNED structure, not an artifact of the cueing mechanism itself).
"""

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET

CYCLE_ORDER = ['row 1', 'col 1', 'diag \\', 'diag /']
PRESENTATION_STEPS = 20
TRAIN_CYCLES = 60
CUE_STEPS = 5
OBSERVE_STEPS = 10


def _train(seed=1):
    e = SimulationEngine(seed=seed, prediction_column_enabled=True, **DASHBOARD_PRESET)
    owner_counts = {p: np.zeros(N_OUT) for p in CYCLE_ORDER}
    for _ in range(TRAIN_CYCLES):
        for pattern in CYCLE_ORDER:
            e.set_pattern(pattern)
            for _ in range(PRESENTATION_STEPS):
                e.step()
                for j in range(N_OUT):
                    if e.spiked.get(f'L2E{j}'):
                        owner_counts[pattern][j] += 1
    owners = {p: int(np.argmax(owner_counts[p])) for p in CYCLE_ORDER}
    return e, owners


def _cue_and_measure(e, cue_j, decoder_permutation=None):
    """Freeze plasticity, zero input, cue L2E_j (or no cue if cue_j is
    None), and measure PCi activity over CUE_STEPS + OBSERVE_STEPS."""
    e._set_plasticity_frozen(True)
    e.input_vec = np.zeros(N_PIX)

    saved_weights = None
    if decoder_permutation is not None:
        saved_weights = [pc._weights_array.copy() for pc in e.pcol]
        # Shuffled-decoder control: permute WHICH pixel each learned decoder
        # row targets (i -> perm[i]) -- swap the eight R_j->PCi weights
        # across columns, leaving each PCi's own fixed lateral weight (index
        # N_OUT) untouched since that identity connection is architectural,
        # never learned, never meant to be shuffled.
        rows = [pc._weights_array[:N_OUT].copy() for pc in e.pcol]
        for i, pc in enumerate(e.pcol):
            pc._weights_array[:N_OUT] = rows[decoder_permutation[i]]

    fired = np.zeros(N_PIX)
    for step_i in range(CUE_STEPS + OBSERVE_STEPS):
        if cue_j is not None and step_i < CUE_STEPS:
            e.l2.excitatory_neurons[cue_j].potential = e.l2.excitatory_neurons[cue_j].threshold + 10_000
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'PC{i}'):
                fired[i] += 1
    # "False L2E activation from PC" must isolate PC's OWN causal effect,
    # not the cue's own (expected, unrelated) L2I-competition side effects on
    # OTHER L2E neurons -- cueing L2Ej itself legitimately perturbs L2 via
    # the existing physical WTA machinery, which is not a PC-caused effect.
    # Directly force every PCi to fire and confirm zero L2E potential change
    # results (PC has no output wiring in this phase -- see Phase 19's
    # dedicated shadow-mode test, which this reproduces as a Phase 20 guard).
    l2e_before = [n.potential for n in e.l2.excitatory_neurons]
    for pc in e.pcol:
        pc.potential = pc.threshold + 10_000
        if pc.check_threshold():
            pc.fire()
    l2e_after = [n.potential for n in e.l2.excitatory_neurons]
    false_l2e_activation = any(l2e_after[j] != l2e_before[j] for j in range(N_OUT))

    if saved_weights is not None:
        for pc, w in zip(e.pcol, saved_weights):
            pc._weights_array = w

    e._set_plasticity_frozen(False)
    return fired, false_l2e_activation


def _score(pattern, fired):
    active = set(i for i, v in enumerate(PATTERNS[pattern]) if v)
    fired_set = set(np.nonzero(fired)[0].tolist())
    tp = len(fired_set & active)
    fp = len(fired_set - active)
    fn = len(active - fired_set)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    center_fired = bool(fired[4] > 0)
    peripheral = [i for i in active if i != 4]
    peripheral_recall = (sum(1 for i in peripheral if i in fired_set) / len(peripheral)
                         if peripheral else 1.0)
    return dict(precision=round(precision, 3), recall=round(recall, 3),
               center_fired=center_fired, peripheral_recall=round(peripheral_recall, 3),
               fired=fired.tolist())


def main():
    e, owners = _train(seed=1)
    print("Owners:", owners)
    results = {}

    # Control 1: no cue at all.
    fired, false_act = _cue_and_measure(e, cue_j=None)
    results['no_cue'] = dict(**_score('row 1', fired), false_l2e_activation=false_act)

    # Control 2: correct-owner cue, one per pattern.
    for pattern in CYCLE_ORDER:
        fired, false_act = _cue_and_measure(e, cue_j=owners[pattern])
        results[f'correct_cue_{pattern}'] = dict(**_score(pattern, fired), false_l2e_activation=false_act)

    # Control 3: wrong-owner cue (row 1's pattern cued with col 1's owner).
    fired, false_act = _cue_and_measure(e, cue_j=owners['col 1'])
    results['wrong_cue_row1_pattern_with_col1_owner'] = dict(**_score('row 1', fired), false_l2e_activation=false_act)

    # Control 4: shuffled decoder (row 1's owner, but decoder rows permuted).
    perm = list(np.roll(np.arange(N_PIX), 1))
    fired, false_act = _cue_and_measure(e, cue_j=owners['row 1'], decoder_permutation=perm)
    results['shuffled_decoder_row1'] = dict(**_score('row 1', fired), false_l2e_activation=false_act)

    for k, v in results.items():
        print(f"\n{k}: {v}")

    import json
    with open('phase20_reconstruction_results.json', 'w') as f:
        json.dump(dict(owners=owners, results=results), f, indent=2, default=str)
    print("\nWritten to phase20_reconstruction_results.json")


if __name__ == "__main__":
    main()
