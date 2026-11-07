"""RandomForest 분류기 (8월 방식 재현): baseline / A / B 비교.

- 데이터·픽셀 분류·분할·템플릿은 01_baseline.py 함수를 그대로 불러 쓴다(01 파일은 수정하지 않음).
  분할: test_size=0.3, random_state=42, stratify (프로젝트 규칙)
  템플릿: 학습셋에서 near full을 제외한 8개 유형(none 포함)의 결함 마스크 평균
- A) 특징 9개 = 결함 면적 비율 + 8개 템플릿 상관계수
     상관계수를 계산할 수 없을 때(마스크나 템플릿의 표준편차가 0)는 8월처럼 -1.0
- B) A의 특징 + 모양 특징 3개 (결함 마스크에서 계산)
     1) 결함 덩어리 개수: scipy.ndimage.label, 8방향 연결(3x3 모두 1인 구조)
     2) 가장 큰 덩어리 픽셀 수 / 전체 결함 픽셀 수
     3) 가장 큰 덩어리의 신장도: 좌표(행, 열) 공분산 행렬 고유값의 sqrt(최대/최소), 50에서 자름
     사용자가 정하지 않은 예외 처리 (이 스크립트에서 정함, 보고서에 건수 기록):
       - 결함 픽셀 0개: 덩어리 개수 0, 비율 0, 신장도 1.0
       - 가장 큰 덩어리가 1픽셀(공분산을 구할 수 없음, 0/0): 신장도 1.0
       - 최소 고유값이 0(한 줄로 늘어선 덩어리, x/0): 신장도 50 (자르는 상한)
- 분류기: RandomForestClassifier(n_estimators=300, random_state=42, max_depth=8, min_samples_leaf=2)
- 결과: results/03_* (비교표, B 특징 중요도, 02 보고서의 12장 예측표)

실행: .venv/bin/python scripts/03_randomforest.py
"""

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

# 01_baseline.py를 모듈로 불러온다 (파일 이름이 숫자로 시작해 import 문을 못 씀)
_spec = importlib.util.spec_from_file_location("baseline", ROOT / "scripts" / "01_baseline.py")
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)

CORR_UNDEFINED = -1.0  # 상관계수 계산 불가 시 값 (8월 방식)
ELONGATION_CAP = 50.0
EIG_ZERO = 1e-12  # 이보다 작은 고유값은 0으로 본다 (부동소수 오차)
RF_PARAMS = dict(n_estimators=300, random_state=42, max_depth=8, min_samples_leaf=2)

# 02_missed12_report.md의 12장 (같은 순서)
MISSED12 = [
    "Center/773253.jpg", "Scratch/809507.jpg", "Center/776169.jpg", "Center/761994.jpg",
    "Edge Ring/766504.jpg", "Scratch/801807.jpg", "Edge Local/810215.jpg", "Local/792182.jpg",
    "Donut/758427.jpg", "Edge Local/810592.jpg", "Local/791996.jpg", "Scratch/807903.jpg",
]


def corr_features(masks, templates):
    """마스크마다 8개 템플릿과의 상관계수. 마스크나 템플릿의 표준편차가 0이면 -1.0."""
    names = list(templates)
    flats = [templates[c].ravel() for c in names]
    feats = np.empty((len(masks), len(names)))
    n_undefined = 0
    for i, m in enumerate(masks):
        flat = m.ravel()
        for j, t in enumerate(flats):
            if flat.std() == 0 or t.std() == 0:
                feats[i, j] = CORR_UNDEFINED
                n_undefined += 1
            else:
                feats[i, j] = np.corrcoef(flat, t)[0, 1]
    return feats, [f"corr_{c}" for c in names], n_undefined


def shape_features(mask):
    """결함 덩어리 개수, 가장 큰 덩어리 비율, 가장 큰 덩어리 신장도. 예외 경우 이름도 함께 돌려준다."""
    binary = mask > 0
    total = int(binary.sum())
    if total == 0:
        return (0.0, 0.0, 1.0), "no_defect"
    labeled, n = ndimage.label(binary, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(labeled.ravel())[1:]  # 0번(배경) 제외
    largest = int(np.argmax(sizes)) + 1
    largest_ratio = sizes[largest - 1] / total
    coords = np.argwhere(labeled == largest).astype(np.float64)
    if len(coords) < 2:
        return (float(n), float(largest_ratio), 1.0), "single_pixel"
    eig = np.linalg.eigvalsh(np.cov(coords, rowvar=False))
    lo, hi = eig.min(), eig.max()
    if lo <= EIG_ZERO:
        return (float(n), float(largest_ratio), ELONGATION_CAP), "line"
    return (float(n), float(largest_ratio), float(min(np.sqrt(hi / lo), ELONGATION_CAP))), "normal"


def evaluate(y_true, y_pred, class_names):
    rep = classification_report(y_true, y_pred, labels=class_names, output_dict=True, zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "correct": int((y_true == y_pred).sum()),
        "f1": {c: float(rep[c]["f1-score"]) for c in class_names},
        "macro_f1": float(rep["macro avg"]["f1-score"]),
        "report_text": classification_report(
            y_true, y_pred, labels=class_names, digits=3, zero_division=0
        ),
        "confusion": confusion_matrix(y_true, y_pred, labels=class_names).tolist(),
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    paths, labels, images = b.load_dataset()
    pc = b.classify_pixels(images)
    masks = (pc == b.DEFECT).astype(np.float64)
    ratios, dcount = b.defect_ratio(pc)
    files = np.array([f"{p.parent.name}/{p.name}" for p in paths])

    tr, te = train_test_split(
        np.arange(len(labels)), test_size=b.TEST_SIZE, random_state=b.RANDOM_STATE, stratify=labels
    )
    class_names = sorted(set(labels))
    y_tr, y_te = labels[tr], labels[te]

    # ---- baseline: 01과 똑같이 다시 계산하고, 01 결과 파일과 일치하는지 확인 ----
    threshold, *_ = b.search_threshold(ratios[tr], y_tr)
    templates = b.build_templates(masks[tr], y_tr)
    with np.errstate(invalid="ignore", divide="ignore"):
        base_pred, _ = b.predict(masks[te], ratios[te], dcount[te], templates, threshold)
    saved = {}
    with open(RESULTS_DIR / "01_baseline_test_predictions.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            saved[row["file"]] = row["pred"]
    mismatch = sum(saved[files[i]] != p for i, p in zip(te, base_pred))
    if mismatch or len(saved) != len(te):
        raise RuntimeError(f"baseline 재계산이 01 결과와 달라요 (불일치 {mismatch}장)")

    # ---- 특징 ----
    corr, corr_names, n_undef = corr_features(masks, templates)
    feat_A = np.column_stack([ratios, corr])
    names_A = ["defect_ratio"] + corr_names

    shape_rows, shape_cases = zip(*(shape_features(m) for m in masks))
    shape = np.array(shape_rows)
    shape_cases = np.array(shape_cases)
    feat_B = np.column_stack([feat_A, shape])
    names_B = names_A + ["n_blobs", "largest_blob_ratio", "largest_blob_elongation"]

    # ---- 학습/예측 ----
    results = {"baseline": evaluate(y_te, base_pred, class_names)}
    preds = {"baseline": base_pred}
    models = {}
    for key, X in (("A", feat_A), ("B", feat_B)):
        rf = RandomForestClassifier(**RF_PARAMS).fit(X[tr], y_tr)
        preds[key] = rf.predict(X[te])
        results[key] = evaluate(y_te, preds[key], class_names)
        models[key] = rf

    # ---- 1) 비교표 (정확도 + 유형별 F1) ----
    order = ["baseline", "A", "B"]
    aug = {"baseline": 0.661, "A": 0.775, "B": 0.793}  # 사용자가 알려준 8월 결과 (참고 열)
    with open(RESULTS_DIR / "03_comparison.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric"] + order)
        w.writerow(["accuracy"] + [f"{results[k]['accuracy']:.4f}" for k in order])
        w.writerow(["correct_of_271"] + [results[k]["correct"] for k in order])
        w.writerow(["august_reported_accuracy"] + [aug[k] for k in order])
        for c in class_names:
            w.writerow([f"F1_{c}"] + [f"{results[k]['f1'][c]:.3f}" for k in order])
        w.writerow(["macro_F1"] + [f"{results[k]['macro_f1']:.3f}" for k in order])

    md = ["| 항목 | baseline | A | B |", "|---|---:|---:|---:|"]
    md.append("| 정확도 | " + " | ".join(
        f"{results[k]['accuracy']:.1%} ({results[k]['correct']}/{len(te)})" for k in order) + " |")
    md.append("| 8월 보고 정확도 | " + " | ".join(f"{aug[k]:.1%}" for k in order) + " |")
    for c in class_names:
        md.append(f"| F1 {c} | " + " | ".join(f"{results[k]['f1'][c]:.3f}" for k in order) + " |")
    md.append("| macro F1 | " + " | ".join(f"{results[k]['macro_f1']:.3f}" for k in order) + " |")
    (RESULTS_DIR / "03_comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---- 2) B 특징 중요도 (RandomForest 불순도 감소 기준) ----
    imp = models["B"].feature_importances_
    with open(RESULTS_DIR / "03_feature_importance_B.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "feature", "importance"])
        for r, j in enumerate(np.argsort(imp)[::-1], 1):
            w.writerow([r, names_B[j], f"{imp[j]:.4f}"])

    # ---- 3) 02 보고서 12장의 예측 ----
    pos = {files[i]: k for k, i in enumerate(te)}
    missing = [f for f in MISSED12 if f not in pos]
    if missing:
        raise RuntimeError(f"12장 중 테스트셋에 없는 파일: {missing}")
    rows = []
    for f_ in MISSED12:
        k = pos[f_]
        i = te[k]
        rows.append({
            "file": f_, "true": labels[i], "defect_px": int(dcount[i]),
            "baseline": preds["baseline"][k], "A": preds["A"][k], "B": preds["B"][k],
            "n_blobs": int(shape[i, 0]), "largest_blob_ratio": round(float(shape[i, 1]), 3),
            "elongation": round(float(shape[i, 2]), 2), "shape_case": shape_cases[i],
        })
    with open(RESULTS_DIR / "03_missed12_predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # ---- 4) 상세 지표 + 예외 처리 건수 ----
    case_counts = {
        part: {c: int((shape_cases[idx] == c).sum()) for c in ("no_defect", "single_pixel", "line", "normal")}
        for part, idx in (("train", tr), ("test", te))
    }
    undef_rows = {part: int((corr[idx] == CORR_UNDEFINED).any(axis=1).sum()) for part, idx in (("train", tr), ("test", te))}
    summary = {
        "n_train": int(len(tr)), "n_test": int(len(te)),
        "rf_params": RF_PARAMS,
        "baseline_matches_01_file": True,
        "corr_undefined_value": CORR_UNDEFINED,
        "corr_undefined_cells_total": n_undef,
        "images_with_undefined_corr": undef_rows,
        "shape_feature_cases": case_counts,
        "features_A": names_A, "features_B": names_B,
        "results": {k: {kk: v for kk, v in results[k].items() if kk != "report_text"} for k in order},
        "class_order": class_names,
    }
    (RESULTS_DIR / "03_randomforest_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = []
    for k in order:
        report.append(f"===== {k} =====\n정확도 {results[k]['accuracy']:.4f} "
                      f"({results[k]['correct']}/{len(te)})\n{results[k]['report_text']}")
        report.append(f"혼동행렬 (행=정답, 열=예측, 순서={class_names})\n{np.array(results[k]['confusion'])}\n")
    (RESULTS_DIR / "03_randomforest_report.txt").write_text("\n".join(report), encoding="utf-8")

    print("\n".join(md))
    print("\n특징 중요도 (B)")
    for j in np.argsort(imp)[::-1]:
        print(f"  {names_B[j]:28s} {imp[j]:.4f}")
    print("\n12장 예측")
    for r in rows:
        print(f"  {r['file']:24s} 정답={r['true']:10s} base={r['baseline']:10s} A={r['A']:10s} B={r['B']}")
    print(f"\n상관계수 계산 불가 이미지: {undef_rows}, 모양 특징 예외: {case_counts}")


if __name__ == "__main__":
    main()
