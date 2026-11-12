"""08: 제품(원본 맵 크기)이 불량 유형과 얼마나 겹치는지, 외곽 모양만으로 유형을 얼마나 맞히는지 짧게 확인한다.

비유: 시험 답안지 글씨체만 보고 어느 반 학생인지 맞힐 수 있다면, "내용"이 아니라 "글씨체"로
채점이 될 위험이 있다. 여기서는 결함(내용)을 전혀 보지 않고 웨이퍼 외곽(글씨체)만으로 유형을 맞혀 본다.

하는 일 (기존 results/와 01~07 스크립트는 바꾸지 않음)
1. 902장을 원본 맵 크기(줄x칸 = 칩 배치 = 제품)로 묶은 크기 그룹 x 유형 표
   - 원본 맵은 05v2가 만든 캐시 data/raw/orig_maps_902.npz 를 쓴다 (없으면 05v2를 먼저 실행)
2. 결함 정보 없이 32x32 이미지의 웨이퍼 영역(배경이 아닌 픽셀, 01의 classify_pixels 기준)만으로 만든 특징
   - 기본 4개: 웨이퍼 픽셀 수, 가로 폭, 세로 폭, 가로/세로 비
   - 윤곽 64개: 행별 웨이퍼 폭 32개 + 열별 웨이퍼 높이 32개
   (웨이퍼 영역 = 정상+결함 칸이라 결함 위치·개수는 들어가지 않는다)
   04와 같은 lot 단위 5-fold: StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42), 그룹 = lotName
   RandomForest: 04와 같은 n_estimators=300, max_depth=8, min_samples_leaf=2, random_state 0~9
   참고: 같은 특징으로 원본 맵 크기 그룹도 맞혀 본다 (이미지가 제품 정보를 담는지)
3. 02의 none 템플릿 "좌우 끝 8칸"(이미지 14~17행 x 0열·31열) 확인
   - 이미지에서 그 칸이 결함인 비율을 유형별·크기 그룹별로
   - 원본에서 같은 높이(14~17행에 해당하는 원본 행)의 웨이퍼 맨 왼쪽·맨 오른쪽 칩이 실제 불량인 비율

출력: results2/08_*
실행: .venv/bin/python scripts/08_product_check.py
"""

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results2"
CACHE = ROOT / "data" / "raw" / "orig_maps_902.npz"
PREFIX = "08_"

N_SPLITS = 5
CV_RANDOM_STATE = 42
RF_SEEDS = list(range(10))
RF_BASE = dict(n_estimators=300, max_depth=8, min_samples_leaf=2)  # 04와 같음
EDGE_ROWS = [14, 15, 16, 17]   # 02 보고서 3-2절의 좌우 끝 8칸
EDGE_COLS = [0, 31]
B_LOT_ACC = 0.775              # 04 lot 5-fold B 모델 정확도 (results/04_lot_split_summary.md)


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lot04 = _load("lot04", "04_lot_split.py")
b = lot04.b  # 01 모듈


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ---------------- 데이터 ----------------

def load_all():
    paths, labels, images = b.load_dataset()
    files = [f"{p.parent.name}/{p.name}" for p in paths]
    lots = lot04.load_lots(files)
    with open(lot04.LOT_MAP, encoding="utf-8") as f:
        src = {r["file_name"]: r["source_row"] for r in csv.DictReader(f)}
    if not CACHE.exists():
        raise SystemExit("원본 맵 캐시가 없어요. 먼저 scripts/05v2_alert_cards_origmap.py 를 실행하세요.")
    with np.load(CACHE) as z:
        maps = [z[src[f]] for f in files]
    pc = b.classify_pixels(images)
    return dict(files=files, labels=labels, lots=lots, maps=maps, pc=pc)


# ---------------- 1. 크기 그룹 x 유형 ----------------

def size_table(d, class_names):
    sizes = np.array([f"{m.shape[0]}x{m.shape[1]}" for m in d["maps"]])
    rows = []
    for s, n in Counter(sizes).most_common():
        sel = sizes == s
        cnt = {c: int((d["labels"][sel] == c).sum()) for c in class_names}
        top = max(cnt, key=cnt.get)
        rows.append({"size": s, "n": int(n), "n_lots": len(set(d["lots"][sel])),
                     "top_type": top, "top_share": round(cnt[top] / n, 3), **cnt})
    mixed = sum(len(set(sizes[d["lots"] == lot])) > 1 for lot in set(d["lots"]))
    return sizes, rows, mixed


# ---------------- 2. 외곽 모양 특징 ----------------

def outline_features(pc):
    wafer = pc != b.BACKGROUND
    row_w = wafer.sum(axis=2)          # 행별 웨이퍼 폭 (N, 32)
    col_h = wafer.sum(axis=1)          # 열별 웨이퍼 높이 (N, 32)
    width = (col_h > 0).sum(axis=1)
    height = (row_w > 0).sum(axis=1)
    basic = np.column_stack([wafer.sum(axis=(1, 2)), width, height, width / np.maximum(height, 1)])
    return {"basic4": basic, "basic4+profile64": np.column_stack([basic, row_w, col_h])}


def lot_cv(X, y, lots, class_names):
    splitter = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=CV_RANDOM_STATE)
    accs, f1s, cm = [], [], np.zeros((len(class_names),) * 2, dtype=np.int64)
    recalls = {c: [] for c in class_names}
    for tr, te in splitter.split(np.zeros(len(y)), y, lots):
        if set(lots[tr]) & set(lots[te]):
            raise RuntimeError("lot이 학습과 시험에 겹쳐요")
        for seed in RF_SEEDS:
            pred = RandomForestClassifier(**RF_BASE, random_state=seed).fit(X[tr], y[tr]).predict(X[te])
            accs.append(float(np.mean(pred == y[te])))
            f1s.append(float(f1_score(y[te], pred, labels=class_names, average="macro", zero_division=0)))
            rec = recall_score(y[te], pred, labels=class_names, average=None, zero_division=0)
            for c, r in zip(class_names, rec):
                if (y[te] == c).any():
                    recalls[c].append(float(r))
            cm += confusion_matrix(y[te], pred, labels=class_names)
    return dict(acc_mean=float(np.mean(accs)), acc_std=float(np.std(accs)), macro_f1=float(np.mean(f1s)),
                recall={c: (float(np.mean(v)) if v else None) for c, v in recalls.items()}, cm=cm.tolist())


# ---------------- 3. 좌우 끝 8칸 ----------------

def edge8(d, sizes, class_names):
    img_hit = (d["pc"][:, EDGE_ROWS][:, :, EDGE_COLS] == b.DEFECT).any(axis=(1, 2))
    img_wafer = (d["pc"][:, EDGE_ROWS][:, :, EDGE_COLS] != b.BACKGROUND).mean(axis=(1, 2))
    orig_hit = []
    for m in d["maps"]:
        h = m.shape[0]
        rows = sorted({min(h - 1, int((r + 0.5) * h / 32)) for r in EDGE_ROWS})
        hit = False
        for r in rows:
            on = np.where(m[r] > 0)[0]
            if len(on) and (m[r, on[0]] == 2 or m[r, on[-1]] == 2):
                hit = True
        orig_hit.append(hit)
    orig_hit = np.array(orig_hit)
    by_type = [{"type": c, "n": int((d["labels"] == c).sum()),
                "img_edge8_defect": round(float(img_hit[d["labels"] == c].mean()), 3),
                "orig_outermost_die_defect": round(float(orig_hit[d["labels"] == c].mean()), 3),
                "img_edge8_on_wafer_share": round(float(img_wafer[d["labels"] == c].mean()), 3)}
               for c in class_names]
    by_size = []
    for s, n in Counter(sizes).most_common():
        sel = sizes == s
        by_size.append({"size": s, "n": int(n), "img_edge8_defect": round(float(img_hit[sel].mean()), 3),
                        "orig_outermost_die_defect": round(float(orig_hit[sel].mean()), 3),
                        "img_edge8_on_wafer_share": round(float(img_wafer[sel].mean()), 3)})
    agree = float(np.mean(img_hit == orig_hit))
    return by_type, by_size, agree, img_hit, orig_hit


# ---------------- 실행 ----------------

def main():
    OUT.mkdir(exist_ok=True)
    d = load_all()
    labels, lots = d["labels"], d["lots"]
    class_names = sorted(set(labels))

    sizes, size_rows, mixed = size_table(d, class_names)
    write_csv(OUT / f"{PREFIX}size_by_type.csv", size_rows)

    feats = outline_features(d["pc"])
    res_type = {k: lot_cv(X, labels, lots, class_names) for k, X in feats.items()}
    size_names = sorted(set(sizes))
    res_size = {k: lot_cv(X, sizes, lots, size_names) for k, X in feats.items()}

    e_type, e_size, agree, img_hit, orig_hit = edge8(d, sizes, class_names)
    write_csv(OUT / f"{PREFIX}edge8_by_type.csv", e_type)
    write_csv(OUT / f"{PREFIX}edge8_by_size.csv", e_size)

    summary = []
    for target, res, chance in (("type", res_type, 1 / len(class_names)), ("size_group", res_size, None)):
        for k, r in res.items():
            summary.append({"target": target, "features": k, "acc_mean": round(r["acc_mean"], 4),
                            "acc_std_over_fold_seed": round(r["acc_std"], 4), "macro_f1": round(r["macro_f1"], 4),
                            "chance": round(chance, 4) if chance else ""})
    write_csv(OUT / f"{PREFIX}outline_rf_summary.csv", summary)

    metrics = {
        "n": len(labels), "n_size_groups": len(size_names), "lots_with_mixed_sizes": int(mixed),
        "rf": RF_BASE, "rf_seeds": RF_SEEDS, "cv": "StratifiedGroupKFold(5, shuffle=True, random_state=42), group=lotName",
        "outline_type": res_type, "outline_size_group": res_size, "class_order": class_names,
        "size_group_order": size_names, "b_lot_acc_04": B_LOT_ACC,
        "edge8_img_vs_orig_agreement": agree,
        "edge8_img_hit_rate": float(img_hit.mean()), "edge8_orig_hit_rate": float(orig_hit.mean()),
    }
    (OUT / f"{PREFIX}metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# 08 제품(원본 맵 크기) 확인 — 수치 (스크립트 자동 생성)", "",
          f"- 902장, 원본 맵 크기 그룹 {len(size_names)}개, 크기가 섞인 lot {mixed}개 / {len(set(lots))}개", "",
          "## 1. 크기 그룹 x 유형", "",
          "| 크기 | 장수 | lot 수 | 최다 유형 (비율) | " + " | ".join(class_names) + " |",
          "|---|---:|---:|---|" + "---:|" * len(class_names)]
    for r in size_rows:
        md.append(f"| {r['size']} | {r['n']} | {r['n_lots']} | {r['top_type']} ({r['top_share']:.0%}) | "
                  + " | ".join(str(r[c]) for c in class_names) + " |")
    md += ["", "## 2. 외곽 모양만으로 RandomForest (lot 5-fold x random_state 10개)", "",
           "| 맞히는 대상 | 특징 | 정확도 평균 ± 표준편차 | macro F1 | 무작위 추측 |", "|---|---|---:|---:|---:|"]
    for r in summary:
        md.append(f"| {r['target']} | {r['features']} | {r['acc_mean']:.1%} ± {r['acc_std_over_fold_seed']:.1%} | "
                  f"{r['macro_f1']:.3f} | {r['chance'] if r['chance'] == '' else format(r['chance'], '.1%')} |")
    md += ["", f"참고: 04 lot 5-fold B 모델(결함 특징 사용) 정확도 {B_LOT_ACC:.1%}", "",
           "유형별 recall (외곽 모양만, 특징 basic4+profile64):", "",
           "| 유형 | recall |", "|---|---:|"]
    for c in class_names:
        md.append(f"| {c} | {res_type['basic4+profile64']['recall'][c]:.3f} |")
    md += ["", "## 3. 02의 좌우 끝 8칸 (이미지 14~17행 x 0·31열)", "",
           f"- 이미지 8칸 결함 여부와 원본 맨 끝 칩 불량 여부가 같은 비율: {agree:.1%}",
           f"- 902장 전체: 이미지 8칸 결함 {img_hit.mean():.1%}, 원본 맨 끝 칩 불량 {orig_hit.mean():.1%}", "",
           "| 유형 | 장수 | 이미지 8칸 결함 | 원본 맨 끝 칩 불량 | 8칸 중 웨이퍼 영역 비율 |", "|---|---:|---:|---:|---:|"]
    for r in e_type:
        md.append(f"| {r['type']} | {r['n']} | {r['img_edge8_defect']:.0%} | {r['orig_outermost_die_defect']:.0%} | "
                  f"{r['img_edge8_on_wafer_share']:.0%} |")
    md += ["", "| 크기 | 장수 | 이미지 8칸 결함 | 원본 맨 끝 칩 불량 | 8칸 중 웨이퍼 영역 비율 |", "|---|---:|---:|---:|---:|"]
    for r in e_size:
        md.append(f"| {r['size']} | {r['n']} | {r['img_edge8_defect']:.0%} | {r['orig_outermost_die_defect']:.0%} | "
                  f"{r['img_edge8_on_wafer_share']:.0%} |")
    (OUT / f"{PREFIX}report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
