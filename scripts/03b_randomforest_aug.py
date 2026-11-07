"""03b: 8월 대화 기록의 모양 특징 코드 원문으로 B만 다시 돌린다.

- 03_randomforest.py와 그 결과는 건드리지 않는다. 데이터·분할·템플릿·상관계수 특징은 01/03 함수를 불러 쓴다.
  분할: test_size=0.3, random_state=42, stratify (03과 같음)
- shape_features_aug: 사용자가 준 8월 코드 원문 그대로 (아래 함수 본문 수정 금지)
- 8월 특징 순서: [면적 비율, 덩어리 개수, 최대 덩어리 비율, min(신장도, 50), 템플릿 상관계수 8개(near full 제외, 폴더 이름 순)]
- 03과의 차이를 나누려고 4가지 조합을 돌린다 (RandomForest 설정은 03과 같음)
    B_03       : 03 예외 처리 + 03 순서   (03 결과 77.5% 재현 확인용)
    edge_only  : 8월 예외 처리 + 03 순서
    order_only : 03 예외 처리 + 8월 순서
    B_aug      : 8월 예외 처리 + 8월 순서 (요청한 본 결과)
  03 순서 = [면적 비율, 상관계수 8개, 덩어리 개수, 최대 덩어리 비율, 신장도]
- 결과: results/03b_*

실행: .venv/bin/python scripts/03b_randomforest_aug.py
"""

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rf03 = _load("rf03", "03_randomforest.py")
b = rf03.b  # 01_baseline 모듈 (03이 불러온 것과 같은 것)

ELONGATION_CAP = 50.0


# ---- 8월 코드 원문 (수정하지 않음) ----
def shape_features_aug(defect_mask):
    labeled, n = ndimage.label(defect_mask, structure=np.ones((3,3)))
    total_defect = defect_mask.sum()
    if n == 0 or total_defect == 0:
        return dict(n_components=0, largest_frac=0.0, elongation=0.0)
    sizes = ndimage.sum(defect_mask, labeled, range(1, n+1))
    largest_idx = np.argmax(sizes) + 1
    largest_frac = sizes.max() / total_defect
    ys, xs = np.where(labeled == largest_idx)
    if len(xs) < 3:
        elong = 0.0
    else:
        coords = np.stack([xs, ys]).astype(np.float32)
        cov = np.cov(coords)
        eigvals = np.linalg.eigvalsh(cov)
        eigvals = np.clip(eigvals, 1e-6, None)
        elong = np.sqrt(eigvals.max() / eigvals.min())
    return dict(n_components=n, largest_frac=float(largest_frac), elongation=float(elong))
# ---- 원문 끝 ----


def shape_matrix_aug(masks):
    """8월 함수 결과를 (덩어리 개수, 최대 덩어리 비율, min(신장도, 50)) 배열로."""
    rows = []
    for m in masks:
        d = shape_features_aug(m)
        rows.append((d["n_components"], d["largest_frac"], min(d["elongation"], ELONGATION_CAP)))
    return np.array(rows, dtype=np.float64)


def shape_matrix_03(masks):
    return np.array([rf03.shape_features(m)[0] for m in masks], dtype=np.float64)


def main():
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

    templates = b.build_templates(masks[tr], y_tr)
    # 템플릿 순서가 폴더 이름 순(near full 제외)인지 확인
    folder_order = [d.name for d in sorted(p for p in b.DATA_DIR.iterdir() if p.is_dir())]
    expected = [c for c in folder_order if c != b.NEAR_FULL]
    if list(templates) != expected:
        raise RuntimeError(f"템플릿 순서가 폴더 이름 순과 달라요: {list(templates)} vs {expected}")

    corr, corr_names, _ = rf03.corr_features(masks, templates)
    shape_names = ["n_blobs", "largest_blob_ratio", "largest_blob_elongation"]
    shapes = {"03": shape_matrix_03(masks), "aug": shape_matrix_aug(masks)}

    def build(edge, order):
        s = shapes[edge]
        if order == "03":
            return np.column_stack([ratios, corr, s]), ["defect_ratio"] + corr_names + shape_names
        return np.column_stack([ratios, s, corr]), ["defect_ratio"] + shape_names + corr_names

    variants = [  # (이름, 예외 처리, 순서)
        ("B_03", "03", "03"),
        ("edge_only", "aug", "03"),
        ("order_only", "03", "aug"),
        ("B_aug", "aug", "aug"),
    ]
    results, preds, imps = {}, {}, {}
    for name, edge, order in variants:
        X, names = build(edge, order)
        rf = RandomForestClassifier(**rf03.RF_PARAMS).fit(X[tr], y_tr)
        preds[name] = rf.predict(X[te])
        results[name] = rf03.evaluate(y_te, preds[name], class_names)
        results[name]["edge"], results[name]["order"] = edge, order
        imps[name] = (names, rf.feature_importances_)

    # 03의 B 결과가 그대로 재현되는지 확인 (같은 코드 경로)
    saved = json.loads((RESULTS_DIR / "03_randomforest_metrics.json").read_text(encoding="utf-8"))
    b03_saved = saved["results"]["B"]["correct"]
    if results["B_03"]["correct"] != b03_saved:
        raise RuntimeError(f"B_03 재현 실패: {results['B_03']['correct']} vs 03 저장값 {b03_saved}")

    # 8월 방식과 03 방식의 모양 특징값이 다른 이미지 수
    diff_any = ~np.isclose(shapes["03"], shapes["aug"]).all(axis=1)
    diff_by_col = {n: {"train": int((~np.isclose(shapes["03"][tr, j], shapes["aug"][tr, j])).sum()),
                       "test": int((~np.isclose(shapes["03"][te, j], shapes["aug"][te, j])).sum())}
                   for j, n in enumerate(shape_names)}

    order = [v[0] for v in variants]
    labels_ko = {"B_03": "03 예외 + 03 순서", "edge_only": "8월 예외 + 03 순서",
                 "order_only": "03 예외 + 8월 순서", "B_aug": "8월 예외 + 8월 순서"}

    # ---- 저장: 비교표 ----
    with open(RESULTS_DIR / "03b_comparison.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric"] + order)
        w.writerow(["edge_case_handling"] + [results[k]["edge"] for k in order])
        w.writerow(["feature_order"] + [results[k]["order"] for k in order])
        w.writerow(["accuracy"] + [f"{results[k]['accuracy']:.4f}" for k in order])
        w.writerow(["correct_of_271"] + [results[k]["correct"] for k in order])
        for c in class_names:
            w.writerow([f"F1_{c}"] + [f"{results[k]['f1'][c]:.3f}" for k in order])
        w.writerow(["macro_F1"] + [f"{results[k]['macro_f1']:.3f}" for k in order])

    md = ["| 항목 | " + " | ".join(labels_ko[k] for k in order) + " |",
          "|---|" + "---:|" * len(order)]
    md.append("| 정확도 | " + " | ".join(
        f"{results[k]['accuracy']:.1%} ({results[k]['correct']}/{len(te)})" for k in order) + " |")
    for c in class_names:
        md.append(f"| F1 {c} | " + " | ".join(f"{results[k]['f1'][c]:.3f}" for k in order) + " |")
    md.append("| macro F1 | " + " | ".join(f"{results[k]['macro_f1']:.3f}" for k in order) + " |")
    (RESULTS_DIR / "03b_comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---- 저장: B_aug 특징 중요도 ----
    names, imp = imps["B_aug"]
    with open(RESULTS_DIR / "03b_feature_importance_B_aug.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "feature", "importance"])
        for r, j in enumerate(np.argsort(imp)[::-1], 1):
            w.writerow([r, names[j], f"{imp[j]:.4f}"])

    # ---- 저장: 테스트셋 장별 예측 (네 조합) + 12장 ----
    with open(RESULTS_DIR / "03b_test_predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "true"] + order)
        for k, i in enumerate(te):
            w.writerow([files[i], labels[i]] + [preds[v][k] for v in order])
    pos = {files[i]: k for k, i in enumerate(te)}
    with open(RESULTS_DIR / "03b_missed12_predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "true"] + order + ["aug_n_blobs", "aug_largest_ratio", "aug_elongation_capped"])
        for f_ in rf03.MISSED12:
            k, i = pos[f_], te[pos[f_]]
            s = shapes["aug"][i]
            w.writerow([f_, labels[i]] + [preds[v][k] for v in order]
                       + [int(s[0]), round(s[1], 3), round(s[2], 2)])

    # 조합 간 예측이 다른 테스트 이미지 수
    pair_diff = {f"{a}_vs_{c}": int((preds[a] != preds[c]).sum())
                 for a in order for c in order if a < c}
    summary = {
        "rf_params": rf03.RF_PARAMS,
        "b03_reproduced": True,
        "template_order": list(templates),
        "variants": {k: {kk: v for kk, v in results[k].items() if kk != "report_text"} for k in order},
        "shape_value_differs_03_vs_aug": {"any_feature_train": int(diff_any[tr].sum()),
                                          "any_feature_test": int(diff_any[te].sum()),
                                          "by_feature": diff_by_col},
        "test_prediction_differences_between_variants": pair_diff,
        "class_order": class_names,
    }
    (RESULTS_DIR / "03b_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / "03b_report.txt").write_text("\n".join(
        f"===== {k} ({labels_ko[k]}) =====\n정확도 {results[k]['accuracy']:.4f} "
        f"({results[k]['correct']}/{len(te)})\n{results[k]['report_text']}\n"
        f"혼동행렬 (행=정답, 열=예측, 순서={class_names})\n{np.array(results[k]['confusion'])}\n"
        for k in order), encoding="utf-8")

    print("\n".join(md))
    print("\n모양 특징값이 03과 다른 이미지:", summary["shape_value_differs_03_vs_aug"])
    print("조합 간 테스트 예측 차이:", pair_diff)
    print("\nB_aug 특징 중요도")
    for j in np.argsort(imp)[::-1]:
        print(f"  {names[j]:28s} {imp[j]:.4f}")


if __name__ == "__main__":
    main()
