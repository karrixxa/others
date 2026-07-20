import json
import glob

SEEDS = [1, 3, 10, 14, 17, 22]
RESULTS_DIR = "/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/mature_efficacy_results"


def load(seed):
    return json.load(open(f"{RESULTS_DIR}/seed_{seed}.json"))


def pc_total(spikes):
    return sum(spikes.values())


def main():
    rows = []
    for seed in SEEDS:
        d = load(seed)
        s1 = d["stage1"]
        b1 = d["stage2"]["B_shadow"]["continued_held"]
        c1 = d["stage2"]["C_active"]["continued_held"]
        b2 = d["stage2"]["B_shadow"]["pattern_switch"]
        c2 = d["stage2"]["C_active"]["pattern_switch"]

        row = dict(
            seed=seed,
            leader=f"L2E{s1['final_leader']}",
            tied=s1["final_tied"],
            matured_step=s1["matured_step"],
            decoder_events=s1["decoder_update_events"],
            independence_ok=d["independence_check"]["ok"],
            test3_ran=d["stage2"]["B_shadow"]["test3_ran"] and d["stage2"]["C_active"]["test3_ran"],

            b_pc_spikes_held=pc_total(b1["pc_spikes"]),
            c_pc_spikes_held=pc_total(c1["pc_spikes"]),
            b_l1e_expected_held=f"{b1['l1e_expected_fires']}/{b1['l1e_expected_opportunities']}",
            c_l1e_expected_held=f"{c1['l1e_expected_fires']}/{c1['l1e_expected_opportunities']}",
            b_l1e_expected_rate_held=round(b1['l1e_expected_fires']/b1['l1e_expected_opportunities'], 4),
            c_l1e_expected_rate_held=round(c1['l1e_expected_fires']/c1['l1e_expected_opportunities'], 4),
            b_l1i_events_held=b1["l1i_events"],
            c_l1i_events_held=c1["l1i_events"],
            b_multi_winner_held=b1["multi_winner_steps"],
            c_multi_winner_held=c1["multi_winner_steps"],

            b_pc_spikes_switch=pc_total(b2["pc_spikes"]),
            c_pc_spikes_switch=pc_total(c2["pc_spikes"]),
            b_l1e_expected_rate_switch=round(b2['l1e_expected_fires']/b2['l1e_expected_opportunities'], 4) if b2['l1e_expected_opportunities'] else None,
            c_l1e_expected_rate_switch=round(c2['l1e_expected_fires']/c2['l1e_expected_opportunities'], 4) if c2['l1e_expected_opportunities'] else None,
            b_l1e_novel_rate_switch=round(b2['l1e_novel_fires']/b2['l1e_novel_opportunities'], 4) if b2['l1e_novel_opportunities'] else None,
            c_l1e_novel_rate_switch=round(c2['l1e_novel_fires']/c2['l1e_novel_opportunities'], 4) if c2['l1e_novel_opportunities'] else None,
            b_stale_switch=b2["stale_counts"],
            c_stale_switch=c2["stale_counts"],
        )
        rows.append(row)

    print(f"{'seed':>5} {'leader':>6} {'tied':>5} {'mat_step':>9} {'B_pc':>6} {'C_pc':>6}  "
          f"{'B_l1e_exp':>10} {'C_l1e_exp':>10}  {'B_l1i_ev':>9} {'C_l1i_ev':>9}")
    for r in rows:
        print(f"{r['seed']:>5} {r['leader']:>6} {str(r['tied']):>5} {r['matured_step']:>9} "
              f"{r['b_pc_spikes_held']:>6} {r['c_pc_spikes_held']:>6}  "
              f"{r['b_l1e_expected_rate_held']:>10} {r['c_l1e_expected_rate_held']:>10}  "
              f"{r['b_l1i_events_held']:>9} {r['c_l1i_events_held']:>9}")

    print()
    print("=== pattern-switch test ===")
    print(f"{'seed':>5} {'B_pc':>6} {'C_pc':>6} {'B_exp_rate':>10} {'C_exp_rate':>10} {'B_nov_rate':>10} {'C_nov_rate':>10}")
    for r in rows:
        print(f"{r['seed']:>5} {r['b_pc_spikes_switch']:>6} {r['c_pc_spikes_switch']:>6} "
              f"{str(r['b_l1e_expected_rate_switch']):>10} {str(r['c_l1e_expected_rate_switch']):>10} "
              f"{str(r['b_l1e_novel_rate_switch']):>10} {str(r['c_l1e_novel_rate_switch']):>10}")

    print()
    print("=== stale classification, pattern-switch test ===")
    for r in rows:
        print(f"seed={r['seed']} B={r['b_stale_switch']} C={r['c_stale_switch']}")

    print()
    print("=== independence / test3 sanity ===")
    for r in rows:
        print(f"seed={r['seed']} independence_ok={r['independence_ok']} test3_ran={r['test3_ran']} "
              f"decoder_events={r['decoder_events']}")

    with open(f"{RESULTS_DIR}/aggregate_rows.json", "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    main()
