"""05: 새 웨이퍼 알림 (특이맵 여부 / 예상 유형·확신도 / 긴급 / 비슷한 과거 맵 3장).

준비
- 04와 같은 lot 분할: StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42), 그룹 = lotName
- 5개 fold 모두 9개 유형이 들어 있다(04_lot_split_folds.csv). 그래서 결과를 보기 전에 정해 둔 규칙
  "가장 앞 번호(fold 0)"로 고른다. 이 fold = "새로 들어온 웨이퍼", 나머지 4개 fold = "과거 데이터".
  (스크립트가 fold 0에 9개 유형이 모두 있는지 다시 확인하고, 없으면 멈춘다.)
- 과거 데이터로만 만든다
  - near full 임계값: 01의 search_threshold (카드와 결과표에 참고값으로만 표시, 판정에는 안 씀)
  - 템플릿: 01의 build_templates (near full 제외 8개 유형)
  - B 모델: 03b의 8월 원문 방식 특징
      [면적 비율, 덩어리 개수, 최대 덩어리 비율, min(신장도, 50), 템플릿 상관계수 8개]
    RandomForestClassifier(n_estimators=300, random_state=42, max_depth=8, min_samples_leaf=2)

알림 (웨이퍼 1장마다)
1. 특이맵 여부: 예상 유형(RandomForest 확률 1위)이 none이 아니면 특이맵
2. 예상 유형과 확신도: 확률 1위·2위. 1위 확률 < 0.5 이면 "사람 확인 필요"
3. 예상 유형이 near full 이면 "긴급"
4. 비슷한 과거 맵 3장: 결함 마스크(결함=1, 그 외=0) 32x32를 펼쳐 구한 피어슨 상관계수가 가장 높은 3장
   - 한쪽 마스크의 값이 모두 같아(결함 0개 등) 상관계수를 구할 수 없으면 -1.0 (03의 규칙과 같음)
   - 동점이면 과거 데이터의 파일 순서(폴더 이름 → 파일 이름)가 앞선 것

출력 (01~04 결과 파일은 건드리지 않음)
- results/05_alert_all.csv           : 새 웨이퍼 전체 결과표
- results/05_alert_cards/*.png       : 정답 유형별로 1장씩(새 웨이퍼 중 파일 순서 첫 장) 9장
- results/05_alert_metrics.json, results/05_alert_summary.md : 평가
  (1) 유형 정확도  (2) 비슷한 과거 맵 3장 중 새 웨이퍼의 정답 유형과 같은 비율

실행
  전체:      .venv/bin/python scripts/05_alert.py
  파일 1장:  .venv/bin/python scripts/05_alert.py --image 경로 [--out 카드.png]
             (32x32 이미지만 받는다. 기본 저장 위치 results/05_alert_single/<파일이름>.png)
"""

import argparse
import csv
import importlib.util
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
CARD_DIR = RESULTS_DIR / "05_alert_cards"
SINGLE_DIR = RESULTS_DIR / "05_alert_single"
PREFIX = "05_alert_"

N_SPLITS = 5
CV_RANDOM_STATE = 42
NEW_FOLD = 0  # 규칙: 9개 유형이 모두 든 fold 중 가장 앞 번호
REVIEW_PROB = 0.5
TOP_K = 3
CORR_UNDEFINED = -1.0


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lot04 = _load("lot04", "04_lot_split.py")
aug = lot04.aug     # 03b 모듈
rf03 = aug.rf03     # 03 모듈
b = aug.b           # 01 모듈


# ---------------- 준비: 데이터, 분할, 과거 데이터로 만든 모델 ----------------

def build_system():
    """902장을 읽고 fold를 나눈 뒤, 과거 데이터로 임계값·템플릿·B 모델을 만든다."""
    paths, labels, images = b.load_dataset()
    pc = b.classify_pixels(images)
    masks = (pc == b.DEFECT).astype(np.float64)
    ratios, _ = b.defect_ratio(pc)
    files = [f"{p.parent.name}/{p.name}" for p in paths]
    lots = lot04.load_lots(files)
    with open(lot04.LOT_MAP, encoding="utf-8") as f:
        wafer_idx = {r["file_name"]: r["waferIndex"] for r in csv.DictReader(f)}
    class_names = sorted(set(labels))

    splitter = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=CV_RANDOM_STATE)
    folds = list(splitter.split(np.zeros(len(labels)), labels, lots))
    fold_types = [sorted(set(labels[te])) for _, te in folds]
    past, new = folds[NEW_FOLD]
    if fold_types[NEW_FOLD] != class_names:
        raise RuntimeError(f"fold {NEW_FOLD}에 9개 유형이 다 없어요: {fold_types[NEW_FOLD]}")
    if set(lots[past]) & set(lots[new]):
        raise RuntimeError("과거 데이터와 새 웨이퍼가 lot을 공유해요")

    threshold, *_ = b.search_threshold(ratios[past], labels[past])
    templates = b.build_templates(masks[past], labels[past])
    corr, _, _ = rf03.corr_features(masks, templates)
    shape = aug.shape_matrix_aug(masks)
    X = np.column_stack([ratios, shape, corr])  # 03b 8월 순서
    model = RandomForestClassifier(**rf03.RF_PARAMS).fit(X[past], labels[past])

    return dict(paths=paths, files=np.array(files), labels=labels, masks=masks, ratios=ratios,
                lots=lots, wafer_idx=np.array([wafer_idx[f] for f in files]), class_names=class_names,
                folds=folds, fold_types=fold_types, past=past, new=new, threshold=threshold,
                templates=templates, model=model, X=X)


def features_for(masks, ratios, sysd):
    """임의의 마스크들에 대해 B 특징을 만든다 (템플릿은 과거 데이터 것)."""
    corr, _, _ = rf03.corr_features(masks, sysd["templates"])
    return np.column_stack([ratios, aug.shape_matrix_aug(masks), corr])


def mask_corr_to_past(masks, sysd):
    """각 마스크와 과거 데이터 마스크 전체의 상관계수 행렬 (계산 불가 = -1.0)."""
    past_flat = sysd["masks"][sysd["past"]].reshape(len(sysd["past"]), -1)
    q = masks.reshape(len(masks), -1)

    def zscore(a):
        c = a - a.mean(axis=1, keepdims=True)
        n = np.sqrt((c ** 2).sum(axis=1, keepdims=True))
        return c, n.ravel()

    qc, qn = zscore(q)
    pc_, pn = zscore(past_flat)
    with np.errstate(invalid="ignore", divide="ignore"):
        sim = (qc @ pc_.T) / np.outer(qn, pn)
    sim[(qn == 0)[:, None] | (pn == 0)[None, :]] = CORR_UNDEFINED
    return sim


def make_alerts(masks, ratios, sysd):
    """마스크 여러 장의 알림 정보를 만든다."""
    model = sysd["model"]
    proba = model.predict_proba(features_for(masks, ratios, sysd))
    classes = model.classes_
    sim = mask_corr_to_past(masks, sysd)
    past = sysd["past"]
    alerts = []
    for i in range(len(masks)):
        order = np.argsort(-proba[i], kind="stable")
        top1, top2 = classes[order[0]], classes[order[1]]
        nn = np.argsort(-sim[i], kind="stable")[:TOP_K]  # 동점이면 파일 순서 앞선 것
        neighbors = []
        for j in nn:
            g = past[j]
            neighbors.append(dict(idx=int(g), file=sysd["files"][g], type=sysd["labels"][g],
                                  lot=sysd["lots"][g], wafer=sysd["wafer_idx"][g],
                                  corr=float(sim[i, j]), undefined=bool(sim[i, j] == CORR_UNDEFINED)))
        alerts.append(dict(
            pred=top1, prob1=float(proba[i, order[0]]), pred2=top2, prob2=float(proba[i, order[1]]),
            anomaly=top1 != b.NONE, review=float(proba[i, order[0]]) < REVIEW_PROB,
            urgent=top1 == b.NEAR_FULL, ratio=float(ratios[i]),
            ratio_ge_threshold=bool(ratios[i] >= sysd["threshold"]),
            n_defect=int(masks[i].sum()), neighbors=neighbors))
    return alerts


# ---------------- 카드 그림 ----------------

def draw_map(ax, img, title, color="black"):
    ax.imshow(img.astype(np.uint8), interpolation="nearest")
    ax.set_title(title, fontsize=9, color=color)
    ax.set_xticks([])
    ax.set_yticks([])


def draw_card(new_img, alert, sysd, header, out_path, past_images):
    fig = plt.figure(figsize=(11, 6.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1], hspace=0.35, wspace=0.15)

    ax0 = fig.add_subplot(gs[0, 0])
    draw_map(ax0, new_img, "NEW WAFER\n" + header, "black")

    # 상태 배지와 정보 텍스트
    ax1 = fig.add_subplot(gs[0, 1:])
    ax1.axis("off")
    badges = []
    badges.append(("ANOMALY MAP" if alert["anomaly"] else "NORMAL (none)",
                   "#c0392b" if alert["anomaly"] else "#27ae60"))
    if alert["urgent"]:
        badges.append(("URGENT (near full)", "#8e0000"))
    if alert["review"]:
        badges.append(("NEEDS HUMAN REVIEW (top-1 prob < 0.5)", "#d68910"))
    x = 0.0
    for text, color in badges:
        t = ax1.text(x, 0.93, f" {text} ", fontsize=11, color="white", weight="bold",
                     transform=ax1.transAxes, va="center",
                     bbox=dict(boxstyle="round,pad=0.35", fc=color, ec=color))
        fig.canvas.draw()
        bb = t.get_window_extent().transformed(ax1.transAxes.inverted())
        x = bb.x1 + 0.05
    lines = [
        f"Predicted type : {alert['pred']}   (p = {alert['prob1']:.2f})",
        f"2nd candidate  : {alert['pred2']}   (p = {alert['prob2']:.2f})",
        "",
        f"Defect area    : {alert['ratio']:.1f}%  "
        f"(near full threshold {sysd['threshold']:.1f}%, reference only)",
        f"Defect pixels  : {alert['n_defect']}",
        "",
        "Model: RandomForest (B features), trained on past data",
        f"       = lot-split folds except fold {NEW_FOLD} ({len(sysd['past'])} wafers)",
    ]
    ax1.text(0.0, 0.78, "\n".join(lines), fontsize=10.5, family="monospace", va="top",
             transform=ax1.transAxes)

    for k, nb in enumerate(alert["neighbors"]):
        ax = fig.add_subplot(gs[1, k])
        sim_txt = "n/a (undefined)" if nb["undefined"] else f"{nb['corr']:.3f}"
        draw_map(ax, past_images[nb["idx"]],
                 f"Similar #{k + 1}: {nb['type']}\n{nb['lot']}  wafer {nb['wafer']}\n"
                 f"mask corr = {sim_txt}")
    fig.suptitle("Wafer map alert card", fontsize=13, weight="bold", x=0.02, ha="left")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def load_images(paths):
    return np.stack([np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) for p in paths])


# ---------------- 실행 모드 ----------------

def run_single(image_path, out_path):
    image_path = Path(image_path)
    img = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.float64)
    if img.shape[:2] != (32, 32):
        raise SystemExit(f"32x32 이미지만 받아요 (받은 크기 {img.shape[1]}x{img.shape[0]}). "
                         "크기를 바꾸는 방법은 정하지 않았어요.")
    sysd = build_system()
    pc = b.classify_pixels(img[np.newaxis])
    masks = (pc == b.DEFECT).astype(np.float64)
    ratios, _ = b.defect_ratio(pc)
    alert = make_alerts(masks, ratios, sysd)[0]

    # 과거 데이터에 들어 있는 파일이면 알려 준다 (자기 자신이 비슷한 맵 1위로 나옴)
    try:
        rel = image_path.resolve().relative_to(b.DATA_DIR.resolve()).as_posix()
    except ValueError:
        rel = None
    note = ""
    if rel is not None and rel in set(sysd["files"][sysd["past"]]):
        note = " (in past data!)"
        print(f"주의: {rel}은 과거 데이터에 들어 있는 파일이라, 자기 자신이 비슷한 맵으로 나올 수 있어요.")

    past_images = load_images(sysd["paths"])
    out = Path(out_path) if out_path else SINGLE_DIR / f"{image_path.stem}.png"
    draw_card(img, alert, sysd, f"{image_path.name}{note}", out, past_images)
    print_alert(image_path.name, alert)
    print(f"카드 저장: {out}")


def print_alert(name, a):
    print(f"\n[{name}]")
    print(f"  특이맵: {'예' if a['anomaly'] else '아니오'}")
    print(f"  예상 유형: {a['pred']} ({a['prob1']:.2f}), 2위: {a['pred2']} ({a['prob2']:.2f})"
          + ("  → 사람 확인 필요" if a["review"] else ""))
    if a["urgent"]:
        print("  긴급: near full 예상")
    for k, nb in enumerate(a["neighbors"], 1):
        print(f"  비슷한 맵 {k}: {nb['file']} ({nb['type']}, {nb['lot']}, wafer {nb['wafer']}, "
              f"상관 {nb['corr']:.3f})")


def run_all():
    sysd = build_system()
    new, labels, cn = sysd["new"], sysd["labels"], sysd["class_names"]
    alerts = make_alerts(sysd["masks"][new], sysd["ratios"][new], sysd)
    y_true = labels[new]
    y_pred = np.array([a["pred"] for a in alerts])

    # ---- 결과표 ----
    rows = []
    for i, g in enumerate(new):
        a = alerts[i]
        same = sum(nb["type"] == labels[g] for nb in a["neighbors"])
        row = {"file": sysd["files"][g], "true_type": labels[g], "lotName": sysd["lots"][g],
               "waferIndex": sysd["wafer_idx"][g], "pred_type": a["pred"], "correct": int(a["pred"] == labels[g]),
               "top1_prob": round(a["prob1"], 4), "top2_type": a["pred2"], "top2_prob": round(a["prob2"], 4),
               "anomaly_map": int(a["anomaly"]), "needs_review": int(a["review"]), "urgent": int(a["urgent"]),
               "defect_ratio_percent": round(a["ratio"], 3), "near_full_threshold": sysd["threshold"],
               "ratio_ge_threshold": int(a["ratio_ge_threshold"]), "n_defect_pixels": a["n_defect"]}
        for k, nb in enumerate(a["neighbors"], 1):
            row.update({f"sim{k}_file": nb["file"], f"sim{k}_type": nb["type"], f"sim{k}_lotName": nb["lot"],
                        f"sim{k}_waferIndex": nb["wafer"], f"sim{k}_corr": round(nb["corr"], 4),
                        f"sim{k}_undefined": int(nb["undefined"])})
        row["sim_same_type_of_3"] = same
        rows.append(row)
    lot04.write_csv(RESULTS_DIR / f"{PREFIX}all.csv", rows)

    # ---- 평가 ----
    acc = float(accuracy_score(y_true, y_pred))
    same = np.array([r["sim_same_type_of_3"] for r in rows])
    rep = classification_report(y_true, y_pred, labels=cn, output_dict=True, zero_division=0)
    review = np.array([a["review"] for a in alerts])
    undefined_any = np.array([any(nb["undefined"] for nb in a["neighbors"]) for a in alerts])
    per_type = {}
    for c in cn:
        s = y_true == c
        per_type[c] = {"n": int(s.sum()), "recall": float(rep[c]["recall"]),
                       "precision": float(rep[c]["precision"]), "f1": float(rep[c]["f1-score"]),
                       "sim_same_type_ratio": float(same[s].sum() / (TOP_K * s.sum())),
                       "sim_top1_same_type": float(np.mean([rows[i]["sim1_type"] == c for i in np.where(s)[0]]))}
    # 참고: 특이맵 판정(none 이냐 아니냐)만 본 정확도
    anomaly_acc = float(np.mean((y_pred != b.NONE) == (y_true != b.NONE)))
    metrics = {
        "new_fold": NEW_FOLD,
        "new_fold_reason": "5개 lot fold 모두 9개 유형을 포함 → 미리 정한 규칙대로 가장 앞 번호 fold 0",
        "fold_types_all_9": [len(t) == len(cn) for t in sysd["fold_types"]],
        "n_new": int(len(new)), "n_past": int(len(sysd["past"])),
        "n_new_lots": int(len(set(sysd["lots"][new]))), "n_past_lots": int(len(set(sysd["lots"][sysd["past"]]))),
        "new_type_counts": {c: int((y_true == c).sum()) for c in cn},
        "near_full_threshold_from_past": sysd["threshold"],
        "rf_params": rf03.RF_PARAMS,
        "eval1_type_accuracy": acc, "eval1_correct": int((y_true == y_pred).sum()),
        "eval2_sim_same_type_ratio": float(same.sum() / (TOP_K * len(same))),
        "eval2_sim_same_type_counts": {str(k): int((same == k).sum()) for k in range(TOP_K + 1)},
        "eval2_sim_top1_same_type": float(np.mean([r["sim1_type"] == r["true_type"] for r in rows])),
        "macro_f1": float(rep["macro avg"]["f1-score"]),
        "per_type": per_type,
        "needs_review_n": int(review.sum()),
        "accuracy_when_review": float(np.mean(y_true[review] == y_pred[review])) if review.any() else None,
        "accuracy_when_confident": float(np.mean(y_true[~review] == y_pred[~review])),
        "anomaly_flag_accuracy": anomaly_acc,
        "urgent_n": int(sum(a["urgent"] for a in alerts)),
        "urgent_true_near_full": int(sum(a["urgent"] and t == b.NEAR_FULL for a, t in zip(alerts, y_true))),
        "wafers_with_undefined_similarity": int(undefined_any.sum()),
        "confusion_class_order": cn,
        "confusion": confusion_matrix(y_true, y_pred, labels=cn).tolist(),
    }
    (RESULTS_DIR / f"{PREFIX}metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")

    md = [f"# 05 알림 평가 (새 웨이퍼 = lot fold {NEW_FOLD}, {len(new)}장 / 과거 데이터 {len(sysd['past'])}장)", "",
          f"- (1) 유형 정확도: {acc:.1%} ({metrics['eval1_correct']}/{len(new)}), macro F1 {metrics['macro_f1']:.3f}",
          f"- (2) 비슷한 과거 맵 3장 중 같은 유형 비율: {metrics['eval2_sim_same_type_ratio']:.1%} "
          f"({int(same.sum())}/{TOP_K * len(same)}), 1위 맵만 보면 {metrics['eval2_sim_top1_same_type']:.1%}",
          f"- 사람 확인 필요: {metrics['needs_review_n']}장 (이때 정확도 "
          + (f"{metrics['accuracy_when_review']:.1%}" if metrics["accuracy_when_review"] is not None else "–")
          + f", 나머지 {metrics['accuracy_when_confident']:.1%})",
          f"- 긴급(near full 예상): {metrics['urgent_n']}장, 그중 정답 near full {metrics['urgent_true_near_full']}장",
          f"- 유사도 계산 불가(-1.0)가 3장 안에 낀 웨이퍼: {metrics['wafers_with_undefined_similarity']}장", "",
          "| 유형 | 장수 | recall | precision | F1 | 비슷한 3장 중 같은 유형 | 1위 맵 같은 유형 |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for c in cn:
        p = per_type[c]
        md.append(f"| {c} | {p['n']} | {p['recall']:.3f} | {p['precision']:.3f} | {p['f1']:.3f} | "
                  f"{p['sim_same_type_ratio']:.1%} | {p['sim_top1_same_type']:.1%} |")
    (RESULTS_DIR / f"{PREFIX}summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---- 카드 9장: 정답 유형마다 새 웨이퍼 중 파일 순서 첫 장 ----
    images = load_images(sysd["paths"])
    for c in cn:
        i = int(np.where(y_true == c)[0][0])
        g = new[i]
        name = sysd["files"][g]
        header = f"{name}\n{sysd['lots'][g]}  wafer {sysd['wafer_idx'][g]}  (true: {c})"
        out = CARD_DIR / f"{c.replace(' ', '_')}_{Path(name).stem}.png"
        draw_card(images[g], alerts[i], sysd, header, out, images)
        print_alert(name, alerts[i])

    print("\n" + "\n".join(md))
    print(f"\nfold별 9개 유형 포함 여부: {metrics['fold_types_all_9']}")


def main():
    ap = argparse.ArgumentParser(description="웨이퍼 맵 알림 카드")
    ap.add_argument("--image", help="이미지 1장 경로 (32x32). 없으면 새 웨이퍼 fold 전체 실행")
    ap.add_argument("--out", help="--image 카드 저장 경로 (기본 results/05_alert_single/<이름>.png)")
    args = ap.parse_args()
    if args.image:
        run_single(args.image, args.out)
    else:
        run_all()


if __name__ == "__main__":
    main()
