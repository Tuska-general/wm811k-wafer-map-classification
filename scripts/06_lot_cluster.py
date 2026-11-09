"""06: 누적 원인 추리기 — 새 웨이퍼(05의 fold 0, 185장)를 lot별로 묶어 같은 패턴이 몰리는지 본다.

비유: 병원에서 한 환자만 보면 "감기"지만, 같은 반 학생 셋이 같은 증상이면 "교실에 원인이 있나?"를
의심한다. 여기서 반 = lot(같이 공정을 거친 웨이퍼 묶음), 증상 = 예측 불량 유형이다.

입력 (읽기만 함, 01~05 결과는 바꾸지 않음)
- results/05_alert_all.csv : 새 웨이퍼 185장의 예측(pred_type), 정답(true_type), 사람 확인 필요(needs_review)
- data/wafer_lot_map.csv   : 902장의 lotName, waferIndex (05 결과표의 값과 같은지 다시 확인)

몰림 판정 규칙 (결과를 보기 전에 정함)
- 한 lot 안에서 none이 아닌 같은 유형이 K장 이상이면 "반복 패턴 lot". 기본 K = 3.
- 민감도 확인용으로 K = 2, 4 도 같이 계산한다.
- "사람 확인 필요"(1위 확률 < 0.5) 웨이퍼도 예측 유형 그대로 센다(규칙은 바꾸지 않음).
  대신 lot별로 몇 장이 그런 웨이퍼인지 따로 적고, 그림에서 표시한다.

예측 기반 판정 vs 실제(정답) 기반 판정 (K마다)
- lot 단위: 맞게 찾은 lot = 둘 다 반복 패턴 lot, 놓친 lot = 실제만, 잘못 표시한 lot = 예측만
- (lot, 유형) 단위도 같이 센다: lot은 맞혔어도 유형이 다를 수 있기 때문

출력
- results/06_lot_summary.csv           : lot별 예측·실제 유형 장수, 사람 확인 필요, K별 판정
- results/06_lot_cluster_heatmap.png   : lot × 유형 히트맵 (웨이퍼 2장 이상인 lot)
- results/06_lot_cluster_seq_<lot>.png : 반복 패턴 lot(K=3, 예측 또는 실제)별 waferIndex 1~25 한 줄 그림
- results/06_lot_cluster_seq_all.png   : 위 그림을 한 장에 모은 것
- results/06_lot_cluster_report.md     : 보고서

실행: .venv/bin/python scripts/06_lot_cluster.py
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Patch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
ALERT_CSV = RESULTS_DIR / "05_alert_all.csv"
LOT_MAP_CSV = ROOT / "data" / "wafer_lot_map.csv"
PREFIX = "06_lot_cluster_"

K_MAIN = 3              # 결과를 보기 전에 정한 기준
K_LIST = [2, 3, 4]      # 민감도 확인
N_SLOTS = 25            # WM-811K lot 하나 = 웨이퍼 25장 (waferIndex 1~25)
NONE = "none"

# 유형 순서와 색 (none은 회색, 나머지 8개는 고정 순서 범주색)
TYPES = ["Center", "Donut", "Edge Local", "Edge Ring", "Local", "Scratch", "random", "near full", NONE]
COLORS = {
    "Center": "#2a78d6", "Donut": "#eb6834", "Edge Local": "#1baf7a", "Edge Ring": "#eda100",
    "Local": "#e87ba4", "Scratch": "#008300", "random": "#6250d6", "near full": "#e34948",
    NONE: "#b5b4ad",
}
ABBR = {"Center": "C", "Donut": "D", "Edge Local": "EL", "Edge Ring": "ER", "Local": "L",
        "Scratch": "S", "random": "R", "near full": "NF", NONE: "n"}
ABSENT_COLOR = "#f1f0ec"
INK = "#2b2b29"
INK_MUTED = "#6b6a64"

KO_FONT = Path("/mnt/c/Windows/Fonts/malgun.ttf")
KO_FONT_BOLD = Path("/mnt/c/Windows/Fonts/malgunbd.ttf")


def setup_font():
    """맑은 고딕을 등록한다. 파일이 없으면 다른 글꼴로 바꾸지 않고 멈춘다(글자 깨짐 방지)."""
    for p in (KO_FONT, KO_FONT_BOLD):
        if not p.exists():
            raise SystemExit(f"한글 글꼴 파일이 없어요: {p}")
        font_manager.fontManager.addfont(str(p))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(KO_FONT)).get_name()
    plt.rcParams["axes.unicode_minus"] = False


# ---------------- 데이터 읽기 ----------------

def load_wafers():
    """05 결과표를 읽고 lot 지도와 대조한다. 어긋나면 멈춘다."""
    with open(ALERT_CSV, newline="", encoding="utf-8") as f:
        alert = list(csv.DictReader(f))
    with open(LOT_MAP_CSV, newline="", encoding="utf-8") as f:
        lot_map = {r["file_name"]: r for r in csv.DictReader(f)}

    wafers = []
    for r in alert:
        m = lot_map.get(r["file"])
        if m is None:
            raise SystemExit(f"lot 지도에 없는 파일: {r['file']}")
        if (m["lotName"], m["waferIndex"], m["type"]) != (r["lotName"], r["waferIndex"], r["true_type"]):
            raise SystemExit(f"05 결과표와 lot 지도가 다름: {r['file']}")
        for t in (r["true_type"], r["pred_type"]):
            if t not in TYPES:
                raise SystemExit(f"모르는 유형: {t}")
        wafers.append(dict(
            file=r["file"], lot=m["lotName"], idx=int(m["waferIndex"]),
            true=r["true_type"], pred=r["pred_type"],
            review=r["needs_review"] == "1", prob=float(r["top1_prob"]),
        ))

    # 같은 lot에 같은 waferIndex가 두 번 나오면 안 된다
    seen = Counter((w["lot"], w["idx"]) for w in wafers)
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        raise SystemExit(f"lot 안에서 waferIndex 중복: {dup[:5]}")
    if any(not 1 <= w["idx"] <= N_SLOTS for w in wafers):
        raise SystemExit("waferIndex가 1~25 밖에 있음")

    # 04/05는 lot 단위로 fold를 나눴으므로, 새 웨이퍼 lot의 902장 속 웨이퍼는 전부 fold 0에 있어야 한다
    n902 = Counter(r["lotName"] for r in lot_map.values())
    nnew = Counter(w["lot"] for w in wafers)
    split = [l for l in nnew if nnew[l] != n902[l]]
    if split:
        raise SystemExit(f"새 웨이퍼 lot 일부가 과거 데이터에도 있음: {split[:5]}")
    return wafers, n902


# ---------------- 판정 ----------------

def repeated_types(counter, k):
    """none이 아닌 유형 중 k장 이상인 것 (TYPES 순서)."""
    return [t for t in TYPES if t != NONE and counter.get(t, 0) >= k]


def longest_run(idxs):
    """정렬된 waferIndex에서 바로 이어지는(차이 1) 가장 긴 구간의 길이."""
    if not idxs:
        return 0
    best = cur = 1
    for a, b in zip(idxs, idxs[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


def summarize_lots(wafers, n902):
    lots = defaultdict(list)
    for w in wafers:
        lots[w["lot"]].append(w)
    rows = []
    for lot in sorted(lots):
        ws = sorted(lots[lot], key=lambda w: w["idx"])
        pc = Counter(w["pred"] for w in ws)
        tc = Counter(w["true"] for w in ws)
        row = dict(lotName=lot, n_wafers=len(ws), n_in_902=n902[lot],
                   waferIndex=" ".join(str(w["idx"]) for w in ws))
        for t in TYPES:
            row[f"pred_{t}"] = pc.get(t, 0)
        for t in TYPES:
            row[f"true_{t}"] = tc.get(t, 0)
        rv = [w for w in ws if w["review"]]
        row["n_needs_review"] = len(rv)
        row["needs_review_waferIndex"] = " ".join(f"{w['idx']}({w['pred']})" for w in rv)
        row["n_pred_correct"] = sum(w["pred"] == w["true"] for w in ws)
        for k in K_LIST:
            row[f"repeat_pred_k{k}"] = ";".join(repeated_types(pc, k))
            row[f"repeat_true_k{k}"] = ";".join(repeated_types(tc, k))
        rows.append(row)
    return rows, lots


def compare(rows, k):
    """예측 기반 판정과 실제 기반 판정을 lot 단위, (lot, 유형) 단위로 비교."""
    P = {r["lotName"] for r in rows if r[f"repeat_pred_k{k}"]}
    T = {r["lotName"] for r in rows if r[f"repeat_true_k{k}"]}
    Pp = {(r["lotName"], t) for r in rows for t in r[f"repeat_pred_k{k}"].split(";") if t}
    Tp = {(r["lotName"], t) for r in rows for t in r[f"repeat_true_k{k}"].split(";") if t}
    return dict(k=k, pred=P, true=T, hit=P & T, miss=T - P, false=P - T,
                pair_hit=Pp & Tp, pair_miss=Tp - Pp, pair_false=Pp - Tp, n_pred_pairs=len(Pp), n_true_pairs=len(Tp))


# ---------------- 그림 ----------------

def plot_heatmap(rows, path):
    """lot × 유형 장수. 왼쪽 예측, 오른쪽 실제. 웨이퍼 1장 lot은 어떤 K에서도 반복이 될 수 없어 뺀다."""
    sel = sorted([r for r in rows if r["n_wafers"] >= 2], key=lambda r: (-r["n_wafers"], r["lotName"]))
    n = len(sel)
    vmax = max(max(r[f"{s}_{t}"] for t in TYPES) for r in sel for s in ("pred", "true"))
    fig, axes = plt.subplots(1, 2, figsize=(13, 0.36 * n + 2.6), sharey=True)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("blue", ["#ffffff", "#cde2fb", "#86b6ef", "#2a78d6", "#104281"])
    for ax, side, title in zip(axes, ("pred", "true"), ("예측 유형 장수", "실제(정답) 유형 장수")):
        M = np.array([[r[f"{side}_{t}"] for t in TYPES] for r in sel])
        ax.imshow(M, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        for i in range(n):
            for j in range(len(TYPES)):
                v = M[i, j]
                if v:
                    flag = TYPES[j] != NONE and v >= K_MAIN
                    ax.text(j, i, str(v), ha="center", va="center", fontsize=8,
                            color="white" if v >= vmax * 0.55 else INK, weight="bold" if flag else "normal")
                    if flag:
                        ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=INK, lw=1.6))
        ax.set_xticks(range(len(TYPES)))
        ax.set_xticklabels(TYPES, rotation=40, ha="right", fontsize=9)
        ax.set_title(title, fontsize=11, loc="left")
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    labels = [f"{r['lotName']}  ({r['n_wafers']}장" + (f", 확인필요 {r['n_needs_review']}" if r["n_needs_review"] else "") + ")"
              for r in sel]
    axes[0].set_yticks(range(n))
    axes[0].set_yticklabels(labels, fontsize=8.5)
    n1 = sum(r["n_wafers"] == 1 for r in rows)
    fig.suptitle(f"새 웨이퍼 lot × 유형 (웨이퍼 2장 이상인 lot {n}개, 1장뿐인 lot {n1}개는 제외)\n"
                 f"굵은 테두리 = none이 아닌 같은 유형 {K_MAIN}장 이상 (반복 패턴)",
                 fontsize=11.5, x=0.02, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def draw_seq(ax, ws, lot, flags_pred, flags_true):
    """waferIndex 1~25를 한 줄 칸으로. 위 = 예측, 아래 = 실제. 칸 글자 = 유형 약자, ? = 사람 확인 필요."""
    by_idx = {w["idx"]: w for w in ws}
    for row_i, (side, label) in enumerate((("pred", "예측"), ("true", "실제"))):
        y = 1 - row_i
        for i in range(1, N_SLOTS + 1):
            w = by_idx.get(i)
            if w is None:
                ax.add_patch(Rectangle((i - 0.46, y - 0.42), 0.92, 0.84, fc=ABSENT_COLOR, ec="none"))
                continue
            t = w[side]
            ax.add_patch(Rectangle((i - 0.46, y - 0.42), 0.92, 0.84, fc=COLORS[t], ec="none"))
            txt = ABBR[t] + ("?" if side == "pred" and w["review"] else "")
            ax.text(i, y, txt, ha="center", va="center", fontsize=7.5, color="white", weight="bold")
            if side == "pred" and w["pred"] != w["true"]:
                ax.plot(i, y + 0.52, marker="v", ms=4, color=INK, clip_on=False)
        ax.text(0.3, y, label, ha="right", va="center", fontsize=9, color=INK)
    ax.set_xlim(-0.6, N_SLOTS + 0.6)
    ax.set_ylim(-0.6, 1.75)
    ax.set_xticks(range(1, N_SLOTS + 1))
    ax.set_xticklabels([str(i) for i in range(1, N_SLOTS + 1)], fontsize=7, color=INK_MUTED)
    ax.set_yticks([])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fp = ", ".join(flags_pred) or "없음"
    ft = ", ".join(flags_true) or "없음"
    ax.set_title(f"{lot}  —  새 웨이퍼 {len(ws)}장 / 반복 패턴(K={K_MAIN}) 예측: {fp}  ·  실제: {ft}",
                 fontsize=9.5, loc="left", color=INK)


def legend_handles():
    h = [Patch(fc=COLORS[t], label=f"{ABBR[t]} = {t}") for t in TYPES]
    h.append(Patch(fc=ABSENT_COLOR, label="902장에 없는 웨이퍼"))
    return h


SEQ_NOTE = "칸 번호 = waferIndex(1~25).  '?' = 사람 확인 필요(1위 확률 < 0.5).  ▼ = 예측이 실제와 다름."


def plot_seq_one(ws, lot, fp, ft, path):
    fig, ax = plt.subplots(figsize=(12, 2.3))
    draw_seq(ax, ws, lot, fp, ft)
    fig.legend(handles=legend_handles(), loc="lower center", ncol=10, fontsize=7.5, frameon=False,
               bbox_to_anchor=(0.5, 0.0))
    fig.text(0.01, 0.17, SEQ_NOTE, fontsize=7.5, color=INK_MUTED)
    fig.subplots_adjust(left=0.05, right=0.99, top=0.84, bottom=0.36)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_seq_all(items, path):
    n = len(items)
    fig, axes = plt.subplots(n, 1, figsize=(12, 1.45 * n + 1.2), squeeze=False)
    for ax, (lot, ws, fp, ft) in zip(axes[:, 0], items):
        draw_seq(ax, ws, lot, fp, ft)
    fig.legend(handles=legend_handles(), loc="lower center", ncol=10, fontsize=7.5, frameon=False)
    fig.suptitle(f"반복 패턴 lot(K={K_MAIN}, 예측 또는 실제 기준)의 웨이퍼 순서\n{SEQ_NOTE}",
                 fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.03, 1, 1 - 0.75 / (1.45 * n + 1.2)))
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------- 보고서 ----------------

def fmt_set(s):
    return ", ".join(sorted(s)) if s else "없음"


def fmt_pairs(s):
    return ", ".join(f"{l}:{t}" for l, t in sorted(s)) if s else "없음"


def write_report(wafers, rows, lots, comps, seq_info, path):
    n_lots = len(rows)
    size_dist = Counter(r["n_wafers"] for r in rows)
    n_review = sum(w["review"] for w in wafers)
    acc = sum(w["pred"] == w["true"] for w in wafers)
    L = []
    L.append("# 06 누적 원인 추리기: 새 웨이퍼의 lot별 패턴 몰림\n")
    L.append("비유: 한 학생만 기침하면 감기지만, 같은 반 세 명이 같은 증상이면 교실(공정 묶음)을 의심한다. "
             "여기서 반 = lot, 증상 = 예측 불량 유형이다.\n")
    L.append("## 입력과 규칙\n")
    L.append(f"- 새 웨이퍼: 05의 lot fold 0, {len(wafers)}장 / lot {n_lots}개 "
             f"(예측 정확도 {acc}/{len(wafers)} = {acc / len(wafers) * 100:.1f}%, 사람 확인 필요 {n_review}장)")
    L.append("- lot 크기(새 웨이퍼 안에서 장수: lot 수): " +
             ", ".join(f"{k}장: {v}개" for k, v in sorted(size_dist.items())))
    L.append("- 05 결과표의 lotName·waferIndex·정답이 data/wafer_lot_map.csv와 185장 모두 같음을 확인했다. "
             "또 새 웨이퍼 lot들의 902장 속 웨이퍼는 모두 fold 0에 있다(lot 단위 분할이라서). "
             "즉 lot별 장수는 902장 기준으로는 빠짐없이 센 것이다.")
    L.append(f"- 판정 규칙(결과 보기 전에 정함): 한 lot 안에서 none이 아닌 같은 유형이 **{K_MAIN}장 이상**이면 반복 패턴 lot. "
             "사람 확인 필요 웨이퍼도 예측 유형 그대로 센다(따로 표시만 함).\n")

    mc = next(c for c in comps if c["k"] == K_MAIN)
    L.append(f"## 핵심 결과 (K = {K_MAIN})\n")
    L.append(f"- 실제 기준 반복 패턴 lot {len(mc['true'])}개 중 예측으로 찾은 것 {len(mc['hit'])}개, 놓친 것 {len(mc['miss'])}개.")
    L.append(f"- 예측이 반복 패턴 lot으로 표시한 {len(mc['pred'])}개 중 실제로도 반복인 것 {len(mc['hit'])}개, 잘못 표시한 것 {len(mc['false'])}개.")
    L.append(f"- 유형까지 맞춘 (lot,유형)은 실제 {mc['n_true_pairs']}쌍 중 {len(mc['pair_hit'])}쌍, 예측 {mc['n_pred_pairs']}쌍 중 {len(mc['pair_hit'])}쌍.")
    L.append("- 놓치거나 잘못 표시한 lot에서 예측이 틀린 웨이퍼 (waferIndex: 예측 → 실제, ?=사람 확인 필요):")
    for lot in sorted(mc["miss"] | mc["false"] | {l for l, _ in mc["pair_false"]}):
        errs = [f"{w['idx']}{'?' if w['review'] else ''}: {w['pred']} → {w['true']}"
                for w in sorted(lots[lot], key=lambda w: w["idx"]) if w["pred"] != w["true"]]
        kind = "놓침" if lot in mc["miss"] else ("잘못 표시" if lot in mc["false"] else "lot은 맞음, 유형 하나 더 표시")
        L.append(f"  - {lot} ({kind}): " + "; ".join(errs))
    L.append("")
    L.append("## 1. K = 2 / 3 / 4 에 따라 달라지는 것\n")
    L.append("| K | 예측 기준 반복 lot | 실제 기준 반복 lot | 맞게 찾은 lot | 놓친 lot | 잘못 표시한 lot | (lot,유형) 맞춤 / 실제 / 예측 |")
    L.append("|---|---|---|---|---|---|---|")
    for c in comps:
        L.append(f"| {c['k']}{' (기준)' if c['k'] == K_MAIN else ''} | {len(c['pred'])} | {len(c['true'])} | "
                 f"{len(c['hit'])} | {len(c['miss'])} | {len(c['false'])} | "
                 f"{len(c['pair_hit'])} / {c['n_true_pairs']} / {c['n_pred_pairs']} |")
    L.append("")
    L.append("- 맞게 찾은 lot = 예측으로도 실제로도 반복 패턴 lot. 놓친 lot = 실제로는 반복인데 예측으로는 못 찾음. "
             "잘못 표시한 lot = 예측으로는 반복인데 실제로는 아님.")
    L.append("- (lot,유형) 맞춤 = lot과 반복 유형까지 같은 경우. lot은 맞혀도 유형이 다르면 여기서는 틀린 것으로 센다.\n")
    for c in comps:
        L.append(f"**K = {c['k']}**")
        L.append(f"- 맞게 찾은 lot: {fmt_set(c['hit'])}")
        L.append(f"- 놓친 lot: {fmt_set(c['miss'])}")
        L.append(f"- 잘못 표시한 lot: {fmt_set(c['false'])}")
        L.append(f"- 놓친 (lot,유형): {fmt_pairs(c['pair_miss'])}")
        L.append(f"- 잘못 표시한 (lot,유형): {fmt_pairs(c['pair_false'])}\n")

    L.append(f"## 2. 반복 패턴 lot 상세 (K = {K_MAIN}, 예측 또는 실제 기준)\n")
    L.append("waferIndex 순서 그림: `06_lot_cluster_seq_<lot>.png`, 모아 보기 `06_lot_cluster_seq_all.png`.\n")
    L.append("| lot | 새 웨이퍼 장수 | 판정(예측 / 실제) | 반복 유형의 waferIndex (예측 판정 기준, 없으면 실제) | 가장 긴 연속 구간 | 그 구간 안 빠진 번호 | 사람 확인 필요 | 예측 맞음 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for s in seq_info:
        L.append(f"| {s['lot']} | {s['n']} | {s['fp'] or '-'} / {s['ft'] or '-'} | {s['idx_text']} | "
                 f"{s['run_text']} | {s['gap_text']} | {s['n_review']} | {s['n_correct']}/{s['n']} |")
    L.append("")
    L.append("- 가장 긴 연속 구간 = 반복 유형 웨이퍼의 waferIndex가 1씩 이어지는 가장 긴 길이. "
             "빠진 번호 = 그 유형 웨이퍼의 처음~끝 번호 사이에서 902장에 아예 없는 번호 수 "
             "(원본에서는 같은 유형이었을 수도, 아니었을 수도 있어 알 수 없다).\n")

    L.append("## 3. 해석할 때 주의할 점 (한계)\n")
    L.append("1. **이 902장은 원본 lot의 일부 웨이퍼만 들어 있다.** WM-811K의 lot은 웨이퍼 25장(waferIndex 1~25)인데, "
             f"새 웨이퍼 lot {n_lots}개 중 {size_dist.get(1, 0)}개는 1장뿐이다. 902장은 유형별로 약 100장씩 고른 "
             "부분집합이라, 어떤 lot에 같은 유형이 많이 보이는 것은 실제 공정의 몰림이 아니라 **뽑는 방식** 때문일 수 있다 "
             "(예: 00에서 random 100장 중 18장이 lot46104 한 곳, none 100장이 lot 6개에서 나옴). "
             "그래서 여기서 나온 '반복 패턴 lot'은 원인 확정이 아니라 **다시 볼 후보** 목록이다. "
             "반대로 902장에 없는 웨이퍼에 같은 패턴이 더 있었을 수도 있어, 놓친 몰림도 있을 수 있다.")
    L.append("2. **설비·layer·날짜 정보가 없다.** 데이터에는 lotName과 waferIndex뿐이라, 몰림이 보여도 "
             "어느 장비·공정 단계·시점 문제인지 이어 볼 수 없다. lot 사이의 시간 순서도 알 수 없다(lot 번호가 시간 순이라는 보장 없음).")
    L.append("3. **waferIndex 연속이 곧 공정 순서라는 보장이 없다.** 원본에는 waferIndex의 뜻(슬롯 번호인지 처리 순서인지)이 "
             "적혀 있지 않다. 그림의 '연속'은 번호가 이어진다는 뜻일 뿐이다.")
    L.append("4. **표본이 작다.** 반복 패턴 lot이 몇 개뿐이라 '얼마나 맞게 찾는가'는 몇 개 lot의 결과이고, "
             "다른 fold나 다른 표본에서 같은 비율이 나온다는 근거는 없다.")
    L.append("5. **기준 K는 임의로 정한 값이다.** K를 바꾸면 결과가 달라지는 정도는 1번 표에 그대로 적었다. "
             "K=2는 우연히 겹친 2장도 잡고, K=4는 작은 lot의 몰림을 놓친다.")
    L.append("6. 예측 기반 판정은 05 B 모델(정확도 77.3%) 예측을 그대로 쓴다. 사람 확인 필요 웨이퍼를 빼거나 "
             "다르게 세는 방식은 쓰지 않았다(규칙을 바꾸지 않음).\n")
    L.append("## 출력 파일\n")
    L.append("- `results/06_lot_summary.csv`: lot별 예측(pred_*)·실제(true_*) 유형 장수, 사람 확인 필요 장수와 번호, "
             "K=2/3/4 판정(repeat_pred_k*, repeat_true_k*), n_in_902(902장 속 그 lot의 장수)")
    L.append("- `results/06_lot_cluster_heatmap.png`: lot × 유형 히트맵 (예측 / 실제)")
    L.append("- `results/06_lot_cluster_seq_*.png`: 반복 패턴 lot별 waferIndex 순서 그림")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------- 실행 ----------------

def main():
    setup_font()
    wafers, n902 = load_wafers()
    rows, lots = summarize_lots(wafers, n902)

    fields = list(rows[0].keys())
    with open(RESULTS_DIR / "06_lot_summary.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)

    comps = [compare(rows, k) for k in K_LIST]
    plot_heatmap(rows, RESULTS_DIR / f"{PREFIX}heatmap.png")

    # 이전 실행에서 남은 lot별 그림 지우기 (06 그림만)
    for p in RESULTS_DIR.glob(f"{PREFIX}seq_*.png"):
        p.unlink()

    rowmap = {r["lotName"]: r for r in rows}
    main_c = comps[K_LIST.index(K_MAIN)]
    target = sorted(main_c["pred"] | main_c["true"], key=lambda l: (-rowmap[l]["n_wafers"], l))
    items, seq_info = [], []
    for lot in target:
        ws = sorted(lots[lot], key=lambda w: w["idx"])
        r = rowmap[lot]
        fp = [t for t in r[f"repeat_pred_k{K_MAIN}"].split(";") if t]
        ft = [t for t in r[f"repeat_true_k{K_MAIN}"].split(";") if t]
        plot_seq_one(ws, lot, fp, ft, RESULTS_DIR / f"{PREFIX}seq_{lot}.png")
        items.append((lot, ws, fp, ft))
        idx_parts, run_parts, gap_parts = [], [], []
        present = {w["idx"] for w in ws}
        for t in (fp or ft):
            side = "pred" if fp else "true"
            idxs = sorted(w["idx"] for w in ws if w[side] == t)
            idx_parts.append(f"{t}({'예측' if fp else '실제'}): {' '.join(map(str, idxs))}")
            run_parts.append(f"{t}: {longest_run(idxs)}장")
            gap_parts.append(f"{t}: {sum(1 for i in range(idxs[0], idxs[-1] + 1) if i not in present)}개")
        seq_info.append(dict(lot=lot, n=len(ws), fp=", ".join(fp), ft=", ".join(ft),
                             idx_text="; ".join(idx_parts), run_text="; ".join(run_parts),
                             gap_text="; ".join(gap_parts), n_review=r["n_needs_review"],
                             n_correct=r["n_pred_correct"]))
    if items:
        plot_seq_all(items, RESULTS_DIR / f"{PREFIX}seq_all.png")

    write_report(wafers, rows, lots, comps, seq_info, RESULTS_DIR / f"{PREFIX}report.md")

    print(f"새 웨이퍼 {len(wafers)}장, lot {len(rows)}개")
    for c in comps:
        print(f"K={c['k']}: 예측 {len(c['pred'])}, 실제 {len(c['true'])}, 맞음 {len(c['hit'])}, "
              f"놓침 {len(c['miss'])}, 잘못 {len(c['false'])} | 쌍 맞음 {len(c['pair_hit'])}/{c['n_true_pairs']} (예측 쌍 {c['n_pred_pairs']})")
    for s in seq_info:
        print(s)


if __name__ == "__main__":
    main()
