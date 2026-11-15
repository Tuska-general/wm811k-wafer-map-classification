"""09: 포트폴리오 슬라이드용 그림만 새로 그린다 (분석·판정·확률은 다시 계산하지 않음).

색: 웨이퍼 바깥 = 검정, 정상 칩 = 흰색, 불량 칩 = 빨강(#E63946).
  1) 유형별 예시 9장: 원본 WM-811K 칩 단위 맵, 800x800, nearest 확대
  2) 평균 히트맵 9장: 01과 같은 계산(7:3 학습셋 결함 마스크 평균, 32x32)
  3) 05v2 알림 카드 2장(near full 긴급, Scratch 사람 확인 필요)을 같은 3색으로
출력: results/portfolio_maps/ (기존 results 파일과 32x32 이미지는 건드리지 않음)
"""
import importlib.util
from pathlib import Path

import numpy as np
from matplotlib.colors import ListedColormap
from PIL import Image
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "portfolio_maps"
SIZE = 800
BLACK, WHITE, RED = (0, 0, 0), (255, 255, 255), (0xE6, 0x39, 0x46)


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


v2 = _load("v2", "05v2_alert_cards_origmap.py")
a05, b = v2.a05, v2.b


def to_png(rgb, path):
    """정사각형 800x800: 정수배 nearest 확대 후 남는 곳은 검정(웨이퍼 바깥)으로 채워 가운데 정렬."""
    h, w, _ = rgb.shape
    k = SIZE // max(h, w)
    big = np.repeat(np.repeat(rgb, k, axis=0), k, axis=1)
    canvas = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
    y, x = (SIZE - big.shape[0]) // 2, (SIZE - big.shape[1]) // 2
    canvas[y:y + big.shape[0], x:x + big.shape[1]] = big
    Image.fromarray(canvas).save(path)


def map_rgb(m):
    return np.array([BLACK, WHITE, RED], dtype=np.uint8)[m]


def heat_rgb(t, outside):
    v = t / t.max() if t.max() > 0 else np.zeros_like(t)
    rgb = np.array(WHITE) + v[..., None] * (np.array(RED) - np.array(WHITE))
    rgb[outside] = BLACK
    return np.round(rgb).astype(np.uint8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths, labels, images = b.load_dataset()
    pc = b.classify_pixels(images)
    masks = (pc == b.DEFECT).astype(np.float64)
    _, dcount = b.defect_ratio(pc)
    tr, _ = train_test_split(np.arange(len(labels)), test_size=b.TEST_SIZE,
                             random_state=b.RANDOM_STATE, stratify=labels)
    templates = b.build_templates(masks[tr], labels[tr])  # 01과 같은 계산(near full 제외)
    nf = labels[tr] == b.NEAR_FULL
    nf_mean = masks[tr][nf].mean(axis=0)  # near full만 같은 방식으로 추가(분류기에는 안 쓰임)

    maps = v2.load_maps()
    rows = {r["file_name"]: r for r in v2.subset_rows()}
    files = [f"{p.parent.name}/{p.name}" for p in paths]
    readme = ["# 포트폴리오 슬라이드용 그림", "",
              "`scripts/09_portfolio_maps.py`로 그렸어요. 분석·판정·확률은 다시 계산하지 않았고, 기존 results 파일과 32×32 이미지는 그대로예요.",
              "", "색: 웨이퍼 바깥 = 검정(#000000), 정상 칩 = 흰색(#FFFFFF), 불량 칩 = 빨강(#E63946). 격자선·글자 없음.",
              "", "## 1) 유형별 예시 (원본 칩 단위 맵, 800×800)", "",
              "고른 기준: 01과 같은 7:3 학습셋 안에서, 32×32 결함 마스크가 그 유형 평균(템플릿)과 상관계수가 가장 높은 웨이퍼. "
              "none은 결함 픽셀이 가장 적은 웨이퍼(같으면 파일 순서 첫 번째).",
              "확대: 칩 1칸을 정수배(800 ÷ 긴 변, 내림)로 nearest 확대하고, 남는 가장자리는 검정으로 채웠어요.", "",
              "| 그림 | 유형 | 파일 | lot | 웨이퍼 번호 | 원본 크기(행×열) | 템플릿 상관 |", "|---|---|---|---|---|---|---|"]
    for c in sorted(set(labels)):
        idx = tr[labels[tr] == c]
        if c == b.NONE:
            pick, score = int(idx[np.argmin(dcount[idx])]), "-"
        else:
            t = (templates[c] if c != b.NEAR_FULL else nf_mean).ravel()
            cs = np.array([np.corrcoef(masks[i].ravel(), t)[0, 1] if masks[i].std() > 0 else -2 for i in idx])
            pick, score = int(idx[np.argmax(cs)]), f"{cs.max():.3f}"
        r = rows[files[pick]]
        m = maps[r["source_row"]]
        name = c.lower().replace(" ", "_") + ".png"
        to_png(map_rgb(m), OUT / name)
        readme.append(f"| {name} | {c} | {files[pick]} | {r['lotName']} | {r['waferIndex']} | {m.shape[0]}×{m.shape[1]} | {score} |")

    readme += ["", "## 2) 평균 히트맵 (32×32 → 800×800)", "",
               "01 분류기 템플릿과 같은 계산값: 7:3 학습셋(test_size=0.3, random_state=42, stratify)에서 유형별 결함 마스크 평균. "
               "near full은 분류기 템플릿에 없어서(01은 near full을 비율 규칙으로 판정) 같은 방식으로 따로 평균을 냈어요.",
               "색: 0 = 흰색 → 그 그림의 최댓값 = 빨강, 연속(그림마다 자기 최댓값 기준). "
               "웨이퍼 바깥(검정) = 그 유형 학습 이미지의 절반 넘게 배경인 칸. 32 × 25 = 800, nearest 확대.", "",
               "| 그림 | 학습 장수 | 최댓값(결함 비율) |", "|---|---|---|"]
    for c in sorted(set(labels)):
        t = templates[c] if c != b.NEAR_FULL else nf_mean
        sel = tr[labels[tr] == c]
        outside = (pc[sel] == b.BACKGROUND).mean(axis=0) > 0.5
        name = f"heatmap_{c.lower().replace(' ', '_')}.png"
        to_png(heat_rgb(t, outside), OUT / name)
        readme.append(f"| {name} | {len(sel)} | {t.max():.3f} |")

    # 3) 카드: 05v2와 같은 판정·문구, 색만 3색
    v2.MAP_CMAP = ListedColormap(np.array([BLACK, WHITE, RED]) / 255.0)
    a05.setup_font("ko")
    sysd = a05.build_system()
    new = sysd["new"]
    alerts = a05.make_alerts(sysd["masks"][new], sysd["ratios"][new], sysd)
    src_of = {r["file_name"]: r["source_row"] for r in rows.values()}
    map_of = lambda f: maps[src_of[f]]
    T = a05.TEXT["ko"]
    readme += ["", "## 3) 알림 카드 (05v2 한국어 카드와 같은 웨이퍼·판정·문구, 맵 색만 3색)", ""]
    for c, out_name, need in [(b.NEAR_FULL, "card_nearfull.png", "urgent"), ("Scratch", "card_scratch.png", "review")]:
        i = int(np.where(sysd["labels"][new] == c)[0][0])  # 05v2와 같은 선택
        g, alert = int(new[i]), alerts[i]
        if not alert[need]:
            raise SystemExit(f"{c} 카드에 '{need}' 표시가 없어요")
        bad, lines = v2.check_same_as_05([(sysd["files"][g], alert)])
        if bad:
            raise SystemExit("판정이 results/05_alert_all.csv와 달라요: " + " ".join(lines))
        name = sysd["files"][g]
        header = f"{name}\n{sysd['lots'][g]}  {T['wafer']} {sysd['wafer_idx'][g]}  ({T['true']}: {c})"
        v2.draw_card(map_of(name), alert, sysd, header, OUT / out_name, map_of, "ko")
        readme.append(f"- {out_name}: {name}, results/05_alert_all.csv와 판정 일치 확인")
    (OUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print("\n".join(readme))


if __name__ == "__main__":
    main()
