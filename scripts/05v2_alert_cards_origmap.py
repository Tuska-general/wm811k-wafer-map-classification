"""05v2: 05 알림 카드의 웨이퍼 그림만 원본 WM-811K 맵(칩 1개 = 1칸)으로 다시 그린다.

비유: 채점(판정)은 기존 32x32 복사본으로 그대로 하고, 보고서에 붙이는 사진만 원본으로 바꾼다.

하는 일
1. 902장의 원본 맵을 꺼내 캐시 파일로 저장한다 (처음 한 번, 원본 pkl을 두 번 읽어 3~5분).
   - 00과 같은 허용 목록 Unpickler를 쓴다. 메모리(약 2GB)가 부족해 맵 81만 장을 다 들고 있을 수 없어서
     1차 읽기: 맵은 크기와 "몇 번째 맵인지"만 기록 → 902장 행이 몇 번째 맵인지 찾음
     2차 읽기: 그 번호의 맵만 실제 값을 남김
   - 확인: 원본 유형 = 폴더 유형, 1·2차 크기 일치, 값은 0/1/2만, 32x32 이미지와 결함 마스크 상관계수
   - 캐시: data/raw/orig_maps_902.npz (data/raw/는 git에 올리지 않음)
2. 05_alert.py의 build_system / make_alerts를 그대로 불러 판정한다 (32x32 이미지 기준, 코드 수정 없음).
3. results/05_alert_all.csv와 카드 9장의 판정(예상 유형, 확률, 비슷한 맵 3장, 상관계수)이 같은지 확인한다.
   하나라도 다르면 카드를 저장하지 않고 멈춘다.
4. 카드 그림만 원본 맵으로 그려 results2/에 저장한다. 색은 기존 이미지와 같은 viridis 3색
   (0=웨이퍼 밖 보라, 1=정상 칩 청록, 2=불량 칩 노랑).

출력 (results/는 건드리지 않음)
- results2/05_alert_cards/*.png, results2/05_alert_cards_ko/*.png : 카드 9장씩 (파일 이름은 기존과 같음)
- results2/05_alert_cards_check_<en/ko>.txt : 판정 일치 확인과 원본 맵 확인 결과

실행: .venv/bin/python scripts/05v2_alert_cards_origmap.py --lang ko   (또는 --lang en)
"""

import argparse
import csv
import importlib.util
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results2"
CACHE = ROOT / "data" / "raw" / "orig_maps_902.npz"
ALERT_CSV = ROOT / "results" / "05_alert_all.csv"
CHECK_TXT = OUT_DIR / "05_alert_cards_check_{lang}.txt"

# 기존 32x32 이미지의 색과 같게: matplotlib viridis의 양 끝과 가운데 (DATA_SOURCE.md 7-1절)
MAP_CMAP = ListedColormap(np.array([[68, 1, 84], [33, 145, 140], [253, 231, 37]]) / 255.0)

NOTE = {
    "en": "Maps: original WM-811K wafer maps (1 cell = 1 die), for display only. "
          "Prediction, probabilities and similar maps are computed from the same 32x32 images as before.",
    "ko": "그림: 원본 WM-811K 웨이퍼 맵(칩 1개 = 1칸, 표시용). "
          "판정·확률·비슷한 맵은 기존과 같은 32x32 이미지로 계산했어요.",
}
ORIG_SIZE = {"en": "original {h}x{w} dies", "ko": "원본 {h}×{w}칸"}


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


a05 = _load("a05", "05_alert.py")
src00 = _load("src00", "00_source_check.py")
b = a05.b


# ---------------- 1. 원본 맵 꺼내기 ----------------

class MapPickUnpickler(src00.AllowListUnpickler):
    """00의 Unpickler와 같되, 웨이퍼 맵(uint8)마다 순번을 매기고 want에 든 순번만 값을 남긴다."""

    def __init__(self, f, keep_memo, want):
        super().__init__(f, keep_memo)
        self.want = want
        self.n_maps = 0
        self.kept = {}

    def find_class(self, module, name):
        obj = super().find_class(module, name)
        return self._frombuffer if obj is src00.frombuffer_light else obj

    def _frombuffer(self, buf, dtype, shape, order):
        if np.dtype(dtype) != np.uint8:
            return src00.frombuffer_light(buf, dtype, shape, order)
        k = self.n_maps
        self.n_maps += 1
        ws = src00.WaferShape(shape)
        ws.k = k
        if k in self.want:
            self.kept[k] = np.frombuffer(bytes(buf), dtype=np.uint8).reshape(shape, order=order).copy()
        return ws


def read_pass(keep_memo, want):
    with src00.PKL_PATH.open("rb") as f:
        up = MapPickUnpickler(io.BufferedReader(f, buffer_size=1 << 22), keep_memo, want)
        df = up.load()
    return df, up


def subset_rows():
    with open(a05.lot04.LOT_MAP, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def locate_maps(df, rows):
    """1차 읽기 결과에서 902장 행의 맵 순번과 크기를 찾고, 원본 유형이 폴더 유형과 같은지 본다."""
    row_index, cols = src00.to_columns(df)
    if "waferMap" not in cols:
        raise SystemExit("원본에 waferMap 칸이 없음")
    pos_of = {int(r): i for i, r in enumerate(row_index)}
    found = {}
    for r in rows:
        i = pos_of[int(r["source_row"])]
        ftype = src00.unwrap_label(cols["failureType"][i])
        if ftype != src00.FOLDER_TO_TYPE[r["type"]]:
            raise SystemExit(f"{r['file_name']}: 원본 유형 {ftype!r}가 폴더와 다름")
        ws = cols["waferMap"][i]
        if not isinstance(ws, src00.WaferShape):
            raise SystemExit(f"{r['file_name']}: 맵 자리에 예상 밖 값 {type(ws).__name__}")
        found[r["source_row"]] = (ws.k, ws.shape)
    ks = [k for k, _ in found.values()]
    if len(set(ks)) != len(ks):
        raise SystemExit("서로 다른 행이 같은 맵 순번을 가리켜요")
    return found


def extract_maps():
    rows = subset_rows()
    print("원본 pkl 메모 번호 훑는 중...")
    keep = src00.find_referenced_memo_keys(src00.PKL_PATH)
    print("1차 읽기 (맵 순번 찾기)...")
    df, up1 = read_pass(keep, set())
    found = locate_maps(df, rows)
    n1 = up1.n_maps
    del df, up1
    print("2차 읽기 (902장 맵만 남기기)...")
    _, up2 = read_pass(keep, {k for k, _ in found.values()})
    if up2.n_maps != n1:
        raise SystemExit(f"1·2차 맵 개수가 달라요 ({n1} / {up2.n_maps})")
    maps = {}
    for src_row, (k, shape) in found.items():
        m = up2.kept[k]
        if m.shape != tuple(shape):
            raise SystemExit(f"행 {src_row}: 크기가 1·2차에서 달라요 {shape} / {m.shape}")
        if not set(np.unique(m)) <= {0, 1, 2}:
            raise SystemExit(f"행 {src_row}: 0/1/2 밖의 값 {np.unique(m)}")
        maps[str(src_row)] = m
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, **maps)
    print(f"캐시 저장: {CACHE.relative_to(ROOT)} ({len(maps)}장, 맵 전체 {n1:,}개 중)")


def load_maps():
    if not CACHE.exists():
        extract_maps()
    with np.load(CACHE) as z:
        maps = {k: z[k] for k in z.files}
    if len(maps) != 902:
        raise SystemExit(f"캐시 맵 수가 902가 아니에요: {len(maps)}")
    return maps


def self_rank_check(maps, sysd):
    """같은 웨이퍼인지 확인: 원본 불량 칩 위치를 32x32로 줄여 902장 이미지의 결함 마스크와 상관계수를 구하고,
    이미지마다 902개 원본 중 자기 원본이 몇 위인지 센다. 맵을 엉뚱하게 꺼냈다면 1위가 거의 나오지 않는다.
    (결함 0개 등으로 상관계수를 못 구하는 이미지는 뺀다)"""
    src_of = {r["file_name"]: r["source_row"] for r in subset_rows()}
    orig = np.array([np.asarray(Image.fromarray((maps[src_of[f]] == 2).astype(np.float32))
                                .resize((32, 32), Image.BILINEAR), dtype=np.float64).ravel()
                     for f in sysd["files"]])
    img = sysd["masks"].reshape(len(orig), -1)

    def unit(x):
        x = x - x.mean(axis=1, keepdims=True)
        n = np.linalg.norm(x, axis=1, keepdims=True)
        return x / np.where(n == 0, np.inf, n)

    sim = unit(img) @ unit(orig).T
    ok = np.where((img.std(axis=1) > 0) & (orig.std(axis=1) > 0))[0]
    rank = np.array([int((sim[i] > sim[i, i]).sum()) + 1 for i in ok])
    return len(ok), rank


# ---------------- 3. 판정이 기존 결과와 같은지 ----------------

def check_same_as_05(card_items):
    with open(ALERT_CSV, encoding="utf-8") as f:
        old = {r["file"]: r for r in csv.DictReader(f)}
    lines, bad = [], 0
    for name, alert in card_items:
        r = old[name]
        now = {"pred_type": alert["pred"], "top1_prob": round(alert["prob1"], 4),
               "top2_type": alert["pred2"], "top2_prob": round(alert["prob2"], 4),
               "n_defect_pixels": alert["n_defect"]}
        for k, nb in enumerate(alert["neighbors"], 1):
            now[f"sim{k}_file"] = nb["file"]
            now[f"sim{k}_corr"] = round(nb["corr"], 4)
        diff = [k for k, v in now.items()
                if (float(r[k]) != v if isinstance(v, (int, float)) else r[k] != v)]
        bad += bool(diff)
        lines.append(f"  {name}: " + ("같음" if not diff else f"다름 {diff}"))
    return bad, lines


# ---------------- 4. 카드 그림 ----------------

def draw_orig(ax, m, title, lang, color="black"):
    ax.imshow(m, cmap=MAP_CMAP, vmin=0, vmax=2, interpolation="nearest")
    ax.set_title(title + "\n" + ORIG_SIZE[lang].format(h=m.shape[0], w=m.shape[1]), fontsize=9, color=color)
    ax.set_xticks([])
    ax.set_yticks([])


def draw_card(new_map, alert, sysd, header, out_path, map_of, lang):
    """05_alert.draw_card와 배치·문구가 같고, 웨이퍼 그림만 원본 맵이며 맨 아래 안내 한 줄이 붙는다."""
    T = a05.TEXT[lang]
    fig = plt.figure(figsize=(11, 7.0))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1], hspace=0.45, wspace=0.15, top=0.86)
    draw_orig(fig.add_subplot(gs[0, 0]), new_map, T["new"] + "\n" + header, lang)

    ax1 = fig.add_subplot(gs[0, 1:])
    ax1.axis("off")
    badges = [(T["anomaly"] if alert["anomaly"] else T["normal"], "#c0392b" if alert["anomaly"] else "#27ae60")]
    if alert["urgent"]:
        badges.append((T["urgent"], "#8e0000"))
    if alert["review"]:
        badges.append((T["review"], "#d68910"))
    x = 0.0
    for text, color in badges:
        t = ax1.text(x, 0.93, f" {text} ", fontsize=11, color="white", weight="bold", transform=ax1.transAxes,
                     va="center", bbox=dict(boxstyle="round,pad=0.35", fc=color, ec=color))
        fig.canvas.draw()
        x = t.get_window_extent().transformed(ax1.transAxes.inverted()).x1 + 0.05
    vals = dict(pred=alert["pred"], p1=alert["prob1"], pred2=alert["pred2"], p2=alert["prob2"],
                ratio=alert["ratio"], thr=sysd["threshold"], nd=alert["n_defect"],
                fold=a05.NEW_FOLD, npast=len(sysd["past"]))
    ax1.text(0.0, 0.78, "\n".join(s.format(**vals) for s in T["lines"]), fontsize=10.5, va="top",
             transform=ax1.transAxes, **({"family": "monospace"} if T["mono"] else {"linespacing": 1.5}))

    for k, nb in enumerate(alert["neighbors"]):
        sim_txt = T["undefined"] if nb["undefined"] else f"{nb['corr']:.3f}"
        draw_orig(fig.add_subplot(gs[1, k]), map_of(nb["file"]),
                  T["similar"].format(k=k + 1, type=nb["type"]) + f"\n{nb['lot']}  {T['wafer']} {nb['wafer']}\n"
                  + T["corr"].format(v=sim_txt), lang)
    fig.suptitle(T["title"], fontsize=13, weight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.005, NOTE[lang], fontsize=8.5, color="#555555", ha="left", va="bottom")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="05 알림 카드를 원본 맵 그림으로 다시 그림 (판정은 그대로)")
    ap.add_argument("--lang", choices=["en", "ko"], default="ko")
    lang = ap.parse_args().lang
    a05.setup_font(lang)

    maps = load_maps()
    sysd = a05.build_system()
    src_of = {r["file_name"]: r["source_row"] for r in subset_rows()}
    map_of = lambda f: maps[src_of[f]]

    n_ok, rank = self_rank_check(maps, sysd)
    new, labels = sysd["new"], sysd["labels"]
    alerts = a05.make_alerts(sysd["masks"][new], sysd["ratios"][new], sysd)
    y_true = labels[new]
    items = []
    for c in sysd["class_names"]:
        i = int(np.where(y_true == c)[0][0])
        items.append((c, int(new[i]), alerts[i]))

    bad, lines = check_same_as_05([(sysd["files"][g], a) for _, g, a in items])
    report = [f"05v2 카드 확인 (--lang {lang})", "",
              "1) 판정이 results/05_alert_all.csv와 같은가 (카드 9장, 예상 유형·확률·결함 픽셀·비슷한 맵 3장·상관계수)"]
    report += lines + [f"  → 다른 카드 {bad}장", "",
                       "2) 꺼낸 원본 맵이 그 이미지의 웨이퍼인가",
                       "  원본 불량 칩 위치를 32x32로 줄여 이미지 결함 마스크와 상관계수를 구하고,",
                       "  이미지마다 902개 원본 중 자기 원본의 순위를 셈 (엉뚱한 맵이면 1위가 거의 안 나옴)",
                       f"  계산 가능 {n_ok}장 (나머지는 한쪽 결함 0개) 중 자기 원본 1위 {int((rank == 1).sum())}장, "
                       f"3위 안 {int((rank <= 3).sum())}장, 최저 순위 {int(rank.max())}위",
                       "  (원본 유형 = 폴더 유형, 1·2차 읽기 크기 일치, 값 0/1/2만: 캐시 만들 때 확인, 어긋나면 멈춤)"]
    OUT_DIR.mkdir(exist_ok=True)
    Path(str(CHECK_TXT).format(lang=lang)).write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    if bad:
        raise SystemExit("판정이 기존 결과와 달라서 카드를 저장하지 않았어요.")

    T = a05.TEXT[lang]
    card_dir = OUT_DIR / ("05_alert_cards" if lang == "en" else "05_alert_cards_ko")
    for c, g, alert in items:
        name = sysd["files"][g]
        header = f"{name}\n{sysd['lots'][g]}  {T['wafer']} {sysd['wafer_idx'][g]}  ({T['true']}: {c})"
        out = card_dir / f"{c.replace(' ', '_')}_{Path(name).stem}.png"
        draw_card(map_of(name), alert, sysd, header, out, map_of, lang)
        print("카드 저장:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
