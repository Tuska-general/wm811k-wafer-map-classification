"""04: lot 단위 분할 vs 무작위 분할 비교 (baseline / A / B).

1) 7:3 무작위 분할(test_size=0.3, random_state=42, stratify)에서 테스트 271장 중
   학습셋과 같은 lot을 공유하는 웨이퍼 수를 유형별로 센다.
2) 5-fold 두 가지
   - lot 분할: StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42), 그룹 = lotName
     (data/wafer_lot_map.csv)
   - 무작위 분할: StratifiedKFold(n_splits=5, shuffle=True, random_state=42), lot 무시
3) fold마다 학습셋으로만 near full 임계값과 템플릿을 다시 만든다(01 함수).
   - baseline: 01의 규칙+템플릿 예측
   - A: [면적 비율, 상관계수 8개] (03과 같음, 계산 불가 상관계수 = -1.0)
   - B: 03b의 8월 원문 방식 [면적 비율, 덩어리 개수, 최대 덩어리 비율, min(신장도, 50), 상관계수 8개]
   - A와 B는 RandomForest(n_estimators=300, max_depth=8, min_samples_leaf=2)의 random_state를 0~9로 바꿔 10번씩
4) 집계 (보고서에 정의를 같이 적음)
   - fold 정확도: A/B는 fold마다 10개 random_state의 평균을 낸 뒤, 5개 fold의 평균±표준편차
   - random_state 흔들림: random_state마다 5-fold 평균 정확도를 구해, 10개 값의 표준편차
   - 유형별 F1: fold별 F1을 fold(와 random_state) 전체로 평균. 테스트 fold에 그 유형이 없으면 그 fold는 빼고 평균
   - B-A 차이: 같은 fold·같은 random_state끼리 짝지어 뺀 값
결과: results/04_lot_split_*  (01, 03, 03b 결과 파일은 건드리지 않음)

실행: .venv/bin/python scripts/04_lot_split.py
"""

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold, train_test_split

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
LOT_MAP = ROOT / "data" / "wafer_lot_map.csv"
PREFIX = "04_lot_split_"

N_SPLITS = 5
CV_RANDOM_STATE = 42
RF_SEEDS = list(range(10))
RF_BASE = dict(n_estimators=300, max_depth=8, min_samples_leaf=2)  # random_state는 0~9로 바꿈


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


aug = _load("rf03b", "03b_randomforest_aug.py")
rf03 = aug.rf03
b = aug.b


def load_lots(files):
    """파일 이름 순서에 맞춰 lotName 배열을 만든다. 902장이 모두 짝지어지는지 확인."""
    with open(LOT_MAP, encoding="utf-8") as f:
        rows = {r["file_name"]: r for r in csv.DictReader(f)}
    missing = [x for x in files if x not in rows]
    if missing or len(rows) != len(files):
        raise RuntimeError(f"lot 매핑 불일치: 없는 파일 {len(missing)}개, 매핑 {len(rows)}행 / 이미지 {len(files)}장")
    return np.array([rows[x]["lotName"] for x in files])


def overlap_7030(labels, lots, class_names):
    """7:3 분할에서 테스트 웨이퍼 중 학습셋에 같은 lot이 있는 장수 (유형별)."""
    tr, te = train_test_split(
        np.arange(len(labels)), test_size=b.TEST_SIZE, random_state=b.RANDOM_STATE, stratify=labels
    )
    train_lots = set(lots[tr])
    shared = np.array([lots[i] in train_lots for i in te])
    rows = []
    for c in class_names + ["전체"]:
        sel = np.ones(len(te), bool) if c == "전체" else labels[te] == c
        rows.append({"type": c, "test_n": int(sel.sum()), "shared_lot_n": int(shared[sel].sum()),
                     "shared_pct": round(100 * shared[sel].mean(), 1),
                     "test_lots": int(len(set(lots[te][sel]))),
                     "test_lots_in_train": int(len(set(lots[te][sel & shared])))})
    return rows


def fold_metrics(y_true, y_pred, class_names):
    present = set(y_true)
    out = {"acc": float(accuracy_score(y_true, y_pred))}
    f1 = f1_score(y_true, y_pred, labels=class_names, average=None, zero_division=0)
    pr = precision_score(y_true, y_pred, labels=class_names, average=None, zero_division=0)
    rc = recall_score(y_true, y_pred, labels=class_names, average=None, zero_division=0)
    for c, f, p, r in zip(class_names, f1, pr, rc):
        # 테스트 fold에 그 유형이 없으면 F1/recall은 정의되지 않으므로 NaN
        out[f"f1_{c}"] = float(f) if c in present else float("nan")
        out[f"recall_{c}"] = float(r) if c in present else float("nan")
        out[f"precision_{c}"] = float(p)
    return out


def run_split(split_name, splitter, labels, lots, masks, ratios, dcount, shape_aug, class_names):
    """한 분할 방식의 5개 fold 전체를 돌린다. fold별 기록과 누적 혼동행렬을 돌려준다."""
    groups = lots if split_name == "lot" else None
    runs, folds_info = [], []
    cms = {m: np.zeros((len(class_names),) * 2, dtype=np.int64) for m in ("baseline", "A", "B")}
    for k, (tr, te) in enumerate(splitter.split(np.zeros(len(labels)), labels, groups)):
        shared_lots = set(lots[tr]) & set(lots[te])
        if split_name == "lot" and shared_lots:
            raise RuntimeError(f"lot 분할 fold {k}에서 lot이 겹쳐요: {len(shared_lots)}개")
        y_tr, y_te = labels[tr], labels[te]
        folds_info.append({"split": split_name, "fold": k, "n_train": len(tr), "n_test": len(te),
                           "shared_lots": len(shared_lots),
                           "test_wafers_sharing_lot": int(np.isin(lots[te], list(set(lots[tr]))).sum()),
                           **{f"test_{c}": int((y_te == c).sum()) for c in class_names}})

        threshold, *_ = b.search_threshold(ratios[tr], y_tr)
        templates = b.build_templates(masks[tr], y_tr)
        with np.errstate(invalid="ignore", divide="ignore"):
            base_pred, _ = b.predict(masks[te], ratios[te], dcount[te], templates, threshold)
        runs.append({"split": split_name, "fold": k, "model": "baseline", "seed": "",
                     "threshold": threshold, **fold_metrics(y_te, base_pred, class_names)})
        cms["baseline"] += confusion_matrix(y_te, base_pred, labels=class_names)

        corr, _, _ = rf03.corr_features(masks, templates)
        feats = {"A": np.column_stack([ratios, corr]),
                 "B": np.column_stack([ratios, shape_aug, corr])}
        for model, X in feats.items():
            for seed in RF_SEEDS:
                rf = RandomForestClassifier(**RF_BASE, random_state=seed).fit(X[tr], y_tr)
                pred = rf.predict(X[te])
                runs.append({"split": split_name, "fold": k, "model": model, "seed": seed,
                             "threshold": threshold, **fold_metrics(y_te, pred, class_names)})
                cms[model] += confusion_matrix(y_te, pred, labels=class_names)
        print(f"  {split_name} fold {k}: 학습 {len(tr)} / 테스트 {len(te)}, 겹치는 lot {len(shared_lots)}")
    return runs, folds_info, cms


def summarize(runs, class_names):
    """분할×모델별 요약. 정의는 모듈 docstring 4) 참고."""
    out = {}
    for split in ("lot", "random"):
        for model in ("baseline", "A", "B"):
            rs = [r for r in runs if r["split"] == split and r["model"] == model]
            folds = sorted({r["fold"] for r in rs})
            fold_acc = np.array([np.mean([r["acc"] for r in rs if r["fold"] == k]) for k in folds])
            row = {"split": split, "model": model,
                   "acc_mean": float(fold_acc.mean()), "acc_fold_std": float(fold_acc.std(ddof=1))}
            if model == "baseline":
                row["acc_seed_std"] = 0.0
                row["acc_seed_min"] = row["acc_seed_max"] = None  # baseline은 random_state가 없음
            else:
                seed_acc = np.array([np.mean([r["acc"] for r in rs if r["seed"] == s]) for s in RF_SEEDS])
                row["acc_seed_std"] = float(seed_acc.std(ddof=1))
                row["acc_seed_min"], row["acc_seed_max"] = float(seed_acc.min()), float(seed_acc.max())
            for c in class_names:
                row[f"f1_{c}"] = float(np.nanmean([r[f"f1_{c}"] for r in rs]))
                row[f"recall_{c}"] = float(np.nanmean([r[f"recall_{c}"] for r in rs]))
                row[f"precision_{c}"] = float(np.mean([r[f"precision_{c}"] for r in rs]))
            row["macro_f1"] = float(np.mean([row[f"f1_{c}"] for c in class_names]))
            out[(split, model)] = row
    return out


def paired_b_minus_a(runs):
    """같은 split·fold·seed끼리 B-A 정확도 차이. seed별 5-fold 평균 차이도 함께."""
    res = {}
    for split in ("lot", "random"):
        key = {(r["fold"], r["seed"]): r["acc"] for r in runs if r["split"] == split and r["model"] == "A"}
        diffs = [(r["fold"], r["seed"], r["acc"] - key[(r["fold"], r["seed"])])
                 for r in runs if r["split"] == split and r["model"] == "B"]
        d = np.array([x[2] for x in diffs])
        per_seed = np.array([np.mean([x[2] for x in diffs if x[1] == s]) for s in RF_SEEDS])
        res[split] = {"diff_mean": float(d.mean()), "diff_std_all50": float(d.std(ddof=1)),
                      "b_better": int((d > 0).sum()), "a_better": int((d < 0).sum()), "tie": int((d == 0).sum()),
                      "per_seed_diff": [float(x) for x in per_seed],
                      "per_seed_diff_mean": float(per_seed.mean()), "per_seed_diff_std": float(per_seed.std(ddof=1)),
                      "seeds_b_better": int((per_seed > 0).sum())}
    return res


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    paths, labels, images = b.load_dataset()
    pc = b.classify_pixels(images)
    masks = (pc == b.DEFECT).astype(np.float64)
    ratios, dcount = b.defect_ratio(pc)
    files = [f"{p.parent.name}/{p.name}" for p in paths]
    lots = load_lots(files)
    class_names = sorted(set(labels))
    shape_aug = aug.shape_matrix_aug(masks)  # 마스크만으로 계산(학습 정보 안 씀) → 한 번만

    # 1) 7:3 분할의 lot 공유
    overlap = overlap_7030(labels, lots, class_names)
    write_csv(RESULTS_DIR / f"{PREFIX}7030_overlap.csv", overlap)

    # 2)~3) 5-fold 두 가지
    splitters = {
        "lot": StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=CV_RANDOM_STATE),
        "random": StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=CV_RANDOM_STATE),
    }
    runs, folds_info, cms = [], [], {}
    for name, sp in splitters.items():
        r, fi, cm = run_split(name, sp, labels, lots, masks, ratios, dcount, shape_aug, class_names)
        runs += r
        folds_info += fi
        cms[name] = cm
    write_csv(RESULTS_DIR / f"{PREFIX}fold_runs.csv", runs)
    write_csv(RESULTS_DIR / f"{PREFIX}folds.csv", folds_info)

    summ = summarize(runs, class_names)
    paired = paired_b_minus_a(runs)

    # 요약표 (CSV + MD)
    order = [(s, m) for s in ("random", "lot") for m in ("baseline", "A", "B")]
    write_csv(RESULTS_DIR / f"{PREFIX}summary.csv", [summ[k] for k in order])
    split_ko = {"random": "무작위", "lot": "lot"}
    md = ["| 분할 | 모델 | 정확도 평균±fold 표준편차 | random_state 표준편차 | macro F1 | "
          + " | ".join(f"F1 {c}" for c in class_names) + " |",
          "|---|---|---:|---:|---:|" + "---:|" * len(class_names)]
    for k in order:
        r = summ[k]
        seed = "–" if k[1] == "baseline" else f"{100 * r['acc_seed_std']:.2f}%p"
        md.append(f"| {split_ko[k[0]]} | {k[1]} | {100 * r['acc_mean']:.1f}% ± {100 * r['acc_fold_std']:.1f} | {seed} | "
                  f"{r['macro_f1']:.3f} | " + " | ".join(f"{r[f'f1_{c}']:.3f}" for c in class_names) + " |")
    (RESULTS_DIR / f"{PREFIX}summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # 혼동행렬 (모든 fold 합계, A/B는 random_state 10번 합계를 10으로 나눈 평균)
    with open(RESULTS_DIR / f"{PREFIX}confusion.txt", "w", encoding="utf-8") as f:
        for split in ("random", "lot"):
            for model in ("baseline", "A", "B"):
                cm = cms[split][model] / (1 if model == "baseline" else len(RF_SEEDS))
                f.write(f"===== {split} / {model} (행=정답, 열=예측, 순서={class_names}) =====\n")
                f.write(np.array2string(cm, precision=1, suppress_small=True, max_line_width=200) + "\n\n")

    summary = {
        "n_images": len(labels), "n_lots": int(len(set(lots))),
        "cv": {"n_splits": N_SPLITS, "shuffle": True, "random_state": CV_RANDOM_STATE},
        "rf_params": {**RF_BASE, "random_state": RF_SEEDS},
        "overlap_7030": overlap,
        "folds": folds_info,
        "summary": {f"{s}/{m}": v for (s, m), v in summ.items()},
        "b_minus_a_paired": paired,
        "confusion_class_order": class_names,
    }
    (RESULTS_DIR / f"{PREFIX}metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")

    print("\n7:3 분할 lot 공유")
    for r in overlap:
        print(f"  {r['type']:10s} {r['shared_lot_n']:3d}/{r['test_n']:3d} ({r['shared_pct']}%)")
    print("\n" + "\n".join(md))
    print("\nB-A 짝 비교:", json.dumps(paired, ensure_ascii=False, indent=1))
    for s in ("random", "lot"):
        for m in ("A", "B"):
            r = summ[(s, m)]
            print(f"{s}/{m}: seed별 5-fold 평균 {100 * r['acc_seed_min']:.2f}~{100 * r['acc_seed_max']:.2f}%")
        for m in ("baseline", "A", "B"):
            r = summ[(s, m)]
            print(f"{s}/{m} none: F1 {r['f1_none']:.3f}, recall {r['recall_none']:.3f}, precision {r['precision_none']:.3f}")


if __name__ == "__main__":
    main()
