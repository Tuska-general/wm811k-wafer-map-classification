"""01_baseline에서 실제로는 불량인데 none으로 예측된 테스트 이미지 조사 (조사 전용, 방법 변경 없음).

- 01_baseline.py는 수정하지 않고 함수만 불러 쓴다. 분할·템플릿·임계값도 01과 똑같이 다시 만든다.
- 이미지마다 확인하는 것:
  1) 기준색 분류 결과(배경/정상/결함 픽셀 수)
  2) "노란 정도": 웨이퍼 픽셀을 정상색→결함색 선분에 투영한 위치 t (0=정상색, 1=결함색).
     기준색 최근접 분류에서 정상/결함의 경계는 대략 t=0.5. 0.25<=t<0.5인 픽셀은
     "결함색 쪽으로 기울었지만 정상으로 분류된 픽셀"(색이 뭉개진 결함 후보)로 센다.
  3) 8개 템플릿과의 상관계수: none 템플릿 값, none 다음으로 높은 유형과 그 차이
- 결과: results/02_missed12_*.csv / *.png (보고서 md는 이 출력으로 따로 작성)

실행: .venv/bin/python scripts/02_missed12_investigate.py
"""

import csv
import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

# 01_baseline.py를 모듈로 불러온다 (파일 이름이 숫자로 시작해 import 문을 못 씀)
_spec = importlib.util.spec_from_file_location("baseline", ROOT / "scripts" / "01_baseline.py")
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)

N_COMPARE = 3  # 유형마다 옆에 놓을, 제대로 맞힌 이미지 장수
BLUR_LOW = 0.25  # 이 값 이상 0.5 미만이면 "결함색 쪽으로 기운 정상 픽셀"로 셈


def yellowness(img):
    """픽셀을 정상색→결함색 선분에 투영한 위치 t (0=정상색, 1=결함색)."""
    normal, defect = b.REF_COLORS[b.NORMAL], b.REF_COLORS[b.DEFECT]
    axis = defect - normal
    return ((img - normal) @ axis) / (axis @ axis)


def template_corrs(mask, templates):
    """8개 템플릿과의 상관계수. 마스크 값이 모두 같으면 NaN(np.corrcoef 경고는 숨김)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return {c: float(np.corrcoef(mask.ravel(), t.ravel())[0, 1]) for c, t in templates.items()}


def rebuild_baseline():
    """01과 같은 데이터·분할·템플릿·예측을 다시 만든다."""
    paths, labels, images = b.load_dataset()
    pc = b.classify_pixels(images)
    masks = (pc == b.DEFECT).astype(np.float64)
    ratios, dcount = b.defect_ratio(pc)
    tr, te = train_test_split(
        np.arange(len(labels)), test_size=b.TEST_SIZE, random_state=b.RANDOM_STATE, stratify=labels
    )
    thr, *_ = b.search_threshold(ratios[tr], labels[tr])
    templates = b.build_templates(masks[tr], labels[tr])
    pred, _ = b.predict(masks[te], ratios[te], dcount[te], templates, thr)
    return dict(paths=paths, labels=labels, images=images, pc=pc, masks=masks,
                ratios=ratios, dcount=dcount, tr=tr, te=te, templates=templates, pred=pred)


def check_against_saved(d):
    """다시 만든 예측이 01 결과 파일과 같은지 확인 (다르면 중단)."""
    saved = {r["file"]: r["pred"] for r in csv.DictReader(open(RESULTS_DIR / "01_baseline_test_predictions.csv"))}
    mine = {f"{d['paths'][i].parent.name}/{d['paths'][i].name}": p for i, p in zip(d["te"], d["pred"])}
    if saved != mine:
        raise RuntimeError("01_baseline 결과 파일과 다시 만든 예측이 달라요.")


def describe(i, d, why):
    """이미지 한 장의 색 분포와 템플릿 상관계수 요약."""
    pc, img = d["pc"][i], d["images"][i]
    wafer = pc != b.BACKGROUND
    t = yellowness(img)[wafer]
    corrs = template_corrs(d["masks"][i], d["templates"])
    others = {c: v for c, v in corrs.items() if c != b.NONE}
    second = max(others, key=lambda c: -np.inf if np.isnan(others[c]) else others[c])
    return {
        "file": f"{d['paths'][i].parent.name}/{d['paths'][i].name}",
        "true": d["labels"][i],
        "why_none": why,
        "bg_px": int((pc == b.BACKGROUND).sum()),
        "normal_px": int((pc == b.NORMAL).sum()),
        "defect_px": int((pc == b.DEFECT).sum()),
        "defect_ratio": round(float(d["ratios"][i]), 3),
        "max_t": round(float(t.max()), 3),
        "blur_candidates_px": int(((t >= BLUR_LOW) & (t < 0.5)).sum()),
        "corr_none": round(corrs[b.NONE], 4),
        "best_other": second,
        "corr_best_other": round(others[second], 4),
        "corr_true": round(corrs.get(d["labels"][i], np.nan), 4),
        "margin_none_minus_other": round(corrs[b.NONE] - others[second], 4),
    }


def write_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def plot_images(missed, compare, d):
    """행 = 놓친 이미지 1장: [원본 | 기준색 분류 결과 | 같은 유형에서 맞힌 원본 N장]."""
    n_cols = 2 + N_COMPARE
    fig, axes = plt.subplots(len(missed), n_cols, figsize=(2.0 * n_cols, 2.1 * len(missed)))
    cls_cmap = matplotlib.colors.ListedColormap(b.REF_COLORS / 255.0)
    for r, i in enumerate(missed):
        cells = [(d["images"][i] / 255.0, None, f"MISSED {d['paths'][i].name}\n{d['labels'][i]} (defect px {int(d['dcount'][i])})"),
                 (d["pc"][i], cls_cmap, "pixel class (nearest color)")]
        cells += [(d["images"][j] / 255.0, None, f"correct {d['paths'][j].name}\n(defect px {int(d['dcount'][j])})")
                  for j in compare[d["labels"][i]]]
        for c, ax in enumerate(axes[r]):
            ax.axis("off")
            if c < len(cells):
                arr, cmap, title = cells[c]
                ax.imshow(arr, cmap=cmap, vmin=0 if cmap else None, vmax=2 if cmap else None, interpolation="nearest")
                ax.set_title(title, fontsize=7, color="crimson" if c == 0 else "black")
    fig.suptitle("01_baseline: defective wafers predicted as none (test set, 12 images)\n"
                 "col1 = original JPEG, col2 = nearest-color class (purple bg / teal normal / yellow defect), "
                 "col3-5 = correctly predicted, same type", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.975))  # 제목과 첫 줄이 겹치지 않게
    fig.savefig(RESULTS_DIR / "02_missed12_images.png", dpi=130)
    plt.close(fig)


def plot_yellowness(missed, compare, d):
    """놓친 12장 vs 같은 유형에서 맞힌 이미지들의 웨이퍼 픽셀 t 분포 (t>=0.1만, 로그 축)."""
    def collect(idx):
        out = []
        for i in idx:
            t = yellowness(d["images"][i])[d["pc"][i] != b.BACKGROUND]
            out.append(t[t >= 0.1])
        return np.concatenate(out)
    comp_idx = sorted({j for js in compare.values() for j in js})
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(0.1, 1.3, 49)
    ax.hist(collect(missed), bins=bins, alpha=0.6, label=f"missed (n={len(missed)} images)",
            weights=np.full(len(collect(missed)), 1 / len(missed)))
    ax.hist(collect(comp_idx), bins=bins, alpha=0.6, label=f"comparison: correct, same types, first {N_COMPARE} per type by filename (n={len(comp_idx)})",
            weights=np.full(len(collect(comp_idx)), 1 / len(comp_idx)))
    ax.axvline(0.5, color="k", ls="--", lw=1)
    ax.set_yscale("log")
    ax.text(0.51, 0.04, "normal | defect boundary (t=0.5)", fontsize=8, transform=ax.get_xaxis_transform())
    ax.set_xlabel("yellowness t (0 = normal-die color, 1 = defect-die color), wafer pixels with t >= 0.1")
    ax.set_ylabel("pixels per image")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "02_missed12_yellowness_hist.png", dpi=130)
    plt.close(fig)


def jpeg_speckle_simulation():
    """정상색 바탕에 결함색 점(1칸/2x2/3x3)을 찍고 Pillow 기본 JPEG(품질 75, 4:2:0)로 저장한 뒤
    그 칸들이 어느 기준색으로 분류되는지 본다. 색은 DATA_SOURCE.md 7-1절의 실제 이미지 평균색."""
    import io
    teal, yellow = np.array([39, 143, 130]), np.array([245, 231, 48])
    lines = []
    for name, size in [("1칸", 1), ("2x2", 2), ("3x3", 3)]:
        arr = np.tile(teal, (32, 32, 1)).astype(np.uint8)
        arr[16:16 + size, 16:16 + size] = yellow
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, "JPEG")
        out = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"), dtype=np.float64)
        cls = b.classify_pixels(out[None])[0][16:16 + size, 16:16 + size]
        px = out[16:16 + size, 16:16 + size].reshape(-1, 3).astype(int).tolist()
        lines.append(f"  결함 점 {name}: 결함으로 분류 {int((cls == b.DEFECT).sum())}/{size * size}칸, JPEG 후 색 예 {px[:2]}")
    return lines


def none_template_lines(d):
    """none 템플릿이 어디에 몰려 있는지, 그 칸이 유형별로 얼마나 결함인지."""
    yy, xx = np.mgrid[:32, :32]
    edge = np.hypot(yy - 15.5, xx - 15.5) >= 12
    lines = ["템플릿별 결함 질량 중 가장자리(중심에서 12칸 이상) 비율:"]
    lines += [f"  {c}: {t[edge].sum() / t.sum():.2f}" for c, t in d["templates"].items()]
    nt = d["templates"][b.NONE]
    hot = np.argwhere(nt >= 0.3)
    lines.append("none 템플릿 값 0.3 이상 칸(행,열): " + ", ".join(f"({r},{c})={nt[r, c]:.2f}" for r, c in hot))
    lines.append("유형별(902장 전체) 위 칸 중 하나라도 결함인 이미지 비율:")
    for c in sorted(set(d["labels"])):
        m = d["masks"][d["labels"] == c][:, hot[:, 0], hot[:, 1]]
        lines.append(f"  {c}: {(m.max(axis=1) > 0).mean():.2f}")
    return lines, hot


def main():
    d = rebuild_baseline()
    check_against_saved(d)

    te, labels, pred = d["te"], d["labels"], d["pred"]
    missed = [i for i, p in zip(te, pred) if p == b.NONE and labels[i] != b.NONE]
    missed.sort(key=lambda i: d["dcount"][i])
    rows = [describe(i, d, "defect_px=0 rule" if d["dcount"][i] == 0 else "none template won")
            for i in missed]
    write_csv(rows, RESULTS_DIR / "02_missed12_details.csv")

    # 비교용: 같은 유형에서 제대로 맞힌 테스트 이미지 (파일 이름 순 앞의 N장, 고정)
    correct = [i for i, p in zip(te, pred) if p == labels[i]]
    compare = {c: sorted((i for i in correct if labels[i] == c), key=lambda i: d["paths"][i].name)[:N_COMPARE]
               for c in sorted({labels[i] for i in missed})}
    comp_rows = [describe(j, d, "correct") for js in compare.values() for j in js]
    write_csv(comp_rows, RESULTS_DIR / "02_missed12_compare_correct.csv")

    # 참고: 같은 유형의 맞힌 테스트 이미지 전체의 결함 픽셀 수 분포
    print("유형별 '맞힌' 테스트 이미지의 결함 픽셀 수 (최소/중앙값/최대):")
    for c in compare:
        v = np.array([d["dcount"][i] for i in correct if labels[i] == c])
        print(f"  {c}: n={len(v)} min={v.min()} median={np.median(v):.0f} max={v.max()}")

    # 참고: 학습셋 none 템플릿이 얼마나 비어 있는지
    nt = d["templates"][b.NONE]
    print(f"none 템플릿: 평균 {nt.mean():.4f}, 최대 {nt.max():.4f}, 0이 아닌 칸 {int((nt > 0).sum())}/1024")

    plot_images(missed, compare, d)
    plot_yellowness(missed, compare, d)

    nt_lines, hot = none_template_lines(d)
    hot_hits = [int(d["masks"][i][hot[:, 0], hot[:, 1]].max()) for i in missed]
    summary = (
        [f"놓친 이미지 {len(missed)}장 (결함 픽셀 0개: {sum(r['defect_px'] == 0 for r in rows)}장)",
         "JPEG 모의실험 (Pillow 기본 저장):"] + jpeg_speckle_simulation() + nt_lines
        + [f"놓친 12장 중 none 템플릿 상위 칸에 결함이 있는 장수: {sum(hot_hits)}/{len(missed)}"]
    )
    (RESULTS_DIR / "02_missed12_summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
