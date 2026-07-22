"""L5 biological prediction after mastery / Path 2 local END evidence."""

from __future__ import annotations

from cognative_paradigm.api.service import BrainService, ParametersPatch
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.stimulus_stream import MasteryPhase


def _bind_catalog(service: BrainService) -> None:
    """Enough catalog passes for Path 1 bind on all four lines (Stage 11 eligible N=2)."""
    for _ in range(4):
        for line_id in LINE_IDS:
            service.stimulate(line_id)


class TestBiologicalL5AfterMastery:
    def test_catalog_refire_predicts_successors_after_bind_and_transitions(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
            )
        )
        _bind_catalog(service)
        # Extra passes build recurrent STDP along the catalog chain.
        for _ in range(6):
            for line_id in LINE_IDS:
                service.stimulate(line_id)

        expected = {"H1": "V1", "V1": "D0", "D0": "D1"}
        for line_id, successor in expected.items():
            payload = service.stimulate(line_id)
            prediction = payload["state"]["cortical_column"]["next_prediction"]
            assert prediction["is_unknown"] is False, (
                f"{line_id} → {prediction} diagnostic="
                f"{payload['state']['cortical_column'].get('prediction_diagnostic')}"
            )
            assert prediction["predicted_line_id"] == successor

    def test_end_episode_on_h1_records_local_end_without_d1_gate(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
            )
        )
        _bind_catalog(service)
        for _ in range(4):
            for line_id in LINE_IDS:
                service.stimulate(line_id)
        service.stimulate("H1")
        service.end_column_episode()

        assemblies = service.simulator.cortical_column._context.assemblies
        h1 = next(a for a in assemblies if a.metadata_label == "H1")
        assert h1.boundary_end_evidence > 0.0

        prediction = service.stimulate("H1")["state"]["cortical_column"][
            "next_prediction"
        ]
        assert prediction.get("is_episode_end") is not True
        assert prediction["predicted_line_id"] == "V1"

    def test_end_episode_on_d1_binds_local_end(self) -> None:
        """Episodic catalog training: END after each pass so D1→H1 wrap STDP
        does not outcompete local END evidence (metric-pack / OrderedColumnEpisodeStream).
        """
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
            )
        )
        # Bind with continuous passes first (N=2 Path 1), then train episodically.
        _bind_catalog(service)
        for _ in range(4):
            for line_id in LINE_IDS:
                service.stimulate(line_id)
            service.end_column_episode()
        assemblies = service.simulator.cortical_column._context.assemblies
        d1 = next(a for a in assemblies if a.metadata_label == "D1")
        assert d1.boundary_end_evidence > 0.0

        for line_id in LINE_IDS:
            service.stimulate(line_id)
        prediction = service.get_state()["cortical_column"]["next_prediction"]
        assert prediction["is_episode_end"] is True
        assert prediction["predicted_line_id"] == "END"

    def test_mastery_probe_does_not_create_plural_unknown_storm(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
                ecological_stimulus_mode="mastery",
            )
        )

        for _ in range(400):
            payload = service.stimulate_auto()
            training = payload["state"]["training"]
            if (
                len(training.get("observed_line_ids") or []) == 4
                and training.get("auto_stim_phase") == MasteryPhase.PROBE.value
            ):
                break
        else:
            raise AssertionError("mastery did not reach probe with 4/4 learned")

        assert service._column_recurrent_plasticity_enabled() is False

        unknown = 0
        plural_ties = 0
        total = 40
        for _ in range(total):
            payload = service.stimulate_auto()
            prediction = payload["state"]["cortical_column"]["next_prediction"]
            diagnostic = payload["state"]["cortical_column"].get(
                "prediction_diagnostic"
            )
            if prediction.get("is_unknown"):
                unknown += 1
                if diagnostic and diagnostic.get("reason") == "plural_tie":
                    plural_ties += 1

        assert plural_ties == 0, "mastery probe must not invent plural-tie UNKNOWN"
        assert unknown <= 25, f"unexpected UNKNOWN rate after mastery: {unknown}/{total}"

        simulator = service.simulator
        for line_id, expected in (("H1", "V1"), ("V1", "D0"), ("D0", "D1")):
            simulator.stimulate_pattern(
                get_line(line_id),
                line_id=line_id,
                recurrent_plasticity=False,
            )
            prediction = simulator.get_state()["cortical_column"]["next_prediction"]
            assert prediction["is_unknown"] is False
            assert prediction["predicted_line_id"] == expected

    def test_h1_unknown_only_until_v1_follows_once(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
            )
        )
        # Stage 11: bind evidence only advances when coincidence-eligible
        # (self-prior apical). First unique win has zero apical → N=2 bind
        # needs three same-line unique wins.
        service.stimulate("H1")
        service.stimulate("H1")
        first = service.stimulate("H1")["state"]["cortical_column"]
        assert first["next_prediction"]["is_unknown"] is True

        service.stimulate("V1")
        service.stimulate("V1")
        service.stimulate("V1")
        again = service.stimulate("H1")["state"]["cortical_column"]
        assert again["next_prediction"]["is_unknown"] is False
        assert again["next_prediction"]["predicted_line_id"] == "V1"
