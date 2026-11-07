"""04 결과에서 유형별 F1의 B − A 차이 계산 (새 실험 없음, 저장된 결과만 사용).

- 입력: results/04_lot_split_fold_runs.csv (04_lot_split.py 출력)
- 분할(무작위/lot)마다 같은 fold·같은 random_state끼리 A와 B를 짝지어(50쌍) 유형별 F1 차이를 계산한다.
- 열 설명
    A_f1, B_f1           : 50쌍 평균 F1
    delta_B_minus_A      : 50쌍의 (B − A) 평균
    delta_sd             : 50쌍 (B − A)의 표본 표준편차
    pairs_B_better / pairs_A_better / pairs_tie : 50쌍 중 B가 높은 / A가 높은 / 같은 쌍 수
    seeds_B_better       : random_state마다 5-fold의 (B − A) 평균을 냈을 때 양수인 개수 (10개 중)
    seed_delta_min/max   : 위 10개 값의 최솟값/최댓값
    folds_B_better       : fold마다 10개 random_state의 (B − A) 평균을 냈을 때 양수인 개수 (5개 중)
    fold_delta_min/max   : 위 5개 값의 최솟값/최댓값
- 출력: results/04_lot_split_class_delta.csv

실행: .venv/bin/python scripts/04_lot_split_class_delta.py
"""

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "04_lot_split_fold_runs.csv"
OUT = ROOT / "results" / "04_lot_split_class_delta.csv"
SPLITS = ("random", "lot")
N_FOLDS, N_SEEDS = 5, 10


def main():
    with open(RUNS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    classes = [c[3:] for c in rows[0] if c.startswith("f1_")]

    out = []
    for split in SPLITS:
        runs = {m: {(r["fold"], r["seed"]): r for r in rows if r["split"] == split and r["model"] == m}
                for m in ("A", "B")}
        keys = sorted(runs["A"])
        if len(keys) != N_FOLDS * N_SEEDS or set(keys) != set(runs["B"]):
            raise RuntimeError(f"{split}: A/B 짝이 {N_FOLDS * N_SEEDS}쌍이 아니에요 ({len(keys)})")
        for c in classes:
            a = np.array([float(runs["A"][k][f"f1_{c}"]) for k in keys])
            b = np.array([float(runs["B"][k][f"f1_{c}"]) for k in keys])
            if np.isnan(a).any() or np.isnan(b).any():
                raise RuntimeError(f"{split}/{c}: F1에 NaN이 있어요 (테스트 fold에 유형 없음)")
            d = b - a
            seed_d = [d[[k[1] == str(s) for k in keys]].mean() for s in range(N_SEEDS)]
            fold_d = [d[[k[0] == str(f) for k in keys]].mean() for f in range(N_FOLDS)]
            out.append({
                "split": split, "type": c,
                "A_f1": round(a.mean(), 4), "B_f1": round(b.mean(), 4),
                "delta_B_minus_A": round(d.mean(), 4), "delta_sd": round(d.std(ddof=1), 4),
                "pairs_B_better": int((d > 0).sum()), "pairs_A_better": int((d < 0).sum()),
                "pairs_tie": int((d == 0).sum()),
                "seeds_B_better": int(sum(x > 0 for x in seed_d)),
                "seed_delta_min": round(min(seed_d), 4), "seed_delta_max": round(max(seed_d), 4),
                "folds_B_better": int(sum(x > 0 for x in fold_d)),
                "fold_delta_min": round(min(fold_d), 4), "fold_delta_max": round(max(fold_d), 4),
            })

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(f"{r['split']:6s} {r['type']:10s} A {r['A_f1']:.3f} B {r['B_f1']:.3f} "
              f"Δ {r['delta_B_minus_A']:+.3f}  {r['pairs_B_better']}/{r['pairs_A_better']}/{r['pairs_tie']}  "
              f"seed {r['seeds_B_better']}/10  fold {r['folds_B_better']}/5")


if __name__ == "__main__":
    main()
