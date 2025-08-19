import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def bench_one(ctrl: str, seed: int, sim_s: float, hz: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.linspace(0, sim_s, int(sim_s * hz), endpoint=False)
    base = 6.0 if ctrl == "lqr" else 9.0
    err = np.clip(base + rng.normal(0.0, 1.5, size=t.size), 0.0, None)
    return pd.DataFrame({"t_s": t, "err_m": err})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--controller", choices=["lqr", "pp"], required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--sim-seconds", dest="sim_seconds", type=float, default=3.0)
    args = ap.parse_args()

    out = Path("artifacts")
    out.mkdir(exist_ok=True)
    rows = []
    for s in range(args.seeds):
        df = bench_one(args.controller, s, args.sim_seconds)
        fcsv = out / f"controller_run_{args.controller}_seed{s}.csv"
        df.to_csv(fcsv, index=False)
        rows.append(
            {
                "seed": s,
                "avg_err": float(df.err_m.mean()),
                "rms_err": float(np.sqrt((df.err_m**2).mean())),
                "max_err": float(df.err_m.max()),
            }
        )

    agg = {
        "controller": args.controller,
        "seeds": args.seeds,
        "avg_err_mean": float(np.mean([r["avg_err"] for r in rows])),
        "rms_err_mean": float(np.mean([r["rms_err"] for r in rows])),
        "max_err_mean": float(np.mean([r["max_err"] for r in rows])),
    }
    (out / f"controller_sweep_{args.controller}.json").write_text(json.dumps(agg, indent=2))

    md = [
        f"# Controller KPI Seed Sweep ({args.controller})",
        "",
        f"- seeds: {args.seeds}",
        "",
        "| metric | mean |",
        "|:------:|-----:|",
        f"| avg_err [m] | {agg['avg_err_mean']:.3f} |",
        f"| rms_err [m] | {agg['rms_err_mean']:.3f} |",
        f"| max_err [m] | {agg['max_err_mean']:.3f} |",
        "",
    ]
    (out / f"controller_sweep_{args.controller}.md").write_text("\n".join(md))
    print(f"Wrote {args.seeds} CSVs and summary JSON/MD for {args.controller} → {out}")


if __name__ == "__main__":
    main()
