"""Regression tests for a subtle interaction the comments used to describe
wrong (see the 2026-07-13 comment fix in backend/simulation.py's
signed_spike_learning docstring):

  - signed_spike_learning=True DOES bypass the separate signed_depression
    ("4a" OFF-gate) block in Neuron._update_weights -- that method's signed
    branch returns before reaching it.
  - signed_spike_learning=True does NOT bypass loser_depression/eta_loss --
    that mechanism lives entirely in Neuron.apply_inhibition (_depress_losers),
    an independent code path triggered by a real inhibitory-discharge event,
    not by _update_weights' postsynaptic-fire branch.

These tests exercise the Neuron class directly (no SimulationEngine / L2
competition needed) so the causal event that matters -- a genuine inhibitory
discharge -- is fully under the test's control.
"""

from neuron_flexible import Neuron


def _make_neuron(signed_spike_learning=False, signed_depression=False, eta_off=0.2,
                  loser_depression=False, eta_loss=0.01):
    n = Neuron(threshold=1000, refractory_period=0, learning_rate=0.05,
               weight_cap=1000, leak_rate=0)
    n.add_input_connection(0.0)   # one positive feedforward afferent (index 0)
    n.add_input_connection(0.0)   # one inhibitory afferent (index 1, set negative below)
    n.finalize_connections()
    n._weights_array[0] = 500.0     # positive feedforward synapse
    n._weights_array[1] = -100.0    # inhibitory synapse (negative sign = inhibitory)
    # These flags are plain attributes (set by SimulationEngine._build() from its
    # own params dict, not Neuron constructor kwargs) -- set them the same way here.
    n.signed_spike_learning = signed_spike_learning
    n.signed_depression = signed_depression
    n.eta_off = eta_off
    n.loser_depression = loser_depression
    n.eta_loss = eta_loss
    return n


def test_signed_spike_learning_bypasses_signed_depression():
    """With signed_spike_learning=True, an OFF (non-participating) positive
    synapse is governed ENTIRELY by the signed rule's own -1 branch; the
    separate signed_depression block must never additionally fire (no double
    depression, no signed_depression_events increment)."""
    n = _make_neuron(signed_spike_learning=True, signed_depression=True, eta_off=0.5)
    n.potential = 1000.0
    # Fire with input 0 (this neuron's only positive afferent) INACTIVE this
    # volley, so it takes the signed rule's -1 branch.
    n._last_input_spikes = __import__("numpy").array([0.0, 0.0])
    w_before = float(n._weights_array[0])
    events_before = n.signed_depression_events
    n._update_weights(v_pre=1000.0)
    assert n.signed_depression_events == events_before, (
        "signed_depression_events incremented -- signed_spike_learning did not "
        "bypass the separate signed_depression block as documented")
    w_after = float(n._weights_array[0])
    # The signed rule's own -1 branch should still have moved the weight (it's
    # the ONLY depression mechanism active here), just not via signed_depression.
    assert w_after < w_before, "expected the signed rule's own -1 branch to depress the OFF synapse"


def test_loser_depression_not_bypassed_by_signed_spike_learning():
    """loser_depression must still fire (via apply_inhibition -> _depress_losers)
    even when signed_spike_learning=True, because it is not part of
    _update_weights at all."""
    n = _make_neuron(signed_spike_learning=True, loser_depression=True, eta_loss=5.0)
    n.potential = 900.0   # close to threshold -- a real "near-winner" being suppressed
    n._last_input_spikes = __import__("numpy").array([1.0, 0.0])  # positive synapse participated
    w_before = float(n._weights_array[0])
    events_before = n.loser_depression_events
    # A real inhibitory discharge: afferent index 1 (negative weight) spikes.
    n.apply_inhibition(__import__("numpy").array([0.0, 1.0]))
    assert n.loser_depression_events == events_before + 1, (
        "loser_depression did not fire on a genuine inhibitory discharge -- "
        "signed_spike_learning must not bypass it (it lives in apply_inhibition, "
        "not _update_weights)")
    w_after = float(n._weights_array[0])
    assert w_after < w_before, "expected the participating positive synapse to be depressed"


def test_eta_loss_changes_loser_weight_magnitude_under_signed_spike_learning():
    """Changing eta_loss (with everything else fixed) must change how much a
    loser's participating synapse is depressed by a single inhibitory event --
    this is the mechanism the eta_loss A/B comparison in
    single_pattern_diagnostic.py relies on."""
    import numpy as np

    def _depression_amount(eta_loss):
        n = _make_neuron(signed_spike_learning=True, loser_depression=True, eta_loss=eta_loss)
        n.potential = 900.0
        n._last_input_spikes = np.array([1.0, 0.0])
        w_before = float(n._weights_array[0])
        n.apply_inhibition(np.array([0.0, 1.0]))
        return w_before - float(n._weights_array[0])

    small = _depression_amount(0.01)
    large = _depression_amount(10.0)
    assert large > small, (
        f"expected a larger eta_loss to depress more (got {small=} {large=}) -- "
        "eta_loss should have a real, monotonic effect on loser weights")


def test_no_loser_depression_without_a_real_inhibitory_event():
    """If no inhibitory afferent actually spikes this step, _depress_losers must
    not run at all -- loser depression is strictly gated on a genuine discharge,
    never a background/no-op call."""
    import numpy as np

    n = _make_neuron(signed_spike_learning=True, loser_depression=True, eta_loss=10.0)
    n.potential = 900.0
    n._last_input_spikes = np.array([1.0, 0.0])
    w_before = float(n._weights_array[0])
    events_before = n.loser_depression_events
    # No inhibitory afferent spikes this call (all zeros) -- apply_inhibition
    # should find nothing to discharge and never invoke _depress_losers.
    n.apply_inhibition(np.array([0.0, 0.0]))
    assert n.loser_depression_events == events_before, (
        "loser_depression_events incremented with no real inhibitory discharge")
    assert float(n._weights_array[0]) == w_before, "weight moved without a real inhibitory event"


if __name__ == "__main__":
    test_signed_spike_learning_bypasses_signed_depression()
    test_loser_depression_not_bypassed_by_signed_spike_learning()
    test_eta_loss_changes_loser_weight_magnitude_under_signed_spike_learning()
    test_no_loser_depression_without_a_real_inhibitory_event()
    print("ALL SIGNED-SPIKE / LOSER-DEPRESSION BYPASS TESTS PASSED")
