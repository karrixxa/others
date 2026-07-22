"""Probe simulator metrics used by frontend charts."""

from cognative_paradigm.simulation.engine import BrainSimulator


def main() -> None:
    sim = BrainSimulator()
    for _ in range(40):
        result = sim.stimulate_line()
        state = sim.get_state()
        winner_id = result.winner_neuron_id
        winner = (
            next((n for n in state["nucleus"]["ring"] if n["id"] == winner_id), None)
            if winner_id
            else None
        )
        bound_events = [e for e in result.step_events if e["type"] == "PATTERN_BOUND"]
        if bound_events or result.timestep <= 3 or result.timestep % 5 == 0:
            learned = len(state["training"]["learned_line_ids"])
            mem = winner["membrane"] if winner else None
            reg = winner["register"] if winner else None
            bind = winner["bind_progress"] if winner else None
            peak_reg = max((n["register"] for n in state["nucleus"]["ring"]), key=lambda r: 1 if r == "1" else 0)
            peak_mem = max(n["membrane"] for n in state["nucleus"]["ring"])
            print(
                f"t={result.timestep} line={result.line_id} learned={learned} "
                f"winner={winner_id} reg={reg} mem={mem} bind={bind} "
                f"peak_mem={peak_mem} any_spike={peak_reg}"
            )


if __name__ == "__main__":
    main()
