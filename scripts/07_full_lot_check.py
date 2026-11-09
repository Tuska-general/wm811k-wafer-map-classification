"""07: 06에서 몰림으로 표시된 lot 10개를 원본 WM-811K의 lot 전체(웨이퍼 최대 25장)로 다시 본다.

비유: 06은 반 학생 25명 중 출석부에 이름이 적힌 몇 명만 보고 "같은 증상이 많다"고 한 것이다.
07은 반 전체 명단을 꺼내, 출석부에 없던 학생들의 진단 기록(원본 라벨)까지 확인한다.

대상 lot (결과를 보기 전에 정함)
- results/06_lot_summary.csv 에서 K=3 판정이 예측(repeat_pred_k3) 또는 실제(repeat_true_k3) 중
  하나라도 있는 lot = 06의 웨이퍼 순서 그림 10개와 같은 lot

하는 일
- 원본 WM811K.pkl을 00과 같은 방식(00_source_check.py의 허용 목록 Unpickler)으로 읽는다.
  웨이퍼 맵 내용은 읽지 않고 lotName, waferIndex, failureType, trainTestLabel만 쓴다.
- lot마다 원본 웨이퍼 번호별 유형표를 만든다. failureType이 비어 있으면 '라벨 없음'.
- 902장에 들어 있던 웨이퍼(in_902)와 없던 웨이퍼를 나눠 센다.
- 라벨 없는 웨이퍼에 모델을 적용하지 않는다. 원본 라벨만 본다.

몰림이 원본 lot 전체에서도 유지되는지 보는 숫자 (06의 판정 유형마다)
- 902장 안 장수 / 원본 lot 전체에서 같은 유형 장수 / 902장 밖에서 더 나온 장수
- 원본 lot 전체의 라벨 있는 웨이퍼 중 그 유형 비율, 라벨 없는 웨이퍼 수
- 902장 밖 라벨 있는 웨이퍼의 유형 구성
  주의: 902장 안 웨이퍼의 라벨도 원본 라벨이므로, 원본 전체에서 같은 유형 장수는 902장 안 장수보다
  줄어들 수 없다. 그래서 "유지"는 장수가 아니라 "lot 전체에서도 그 유형이 두드러지는가"(비율)로 본다.

출력 (01~06 결과는 바꾸지 않음)
- results/07_full_lot_wafers.csv  : 대상 lot의 원본 웨이퍼 전체 (lot, 번호, 원본 유형, 902장 포함 여부 등)
- results/07_full_lot_summary.csv : lot × 06 판정 유형별 유지 여부 숫자
- results/07_full_lot_types.csv   : lot별 원본 전체 / 902장 안 유형 장수, 같은 규칙(K=3)을 원본 라벨에 적용한 판정
- results/07_full_lot_check.png   : lot마다 웨이퍼 번호 1~25 한 줄 그림 (굵은 테두리 = 902장에 있던 웨이퍼)
- results/07_full_lot_report.md   : 보고서 (lot별 웨이퍼 번호별 유형표 포함)

실행: .venv/bin/python scripts/07_full_lot_check.py   (원본 pkl 읽기에 1~2분)
"""

import csv
import importlib.util
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
SUMMARY06 = RESULTS_DIR / "06_lot_summary.csv"
LOT_MAP_CSV = ROOT / "data" / "wafer_lot_map.csv"
ALERT_CSV = RESULTS_DIR / "05_alert_all.csv"
K = 3
N_SLOTS = 25
UNLABELED = "라벨 없음"
NONE = "none"

TYPES = ["Center", "Donut", "Edge Local", "Edge Ring", "Local", "Scratch", "random", "near full", NONE]
COLORS = {
    "Center": "#2a78d6", "Donut": "#eb6834", "Edge Local": "#1baf7a", "Edge Ring": "#eda100",
    "Local": "#e87ba4", "Scratch": "#008300", "random": "#6250d6", "near full": "#e34948",
    NONE: "#b5b4ad",
}
ABBR = {"Center": "C", "Donut": "D", "Edge Local": "EL", "Edge Ring": "ER", "Local": "L",
        "Scratch": "S", "random": "R", "near full": "NF", NONE: "n"}
UNLABELED_COLOR = "#ffffff"
MISSING_COLOR = "#f1f0ec"
INK = "#2b2b29"
INK_MUTED = "#6b6a64"
KO_FONTS = [Path("/mnt/c/Windows/Fonts/malgun.ttf"), Path("/mnt/c/Windows/Fonts/malgunbd.ttf")]


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


src00 = _load("src00", "00_source_check.py")
ORIG_TO_TYPE = {v: k for k, v in src00.FOLDER_TO_TYPE.items()}  # 원본 이름(Edge-Loc 등) → 이 프로젝트 이름


def setup_font():
    for p in KO_FONTS:
        if not p.exists():
            raise SystemExit(f"한글 글꼴 파일이 없어요: {p}")
        font_manager.fontManager.addfont(str(p))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(KO_FONTS[0])).get_name()
    plt.rcParams["axes.unicode_minus"] = False


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------- 입력 ----------------

def target_lots():
    """06의 K=3 판정(예측 또는 실제)이 있는 lot과 그 판정 유형."""
    out = {}
    for r in read_csv(SUMMARY06):
        fp = [t for t in r[f"repeat_pred_k{K}"].split(";") if t]
        ft = [t for t in r[f"repeat_true_k{K}"].split(";") if t]
        if fp or ft:
            out[r["lotName"]] = dict(pred=fp, true=ft, n06=int(r["n_wafers"]))
    return out


def load_original_lots(lots):
    """원본 pkl에서 대상 lot의 행만 뽑는다."""
    df, _ = src00.load_pkl_light(src00.PKL_PATH)
    row_index, cols = src00.to_columns(df)
    for c in ("lotName", "waferIndex", "failureType", "trainTestLabel"):
        if c not in cols:
            raise SystemExit(f"원본에 {c} 칸이 없음")
    rows = []
    for i, lot in enumerate(cols["lotName"]):
        lot = str(lot)
        if lot not in lots:
            continue
        wi = float(cols["waferIndex"][i])
        if not wi.is_integer():
            raise SystemExit(f"{lot}: waferIndex가 정수가 아님 ({wi})")
        raw = src00.unwrap_label(cols["failureType"][i])
        if raw in ("", "0"):
            t = UNLABELED
        elif raw in ORIG_TO_TYPE:
            t = ORIG_TO_TYPE[raw]
        else:
            raise SystemExit(f"{lot}: 모르는 원본 유형 {raw!r}")
        rows.append(dict(lotName=lot, waferIndex=int(wi), source_row=int(row_index[i]),
                         original_label=raw if raw not in ("", "0") else "",
                         type=t, trainTestLabel=src00.unwrap_label(cols["trainTestLabel"][i])))
    return rows, len(row_index)


def attach_subset(rows):
    """902장 포함 여부, 05 새 웨이퍼 예측을 붙이고 902장 쪽과 원본이 맞는지 확인한다."""
    by_src = {int(r["source_row"]): r for r in read_csv(LOT_MAP_CSV)}
    alert = {r["file"]: r for r in read_csv(ALERT_CSV)}
    seen = set()
    for r in rows:
        m = by_src.get(r["source_row"])
        r["in_902"] = int(m is not None)
        r["file_name"] = m["file_name"] if m else ""
        r["pred_type_05"] = alert[m["file_name"]]["pred_type"] if m and m["file_name"] in alert else ""
        if m:
            seen.add(r["source_row"])
            if (m["lotName"], int(m["waferIndex"]), m["type"]) != (r["lotName"], r["waferIndex"], r["type"]):
                raise SystemExit(f"902장 지도와 원본이 다름: 원본 행 {r['source_row']}")
    expected = {int(r["source_row"]) for r in by_src.values()
                if r["lotName"] in {x["lotName"] for x in rows}}
    if expected != seen:
        raise SystemExit(f"902장 중 원본에서 못 찾은 행: {sorted(expected - seen)[:5]}")
    return rows


# ---------------- 정리 ----------------

def summarize(rows, lots):
    by_lot = defaultdict(list)
    for r in rows:
        by_lot[r["lotName"]].append(r)
    out = []
    for lot, info in lots.items():
        ws = by_lot.get(lot, [])
        if not ws:
            raise SystemExit(f"원본에 lot이 없음: {lot}")
        idx_count = Counter(w["waferIndex"] for w in ws)
        labeled = [w for w in ws if w["type"] != UNLABELED]
        outside = [w for w in ws if not w["in_902"]]
        outside_lab = [w for w in outside if w["type"] != UNLABELED]
        for t in dict.fromkeys(info["pred"] + info["true"]):
            n_in = sum(1 for w in ws if w["in_902"] and w["type"] == t)
            n_all = sum(1 for w in labeled if w["type"] == t)
            out.append(dict(
                lotName=lot, flagged_type=t,
                flagged_by="+".join(s for s, l in (("예측", info["pred"]), ("실제", info["true"])) if t in l),
                n_original=len(ws), n_in_902=sum(w["in_902"] for w in ws),
                n_labeled=len(labeled), n_unlabeled=len(ws) - len(labeled),
                n_type_in_902=n_in, n_type_original=n_all, n_type_outside_902=n_all - n_in,
                share_of_labeled=round(n_all / len(labeled), 3) if labeled else "",
                n_outside_labeled=len(outside_lab),
                outside_labeled_types=" ".join(f"{k}:{v}" for k, v in
                                               sorted(Counter(w["type"] for w in outside_lab).items(),
                                                      key=lambda kv: TYPES.index(kv[0]))),
                n_unlabeled_outside_902=sum(1 for w in outside if w["type"] == UNLABELED),
                type_waferIndex_original=" ".join(str(w["waferIndex"]) for w in sorted(labeled, key=lambda w: w["waferIndex"]) if w["type"] == t),
                missing_waferIndex=" ".join(str(i) for i in range(1, N_SLOTS + 1) if i not in idx_count),
                duplicate_waferIndex=" ".join(str(i) for i, c in sorted(idx_count.items()) if c > 1),
                trainTestLabel_counts=" ".join(f"{k or '(빈값)'}:{v}" for k, v in sorted(Counter(w["trainTestLabel"] for w in ws).items())),
            ))
    return out, by_lot


def lot_table(by_lot, lots):
    """lot마다 원본 전체 유형 장수와, 06과 같은 규칙(none이 아닌 같은 유형 K장 이상)을
    902장 안 원본 라벨 / 원본 lot 전체 라벨에 각각 적용한 결과."""
    out = []
    for lot, info in lots.items():
        ws = by_lot[lot]
        full = Counter(w["type"] for w in ws)
        sub = Counter(w["type"] for w in ws if w["in_902"])
        rep_sub = [t for t in TYPES if t != NONE and sub.get(t, 0) >= K]
        rep_full = [t for t in TYPES if t != NONE and full.get(t, 0) >= K]
        defect = sorted(((full[t], t) for t in TYPES if t != NONE and full.get(t, 0)), key=lambda x: (-x[0], TYPES.index(x[1])))
        row = dict(lotName=lot, n_original=len(ws), n_in_902=sum(w["in_902"] for w in ws),
                   pred_flag_06=";".join(info["pred"]), true_flag_06=";".join(info["true"]),
                   repeat_true_k3_in_902=";".join(rep_sub), repeat_true_k3_full_lot=";".join(rep_full),
                   new_in_full_lot=";".join(t for t in rep_full if t not in rep_sub),
                   top_defect_full_lot=f"{defect[0][1]}:{defect[0][0]}" if defect else "")
        for t in TYPES + [UNLABELED]:
            row[f"full_{t}"] = full.get(t, 0)
        for t in TYPES + [UNLABELED]:
            row[f"in902_{t}"] = sub.get(t, 0)
        out.append(row)
    return out


# ---------------- 그림 ----------------

def plot(by_lot, lots, path):
    order = list(lots)
    n = len(order)
    fig, axes = plt.subplots(n, 1, figsize=(12, 0.95 * n + 1.6), squeeze=False)
    for ax, lot in zip(axes[:, 0], order):
        ws = {w["waferIndex"]: w for w in by_lot[lot]}
        for i in range(1, N_SLOTS + 1):
            w = ws.get(i)
            if w is None:
                ax.add_patch(Rectangle((i - 0.46, -0.42), 0.92, 0.84, fc=MISSING_COLOR, ec="none"))
                continue
            t = w["type"]
            fc = UNLABELED_COLOR if t == UNLABELED else COLORS[t]
            ec, lw = (INK, 2.2) if w["in_902"] else (INK_MUTED if t == UNLABELED else "none", 0.6)
            ax.add_patch(Rectangle((i - 0.46, -0.42), 0.92, 0.84, fc=fc, ec=ec, lw=lw))
            ax.text(i, 0, "–" if t == UNLABELED else ABBR[t], ha="center", va="center", fontsize=7.5,
                    color=INK_MUTED if t == UNLABELED else "white", weight="bold")
        info = lots[lot]
        ax.set_title(f"{lot}  —  06 판정 예측: {', '.join(info['pred']) or '없음'} · 실제: {', '.join(info['true']) or '없음'}"
                     f"   (원본 {len(ws)}장 중 902장에 {sum(w['in_902'] for w in ws.values())}장)",
                     fontsize=9, loc="left", color=INK)
        ax.set_xlim(0.4, N_SLOTS + 0.6)
        ax.set_ylim(-0.55, 0.55)
        ax.set_xticks(range(1, N_SLOTS + 1))
        ax.set_xticklabels([str(i) for i in range(1, N_SLOTS + 1)], fontsize=7, color=INK_MUTED)
        ax.set_yticks([])
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    h = [Patch(fc=COLORS[t], label=f"{ABBR[t]} = {t}") for t in TYPES]
    h += [Patch(fc=UNLABELED_COLOR, ec=INK_MUTED, label="– = 라벨 없음"),
          Patch(fc=MISSING_COLOR, label="원본에 없는 번호"),
          Patch(fc="white", ec=INK, lw=2.2, label="굵은 테두리 = 902장에 있던 웨이퍼")]
    fig.legend(handles=h, loc="lower center", ncol=6, fontsize=7.5, frameon=False)
    fig.suptitle("06에서 몰림으로 표시된 lot 10개: 원본 WM-811K lot 전체의 원본 라벨 (모델 예측 아님)",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 1 - 0.5 / (0.95 * n + 1.6)))
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------- 보고서 ----------------

def verdict(s):
    """보고서용 한 줄 설명. 숫자를 그대로 말로 옮길 뿐, 새 판정 기준을 만들지 않는다."""
    return (f"902장 안 {s['n_type_in_902']}장 → 원본 전체 {s['n_type_original']}장 "
            f"(902장 밖에서 {s['n_type_outside_902']}장 더). 라벨 있는 {s['n_labeled']}장 중 "
            f"{s['share_of_labeled'] * 100:.0f}%, 라벨 없음 {s['n_unlabeled']}장.")


def write_report(summary, lot_rows, by_lot, lots, n_rows, path):
    L = ["# 07 원본 lot 전체 확인: 06 몰림 lot 10개\n"]
    L.append("비유: 06은 출석부에 이름이 있던 학생만 보고 \"같은 증상이 많다\"고 했다. 07은 반 전체 명단(원본 lot)을 꺼내 "
             "나머지 학생의 진단 기록(원본 라벨)까지 본다. 진단 기록이 없는 학생(라벨 없음)은 추측하지 않는다.\n")
    L.append("## 방법\n")
    L.append(f"- 원본 `WM811K.pkl`({n_rows:,}행)을 00과 같은 방식으로 읽어, 대상 lot의 행을 모두 뽑았다.")
    L.append(f"- 대상 = 06에서 K={K} 판정이 예측 또는 실제로 하나라도 있는 lot {len(lots)}개 (06 순서 그림과 같은 lot).")
    L.append("- failureType이 비어 있으면 '라벨 없음'. 라벨 없는 웨이퍼에는 모델을 적용하지 않았다.")
    L.append("- 902장에 있던 웨이퍼는 원본 행 번호로 `data/wafer_lot_map.csv`와 맞췄고, lot·번호·유형이 모두 같음을 확인했다.")
    L.append("- 902장 안 웨이퍼의 라벨도 원본 라벨이라, 원본 전체의 같은 유형 장수는 902장 안 장수보다 줄 수 없다. "
             "그래서 \"유지되는가\"는 장수보다 **lot 전체(라벨 있는 웨이퍼)에서 그 유형이 차지하는 비율**과 "
             "**902장 밖에서 같은 유형이 더 나왔는가**로 본다.\n")

    L.append("## 핵심 결과 (숫자는 아래 표에서 계산)\n")
    same = [s for s in summary if s["n_type_outside_902"] == 0]
    more = [s for s in summary if s["n_type_outside_902"] > 0]
    L.append(f"- 06 판정 (lot,유형) {len(summary)}개 중 {len(same)}개는 그 유형 웨이퍼가 902장 안에 이미 전부 있었다 "
             f"(902장 밖에서 같은 유형 0장). 더 나온 것은 {len(more)}개: "
             + (", ".join(f"{s['lotName']} {s['flagged_type']} +{s['n_type_outside_902']}" for s in more) or "없음") + ".")
    major = [s for s in summary if s["share_of_labeled"] != "" and s["share_of_labeled"] > 0.5]
    L.append(f"- 라벨 있는 웨이퍼의 절반을 넘는 판정 유형은 {len(major)}개"
             + (" (" + ", ".join(f"{s['lotName']} {s['flagged_type']} {s['share_of_labeled'] * 100:.0f}%" for s in major) + ")" if major else "")
             + f". 나머지는 라벨 있는 웨이퍼의 {min(s['share_of_labeled'] for s in summary if s not in major) * 100:.0f}"
             f"~{max(s['share_of_labeled'] for s in summary if s not in major) * 100:.0f}%이다.")
    newl = [r for r in lot_rows if r["new_in_full_lot"]]
    L.append(f"- 같은 규칙을 원본 lot 전체에 적용하면 902장 안에서는 안 보이던 반복 유형이 {len(newl)}개 lot에서 새로 생긴다: "
             + ", ".join(f"{r['lotName']} {r['new_in_full_lot'].replace(';', ', ')}" for r in newl) + ".")
    hidden = [r for r in lot_rows if r["top_defect_full_lot"] and r["top_defect_full_lot"].split(":")[0]
              not in (r["pred_flag_06"].split(";") + r["true_flag_06"].split(";"))]
    L.append(f"- 원본 lot 전체에서 가장 많은 불량 유형이 06 판정 유형과 다른 lot {len(hidden)}개: "
             + ", ".join(f"{r['lotName']}(최다 {r['top_defect_full_lot'].replace(':', ' ')}장)" for r in hidden) + ".")
    L.append(f"- 대상 lot 원본 {sum(r['n_original'] for r in lot_rows)}장 중 라벨 없음은 "
             f"{sum(r['full_' + UNLABELED] for r in lot_rows)}장이다(이 10개 lot에 한한 숫자).\n")
    L.append(f"## 1. lot 단위: 같은 규칙(none이 아닌 같은 유형 {K}장 이상)을 원본 라벨에 적용\n")
    L.append("06의 규칙을 그대로 두고, 대상만 902장 안 웨이퍼 → 원본 lot 전체로 넓혔다. 판정에 쓴 유형은 모두 원본 라벨이다.\n")
    L.append("| lot | 원본 / 902장 안 | 06 판정 (예측 / 실제) | 902장 안 원본 라벨로 판정 | 원본 lot 전체로 판정 | 전체에서 새로 생긴 유형 | 원본 전체 유형 장수 (none 아닌 것) | none | 라벨 없음 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in lot_rows:
        defect = ", ".join(f"{t} {r['full_' + t]}" for t in TYPES if t != NONE and r["full_" + t])
        L.append(f"| {r['lotName']} | {r['n_original']} / {r['n_in_902']} | {r['pred_flag_06'] or '-'} / {r['true_flag_06'] or '-'} | "
                 f"{r['repeat_true_k3_in_902'] or '-'} | {r['repeat_true_k3_full_lot'] or '-'} | {r['new_in_full_lot'] or '-'} | "
                 f"{defect} | {r['full_' + NONE]} | {r['full_' + UNLABELED]} |")
    L.append("")
    L.append("## 2. 06 판정 유형별 요약\n")
    L.append("| lot | 06 판정 유형 (판정 근거) | 원본 장수 / 902장 안 | 라벨 있음 / 없음 | 그 유형: 902장 안 → 원본 전체 | 라벨 있는 웨이퍼 중 비율 | 902장 밖 라벨 있는 웨이퍼 유형 |")
    L.append("|---|---|---|---|---|---|---|")
    for s in summary:
        L.append(f"| {s['lotName']} | {s['flagged_type']} ({s['flagged_by']}) | {s['n_original']} / {s['n_in_902']} | "
                 f"{s['n_labeled']} / {s['n_unlabeled']} | {s['n_type_in_902']} → {s['n_type_original']} | "
                 f"{s['share_of_labeled'] * 100:.0f}% | {s['outside_labeled_types'] or '없음'} |")
    L.append("")
    tot_unl = sum(sum(1 for w in by_lot[l] if w["type"] == UNLABELED) for l in lots)
    tot_out = sum(sum(1 for w in by_lot[l] if not w["in_902"]) for l in lots)
    tot_out_lab = sum(sum(1 for w in by_lot[l] if not w["in_902"] and w["type"] != UNLABELED) for l in lots)
    L.append(f"- 대상 lot 10개의 902장 밖 웨이퍼 {tot_out}장 중 라벨 있는 것 {tot_out_lab}장, 라벨 없음 {tot_out - tot_out_lab}장 "
             f"(전체 라벨 없음 {tot_unl}장).\n")
    L.append("lot·유형별 한 줄 설명:\n")
    for s in summary:
        L.append(f"- **{s['lotName']} {s['flagged_type']}** ({s['flagged_by']}): {verdict(s)}")
    L.append("")

    L.append("## 3. lot별 원본 웨이퍼 번호별 유형\n")
    L.append("표시: `유형*` = 902장에 있던 웨이퍼, `라벨 없음` = 원본 failureType이 비어 있음, "
             "`(원본에 없음)` = 그 번호 행이 원본에 없음. 902장에 있던 웨이퍼는 06의 예측(05 B 모델)도 함께 적었다.\n")
    for lot in lots:
        ws = {w["waferIndex"]: w for w in by_lot[lot]}
        info = lots[lot]
        L.append(f"### {lot}  (06 판정 예측: {', '.join(info['pred']) or '없음'} · 실제: {', '.join(info['true']) or '없음'})\n")
        L.append("| 번호 | " + " | ".join(str(i) for i in range(1, N_SLOTS + 1)) + " |")
        L.append("|---|" + "---|" * N_SLOTS)
        cells, preds = [], []
        for i in range(1, N_SLOTS + 1):
            w = ws.get(i)
            if w is None:
                cells.append("(원본에 없음)")
                preds.append("")
            else:
                cells.append(w["type"] + ("*" if w["in_902"] else ""))
                preds.append(w["pred_type_05"])
        L.append("| 원본 유형 | " + " | ".join(cells) + " |")
        L.append("| 06 예측 | " + " | ".join(p or "" for p in preds) + " |")
        L.append("")

    L.append("## 4. 해석할 때 주의할 점\n")
    L.append("1. 라벨 없는 웨이퍼는 불량이었는지 정상이었는지 알 수 없다. 그 웨이퍼들까지 같은 유형이었다면 몰림은 더 크고, "
             "none이었다면 비율은 더 낮아진다. 오늘은 원본 라벨만 봤으므로 이 부분은 판단하지 않았다.")
    L.append("2. 설비·layer·날짜 정보는 원본에도 없다. lot 전체에서 몰림이 유지돼도 원인(장비·공정)을 특정할 수는 없다.")
    L.append("3. waferIndex가 처리 순서인지 슬롯 번호인지는 원본에 적혀 있지 않다.")
    L.append("4. 원본 라벨 자체가 사람이 붙인 것이라 틀린 라벨이 있을 수 있다(이 프로젝트에서 검증하지 않음).\n")
    L.append("## 출력 파일\n")
    L.append("- `results/07_full_lot_wafers.csv`: 대상 lot의 원본 웨이퍼 전체 (원본 행 번호, 원본 라벨, trainTestLabel, 902장 포함 여부, 05 예측)")
    L.append("- `results/07_full_lot_summary.csv`: lot × 06 판정 유형별 숫자")
    L.append("- `results/07_full_lot_types.csv`: lot별 원본 전체·902장 안 유형 장수와 같은 규칙의 판정")
    L.append("- `results/07_full_lot_check.png`: lot별 웨이퍼 번호 1~25 원본 라벨 그림")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)


def main():
    setup_font()
    lots = target_lots()
    print(f"대상 lot {len(lots)}개: {', '.join(lots)}")
    rows, n_rows = load_original_lots(lots)
    rows = attach_subset(rows)
    rows.sort(key=lambda r: (list(lots).index(r["lotName"]), r["waferIndex"], r["source_row"]))
    summary, by_lot = summarize(rows, lots)
    write_csv(RESULTS_DIR / "07_full_lot_wafers.csv", rows)
    write_csv(RESULTS_DIR / "07_full_lot_summary.csv", summary)
    plot(by_lot, lots, RESULTS_DIR / "07_full_lot_check.png")
    lot_rows = lot_table(by_lot, lots)
    write_csv(RESULTS_DIR / "07_full_lot_types.csv", lot_rows)
    write_report(summary, lot_rows, by_lot, lots, n_rows, RESULTS_DIR / "07_full_lot_report.md")
    for r in lot_rows:
        print(r["lotName"], "902안:", r["repeat_true_k3_in_902"] or "-", "| 전체:", r["repeat_true_k3_full_lot"] or "-",
              "| 새로:", r["new_in_full_lot"] or "-", "| 최다:", r["top_defect_full_lot"])
    for s in summary:
        print(s["lotName"], s["flagged_type"], s["flagged_by"], verdict(s), "| 밖:", s["outside_labeled_types"],
              "| 빠진번호:", s["missing_waferIndex"] or "-", "| 중복:", s["duplicate_waferIndex"] or "-",
              "|", s["trainTestLabel_counts"])


if __name__ == "__main__":
    main()
