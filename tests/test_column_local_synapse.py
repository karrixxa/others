"""Stage 4 — local sensory synapse unit tests."""

from cognative_paradigm.domain.column_profile import FireTogetherWindow
from cognative_paradigm.domain.local_synapse import LocalSensorySynapse
from cognative_paradigm.learning.spike_timing_plasticity import (
    SpikeTimingPlasticityConfig,
)


class TestColumnLocalSynapse:
    def test_hebbian_update_requires_pre_and_post(self) -> None:
        synapse = LocalSensorySynapse(
            source_cell_index=4,
            receiver_id="repr_0",
            weight=0.35,
            eta=0.05,
        )
        window = FireTogetherWindow.from_stdp_defaults()
        assert (
            synapse.try_hebbian_update(
                pre_fired=True,
                post_fired=False,
                pre_timestep=1,
                post_timestep=1,
                window=window,
            )
            is None
        )
        assert synapse.weight == 0.35

    def test_hebbian_update_records_provenance(self) -> None:
        synapse = LocalSensorySynapse(
            source_cell_index=4,
            receiver_id="repr_0",
            weight=0.35,
            eta=0.05,
        )
        window = FireTogetherWindow.from_stdp_defaults()
        provenance = synapse.try_hebbian_update(
            pre_fired=True,
            post_fired=True,
            pre_timestep=3,
            post_timestep=3,
            window=window,
        )
        assert provenance is not None
        assert provenance.receiver_id == "repr_0"
        assert provenance.source_id == "l4_4"
        assert provenance.pre_event_timestep == 3
        assert provenance.post_event_timestep == 3
        assert provenance.delta_w > 0.0
        assert synapse.weight == provenance.weight_after
        assert synapse.weight <= synapse.w_max

    def test_weight_clamped_to_bounds(self) -> None:
        synapse = LocalSensorySynapse(
            source_cell_index=0,
            receiver_id="repr_1",
            weight=1.99,
            eta=0.5,
            w_max=2.0,
        )
        window = FireTogetherWindow.from_stdp_defaults()
        synapse.try_hebbian_update(
            pre_fired=True,
            post_fired=True,
            pre_timestep=1,
            post_timestep=1,
            window=window,
        )
        assert synapse.weight == 2.0

    def test_fire_together_window_matches_stdp_defaults(self) -> None:
        window = FireTogetherWindow.from_stdp_defaults()
        cfg = SpikeTimingPlasticityConfig()
        assert window.tau_plus_ms == cfg.tau_plus_ms
        assert window.tau_minus_ms == cfg.tau_minus_ms
        assert window.coincident_dt_ms == cfg.coincident_dt_ms
        assert window.tau_plus_ms == 20.0
        assert window.coincident_dt_ms == 1.0

    def test_outside_timing_window_no_update(self) -> None:
        synapse = LocalSensorySynapse(
            source_cell_index=1,
            receiver_id="repr_0",
            weight=0.35,
            eta=0.05,
        )
        window = FireTogetherWindow(
            tau_plus_ms=2.0,
            tau_minus_ms=2.0,
            coincident_dt_ms=1.0,
        )
        result = synapse.try_hebbian_update(
            pre_fired=True,
            post_fired=True,
            pre_timestep=1,
            post_timestep=10,
            window=window,
        )
        assert result is None
        assert synapse.weight == 0.35
