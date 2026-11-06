"""원본 WM-811K와 902장 서브셋 대조 (출처 확인용).

하는 일:
1. 원본 zip(data/raw/MIR-WM811K.zip)의 크기와 SHA-256을 기록한다.
2. zip 안의 Python/ 폴더만 data/raw/MIR-WM811K/Python/ 에 푼다(이미 있으면 건너뜀).
3. WM811K.pkl(약 2GB)을 스트리밍으로 읽는다.
   - 메모리가 3.7GB라 pandas로 통째로 열 수 없다.
   - 그래서 허용 목록에 있는 클래스만 만드는 Unpickler로 읽고,
     웨이퍼 맵 배열(uint8)은 크기(shape)만 남기고 내용은 버린다.
   - 필요한 칸: failureType, lotName, waferIndex, trainTestLabel, dieSize, 웨이퍼 맵 크기
4. 902장 각 파일의 번호를 원본 행 번호로 보고, 그 행의 유형이 폴더 유형과 같은지 확인한다.
5. data/wafer_lot_map.csv 와 results/00_source_check_summary.txt 를 저장한다.

방법을 바꾸지 않는다. 분할 실험(로트 기준 분할 등)은 하지 않는다.

실행: .venv/bin/python scripts/00_source_check.py
"""

import builtins
import csv
import hashlib
import io
import json
import pickle
import pickletools
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from numpy._core.multiarray import _reconstruct

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
ZIP_PATH = RAW_DIR / "MIR-WM811K.zip"
PKL_MEMBER = "MIR-WM811K/Python/WM811K.pkl"
PY_PREFIX = "MIR-WM811K/Python/"
PKL_PATH = RAW_DIR / PKL_MEMBER
IMAGE_DIR = ROOT / "WM811k Dataset"
OUT_CSV = ROOT / "data" / "wafer_lot_map.csv"
OUT_SUMMARY = ROOT / "results" / "00_source_check_summary.txt"
OUT_JSON = ROOT / "results" / "00_source_check_summary.json"

# 인터넷 아카이브 사본 (2022-06-17 저장)
SOURCE_URL = (
    "http://web.archive.org/web/20220617223043/"
    "http://mirlab.org/dataSet/public/MIR-WM811K.zip"
)
EXPECTED_ZIP_SIZE = 344_542_743

# 서브셋 폴더 이름 → 원본 failureType 이름
FOLDER_TO_TYPE = {
    "Center": "Center",
    "Donut": "Donut",
    "Edge Local": "Edge-Loc",
    "Edge Ring": "Edge-Ring",
    "Local": "Loc",
    "Scratch": "Scratch",
    "near full": "Near-full",
    "none": "none",
    "random": "Random",
}

# 이보다 큰 bytearray는 pickle 메모에 남기지 않는다(웨이퍼 맵 원자료라서)
BIG_BUFFER = 64


# ---------------------------------------------------------------------------
# 1~2. zip 확인과 Python/ 폴더 풀기
# ---------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_python_folder() -> list[str]:
    """zip 안의 Python/ 폴더만 푼다. 경로가 예상 밖이면 멈춘다."""
    extracted = []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for info in zf.infolist():
            name = info.filename
            if not name.startswith(PY_PREFIX) or info.is_dir():
                continue
            # 압축 파일 안 경로가 data/raw 밖으로 나가지 않는지 확인
            target = (RAW_DIR / name).resolve()
            if RAW_DIR.resolve() not in target.parents:
                raise RuntimeError(f"예상 밖 경로: {name}")
            if target.exists() and target.stat().st_size == info.file_size:
                extracted.append(f"{name} (이미 있음)")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                for chunk in iter(lambda: src.read(1 << 20), b""):
                    dst.write(chunk)
            if target.stat().st_size != info.file_size:
                raise RuntimeError(f"풀린 크기가 다름: {name}")
            extracted.append(name)
    return extracted


# ---------------------------------------------------------------------------
# 3. 스트리밍 Unpickler
# ---------------------------------------------------------------------------
class Stub:
    """pandas 객체 대신 쓰는 빈 그릇. 생성 인자와 상태만 기록한다."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.state = None

    def __setstate__(self, state):
        self.state = state


def make_stub_class(module: str, name: str):
    return type(name, (Stub,), {"_origin": f"{module}.{name}"})


class WaferShape:
    """웨이퍼 맵 배열 대신 크기만 담는다."""

    def __init__(self, shape):
        self.shape = tuple(shape)


def frombuffer_light(buf, dtype, shape, order):
    """numpy _frombuffer 대체. 웨이퍼 맵(uint8)은 크기만, 나머지는 실제 배열로."""
    dtype = np.dtype(dtype)
    if dtype == np.uint8:
        return WaferShape(shape)
    arr = np.frombuffer(bytes(buf), dtype=dtype)
    return arr.reshape(shape, order=order)


def unpickle_block(values, placement, ndim=None):
    return {"values": values, "placement": placement, "ndim": ndim}


def new_index(cls, d):
    return {"index_class": getattr(cls, "_origin", str(cls)), "data": d}


GET_OPS = {"GET", "BINGET", "LONG_BINGET"}


def find_referenced_memo_keys(path: Path) -> set[int]:
    """1차 훑기: 나중에 다시 꺼내 쓰는(GET) 메모 번호만 모은다.

    pickle은 객체를 만들 때마다 메모에 번호를 붙여 두는데, 실제로 다시 꺼내 쓰는 건 일부뿐이다.
    다시 쓰이는 번호만 남기면 메모가 수천만 개로 불어나지 않는다.
    """
    keys = set()
    with path.open("rb") as f:
        for op, arg, _pos in pickletools.genops(io.BufferedReader(f, buffer_size=1 << 22)):
            if op.name in GET_OPS:
                keys.add(int(arg))
    return keys


class MemoDropBig(dict):
    """메모리를 아끼는 pickle 메모 (2차 읽기용).

    - 1차 훑기에서 다시 쓰인다고 확인된 번호만 남긴다.
    - 웨이퍼 맵 원자료(큰 bytearray)는 다시 쓰이더라도 남기지 않는다(쓰이면 아래에서 멈춤).
    - 남기지 않은 번호를 찾으면 pickle이 오류를 내고 멈추므로, 값이 조용히 틀려지는 일은 없다.
    """

    def __init__(self, keep: set[int]):
        super().__init__()
        self.keep = keep
        self.count = 0  # MEMOIZE 번호는 len(memo)로 매겨지므로 남기지 않은 것까지 센다

    def __len__(self):
        return self.count

    def __setitem__(self, key, value):
        self.count = max(self.count, key + 1)
        if key not in self.keep:
            return
        if isinstance(value, (bytes, bytearray)) and len(value) > BIG_BUFFER:
            return
        super().__setitem__(key, value)


class AllowListUnpickler(pickle._Unpickler):
    """허용 목록 클래스만 만드는 Unpickler.

    순수 파이썬 구현(pickle._Unpickler)을 써야 메모를 바꿔 끼울 수 있다.
    허용 목록 밖 클래스가 나오면 바로 멈춘다(내려받은 파일의 코드를 실행하지 않기 위해).
    """

    def __init__(self, f, keep_memo: set[int]):
        super().__init__(f)
        self.memo = MemoDropBig(keep_memo)
        self.seen_globals = Counter()

    def find_class(self, module, name):
        self.seen_globals[f"{module}.{name}"] += 1
        mod = module.replace("numpy._core", "numpy.core")
        if (mod, name) == ("numpy.core.numeric", "_frombuffer"):
            return frombuffer_light
        if (mod, name) == ("numpy.core.multiarray", "_reconstruct"):
            return _reconstruct
        if (module, name) in (("numpy", "ndarray"), ("numpy", "dtype")):
            return getattr(np, name)
        if (module, name) == ("pandas._libs.internals", "_unpickle_block"):
            return unpickle_block
        if (module, name) == ("pandas.core.indexes.base", "_new_Index"):
            return new_index
        if module.startswith(("pandas.core.", "pandas._libs.")):
            return make_stub_class(module, name)
        if (module, name) == ("builtins", "slice"):
            return builtins.slice
        raise pickle.UnpicklingError(f"허용 목록 밖 클래스: {module}.{name}")


def load_pkl_light(path: Path):
    keep = find_referenced_memo_keys(path)
    print(f"다시 쓰이는 메모 번호: {len(keep):,}개")
    with path.open("rb") as f:
        up = AllowListUnpickler(io.BufferedReader(f, buffer_size=1 << 22), keep)
        df = up.load()
    return df, up.seen_globals


# ---------------------------------------------------------------------------
# 4. 읽은 표를 칸별 목록으로 정리
# ---------------------------------------------------------------------------
def unwrap_label(v):
    """failureType/trainTestLabel은 [['none']] 같은 배열이거나 빈 배열이다."""
    arr = np.asarray(v, dtype=object).ravel() if not isinstance(v, str) else [v]
    return str(arr[0]) if len(arr) else ""


def to_columns(df_stub):
    """DataFrame 그릇에서 열 이름별 값 목록과 행 번호(index)를 꺼낸다."""
    state = df_stub.state
    mgr = state["_mgr"] if isinstance(state, dict) else state
    # pandas 버전에 따라 BlockManager가 생성 인자(blocks, axes)로 오거나 상태로 온다
    axes, blocks = find_axes_and_blocks(mgr)
    col_names = [str(c) for c in index_values(axes[0])]
    row_index = np.asarray(index_values(axes[1]))
    columns = {}
    for blk in blocks:
        values = blk["values"]
        rows = placement_list(blk["placement"], len(col_names))
        for j, col_pos in enumerate(rows):
            columns[col_names[col_pos]] = values[j] if values.ndim == 2 else values
    return row_index, columns


def find_axes_and_blocks(mgr):
    st = mgr.state
    if isinstance(st, tuple) and len(st) >= 4 and isinstance(st[3], dict):
        info = st[3]["0.14.1"]
        return info["axes"], info["blocks"]
    # BlockManager(blocks, axes, ...) 형태
    if len(mgr.args) >= 2 and all(isinstance(b, dict) and "values" in b for b in mgr.args[0]):
        return mgr.args[1], list(mgr.args[0])
    shapes = [type(a).__name__ for a in mgr.args]
    raise RuntimeError(f"예상 밖 BlockManager 형태: state={type(st).__name__}, args={shapes}")


def index_values(ix):
    """_new_Index(dict) 또는 RangeIndex 그릇에서 값 목록을 꺼낸다."""
    if isinstance(ix, dict) and "data" in ix:
        d = ix["data"]
        if "data" in d:
            return list(d["data"])
        if "start" in d:  # RangeIndex
            return list(range(d["start"], d["stop"], d.get("step", 1)))
    if isinstance(ix, Stub):
        st = ix.state if ix.state is not None else (ix.args[1] if len(ix.args) > 1 else None)
        if isinstance(st, dict) and "start" in st:
            return list(range(st["start"], st["stop"], st.get("step", 1)))
    raise RuntimeError(f"예상 밖 Index 형태: {ix!r}")


def placement_list(p, n):
    if isinstance(p, slice):
        return list(range(*p.indices(n)))
    return [int(x) for x in np.asarray(p).ravel()]


# ---------------------------------------------------------------------------
# 5. 902장과 원본 행 대조
# ---------------------------------------------------------------------------
def list_subset_images():
    """(폴더 이름, 파일 이름, 파일 번호) 목록. Windows 흔적 파일은 뺀다."""
    items = []
    for folder in sorted(FOLDER_TO_TYPE):
        for p in sorted((IMAGE_DIR / folder).glob("*.jpg")):
            items.append((folder, p.name, int(p.stem)))
    return items


def match_subset(images, row_index, cols):
    pos_of = {int(r): i for i, r in enumerate(row_index)}
    out, problems = [], []
    for folder, fname, num in images:
        i = pos_of.get(num)
        if i is None:
            problems.append(f"{folder}/{fname}: 원본에 행 번호 {num} 없음")
            continue
        ftype = unwrap_label(cols["failureType"][i])
        split = unwrap_label(cols["trainTestLabel"][i])
        if ftype != FOLDER_TO_TYPE[folder]:
            problems.append(f"{folder}/{fname}: 원본 유형 {ftype!r}가 폴더와 다름")
        wafer_index = cols["waferIndex"][i]
        out.append(
            {
                "file_name": f"{folder}/{fname}",
                "type": folder,
                "source_row": num,
                "lotName": str(cols["lotName"][i]),
                "waferIndex": int(wafer_index) if float(wafer_index).is_integer() else wafer_index,
                "_source_type": ftype,
                "_split": split,
            }
        )
    return out, problems


# ---------------------------------------------------------------------------
# 6. 저장
# ---------------------------------------------------------------------------
CSV_FIELDS = ["file_name", "type", "source_row", "lotName", "waferIndex"]


def save_csv(rows):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["type"], r["source_row"])))


def summarize(rows, all_type_counts, zip_info, problems, n_rows):
    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    per_type = {}
    for folder in sorted(by_type):
        rs = by_type[folder]
        lots = Counter(r["lotName"] for r in rs)
        top_lot, top_n = lots.most_common(1)[0]
        per_type[folder] = {
            "images": len(rs),
            "lots": len(lots),
            "top_lot": top_lot,
            "top_lot_images": top_n,
            "splits": dict(Counter(r["_split"] for r in rs)),
        }
    all_lots = {r["lotName"] for r in rows}
    shared = Counter()
    lot_types = defaultdict(set)
    for r in rows:
        lot_types[r["lotName"]].add(r["type"])
    for lot, ts in lot_types.items():
        shared[len(ts)] += 1
    return {
        "zip": zip_info,
        "source_rows": n_rows,
        "source_type_counts": all_type_counts,
        "matched_images": len(rows),
        "problems": problems,
        "per_type": per_type,
        "total_lots": len(all_lots),
        "lots_by_number_of_types": {str(k): v for k, v in sorted(shared.items())},
    }


def write_summary_text(s):
    lines = [
        "00_source_check: 원본 WM-811K와 902장 서브셋 대조",
        f"원본 zip: {s['zip']['path']}",
        f"  크기 {s['zip']['size']:,}바이트 (예상 {EXPECTED_ZIP_SIZE:,}), SHA-256 {s['zip']['sha256']}",
        f"  출처 {SOURCE_URL}",
        f"원본 행 수: {s['source_rows']:,}",
        "원본 유형별 행 수: "
        + " / ".join(f"{k} {v:,}" for k, v in sorted(s["source_type_counts"].items(), key=lambda kv: -kv[1])),
        f"대조된 이미지: {s['matched_images']}장, 문제 {len(s['problems'])}건",
    ]
    lines += [f"  - {p}" for p in s["problems"]]
    lines += ["", "유형별 lot 개수 (서브셋 기준)", f"{'유형':<12}{'장수':>6}{'lot 수':>8}  최다 lot (장수)  원본 분할"]
    for t, d in s["per_type"].items():
        lines.append(f"{t:<12}{d['images']:>6}{d['lots']:>8}  {d['top_lot']} ({d['top_lot_images']})  {d['splits']}")
    lines += [
        "",
        f"서로 다른 lot 전체: {s['total_lots']}개",
        "lot 하나에 들어 있는 유형 수별 lot 개수: " + str(s["lots_by_number_of_types"]),
    ]
    OUT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return "\n".join(lines)


def main():
    size = ZIP_PATH.stat().st_size
    if size != EXPECTED_ZIP_SIZE:
        raise RuntimeError(f"zip 크기 {size:,}가 예상 {EXPECTED_ZIP_SIZE:,}와 다름")
    zip_info = {"path": str(ZIP_PATH.relative_to(ROOT)), "size": size, "sha256": sha256_of(ZIP_PATH)}
    print("zip SHA-256:", zip_info["sha256"])
    for name in extract_python_folder():
        print("풀기:", name)
    df, seen = load_pkl_light(PKL_PATH)
    print("pickle 안의 클래스:", dict(seen))
    row_index, cols = to_columns(df)
    all_counts = Counter(unwrap_label(v) for v in cols["failureType"])
    all_counts = {("(라벨 없음)" if k in ("", "0") else k): v for k, v in all_counts.items()}
    images = list_subset_images()
    rows, problems = match_subset(images, row_index, cols)
    save_csv(rows)
    s = summarize(rows, all_counts, zip_info, problems, len(row_index))
    print(write_summary_text(s))


if __name__ == "__main__":
    main()
