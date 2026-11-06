"""1차 분류기(규칙 기반 베이스라인) 재현.

방법 (6월 1차 분류기와 같은 절차):
1. 픽셀 분류: 이미지를 RGB로 읽고, 픽셀마다 기준색 3개 중 가장 가까운 색(유클리드 거리)으로 나눈다.
   - 배경 [64.5, 3.5, 83.0], 정상 다이 [48.0, 149.0, 125.0], 결함 다이 [238.0, 229.0, 48.0]
   - 웨이퍼 영역 = 배경이 아닌 픽셀, 결함 = 결함 다이 픽셀
2. 결함 면적 비율 = 결함 픽셀 수 / 웨이퍼 픽셀 수 × 100
3. 학습/테스트 분할: test_size=0.3, random_state=42, stratify (프로젝트 규칙)
4. near full 임계값: 학습셋에서 20~90%를 0.5 간격으로 탐색해,
   "비율 >= 임계값이면 near full" 판별의 정확도가 가장 높은 값을 고른다.
5. 템플릿: 학습셋에서 near full을 제외한 8개 유형마다 결함 마스크(결함=1, 그 외=0)의 평균
6. 예측: 결함 픽셀 0개 → none / 비율 >= 임계값 → near full /
   그 외 → 8개 템플릿과의 상관계수(np.corrcoef)가 가장 큰 유형
7. 테스트셋 정확도, 유형별 precision/recall/F1, 혼동행렬 그림을 results/에 저장

실행: .venv/bin/python scripts/01_baseline.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 화면 없이 그림 파일만 저장
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "WM811k Dataset"
RESULTS_DIR = ROOT / "results"

# 기준색 (순서: 0=배경, 1=정상 다이, 2=결함 다이)
REF_COLORS = np.array(
    [
        [64.5, 3.5, 83.0],  # 배경
        [48.0, 149.0, 125.0],  # 정상 다이
        [238.0, 229.0, 48.0],  # 결함 다이
    ]
)
BACKGROUND, NORMAL, DEFECT = 0, 1, 2

NEAR_FULL = "near full"
NONE = "none"

# 분할 규칙 (CLAUDE.md 고정값)
TEST_SIZE = 0.3
RANDOM_STATE = 42

# 임계값 탐색 범위: 20.0, 20.5, ..., 90.0
THRESHOLDS = np.round(np.arange(20.0, 90.0 + 1e-9, 0.5), 1)


def load_dataset():
    """폴더 이름을 라벨로 삼아 이미지를 읽는다. 순서는 폴더 이름 → 파일 이름 정렬(재현성 위해 고정)."""
    paths, labels = [], []
    for class_dir in sorted(p for p in DATA_DIR.iterdir() if p.is_dir()):
        for img_path in sorted(class_dir.glob("*.jpg")):
            paths.append(img_path)
            labels.append(class_dir.name)
    images = np.stack(
        [np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) for p in paths]
    )
    return paths, np.array(labels), images


def classify_pixels(images):
    """각 픽셀을 가장 가까운 기준색 번호(0/1/2)로 바꾼다. 결과 모양: (장수, 높이, 너비)."""
    # (N, H, W, 1, 3) - (3, 3) → 기준색마다 거리 제곱
    diff = images[..., np.newaxis, :] - REF_COLORS
    dist2 = (diff**2).sum(axis=-1)
    return dist2.argmin(axis=-1)


def defect_ratio(pixel_classes):
    """결함 면적 비율(%) = 결함 픽셀 수 / 웨이퍼(배경이 아닌) 픽셀 수 × 100."""
    defect = (pixel_classes == DEFECT).sum(axis=(1, 2))
    wafer = (pixel_classes != BACKGROUND).sum(axis=(1, 2))
    if np.any(wafer == 0):
        raise ValueError("웨이퍼 픽셀이 0개인 이미지가 있어요. 비율을 계산할 수 없어요.")
    return defect / wafer * 100.0, defect


def search_threshold(ratios, labels):
    """학습셋에서 near full 판별(비율 >= t) 정확도가 가장 높은 t를 찾는다.
    정확도가 같은 값이 여러 개면 가장 작은 값을 쓴다(np.argmax는 첫 번째를 고름)."""
    is_near_full = labels == NEAR_FULL
    accs = np.array([((ratios >= t) == is_near_full).mean() for t in THRESHOLDS])
    best_idx = int(np.argmax(accs))
    tied = THRESHOLDS[accs == accs[best_idx]]
    return float(THRESHOLDS[best_idx]), float(accs[best_idx]), accs, tied


def build_templates(masks, labels):
    """near full을 제외한 유형마다 결함 마스크의 평균 템플릿을 만든다."""
    classes = [c for c in sorted(set(labels)) if c != NEAR_FULL]
    return {c: masks[labels == c].mean(axis=0) for c in classes}


def predict(masks, ratios, defect_counts, templates, threshold):
    """예측 규칙 적용. 상관계수를 구할 수 없는 경우(NaN, 값이 모두 같은 마스크/템플릿)는 개수를 센다."""
    template_names = list(templates)
    template_flat = [templates[c].ravel() for c in template_names]
    preds, nan_count = [], 0
    for mask, ratio, n_defect in zip(masks, ratios, defect_counts):
        if n_defect == 0:
            preds.append(NONE)
            continue
        if ratio >= threshold:
            preds.append(NEAR_FULL)
            continue
        flat = mask.ravel()
        corrs = np.array([np.corrcoef(flat, t)[0, 1] for t in template_flat])
        if np.isnan(corrs).any():
            nan_count += 1
            corrs = np.where(np.isnan(corrs), -np.inf, corrs)  # 계산 불가는 후보에서 제외
        preds.append(template_names[int(np.argmax(corrs))])
    return np.array(preds), nan_count


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    paths, labels, images = load_dataset()
    pixel_classes = classify_pixels(images)
    masks = (pixel_classes == DEFECT).astype(np.float64)
    ratios, defect_counts = defect_ratio(pixel_classes)

    idx = np.arange(len(labels))
    train_idx, test_idx = train_test_split(
        idx, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=labels
    )

    threshold, train_nf_acc, accs, tied = search_threshold(
        ratios[train_idx], labels[train_idx]
    )
    templates = build_templates(masks[train_idx], labels[train_idx])

    y_test = labels[test_idx]
    y_pred, nan_count = predict(
        masks[test_idx], ratios[test_idx], defect_counts[test_idx], templates, threshold
    )

    class_names = sorted(set(labels))
    acc = accuracy_score(y_test, y_pred)
    report_text = classification_report(
        y_test, y_pred, labels=class_names, digits=3, zero_division=0
    )
    report_dict = classification_report(
        y_test, y_pred, labels=class_names, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=class_names)

    # 테스트셋에서 near full 판별만 따로 본 정확도 (참고용)
    test_nf_acc = float(((ratios[test_idx] >= threshold) == (y_test == NEAR_FULL)).mean())

    # ---- 결과 저장 ----
    summary = {
        "n_total": int(len(labels)),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "split": {"test_size": TEST_SIZE, "random_state": RANDOM_STATE, "stratify": True,
                  "input_order": "폴더 이름 정렬 → 파일 이름 정렬"},
        "near_full_threshold_percent": threshold,
        "near_full_threshold_train_accuracy": train_nf_acc,
        "near_full_threshold_tied_values": [float(t) for t in tied],
        "near_full_detection_test_accuracy": test_nf_acc,
        "test_accuracy": float(acc),
        "test_correct": int((y_test == y_pred).sum()),
        "corrcoef_nan_cases_in_test": nan_count,
        "per_class": {c: report_dict[c] for c in class_names},
    }
    (RESULTS_DIR / "01_baseline_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / "01_baseline_report.txt").write_text(
        f"테스트 정확도: {acc:.4f} ({summary['test_correct']}/{len(test_idx)})\n"
        f"near full 임계값: {threshold}% (학습셋 판별 정확도 {train_nf_acc:.4f}, "
        f"동점 값 {len(tied)}개: {tied.min()}~{tied.max()})\n\n"
        f"{report_text}\n"
        f"혼동행렬 (행=정답, 열=예측, 순서={class_names})\n{cm}\n",
        encoding="utf-8",
    )

    # 임계값 탐색 곡선 (CSV)
    with open(RESULTS_DIR / "01_baseline_threshold_search.csv", "w", encoding="utf-8") as f:
        f.write("threshold_percent,train_near_full_accuracy\n")
        for t, a in zip(THRESHOLDS, accs):
            f.write(f"{t},{a:.6f}\n")

    # 테스트셋 장별 예측 (CSV)
    with open(RESULTS_DIR / "01_baseline_test_predictions.csv", "w", encoding="utf-8") as f:
        f.write("file,true,pred,defect_ratio_percent\n")
        for i, p in zip(test_idx, y_pred):
            f.write(f"{paths[i].parent.name}/{paths[i].name},{labels[i]},{p},{ratios[i]:.3f}\n")

    # 혼동행렬 그림
    fig, ax = plt.subplots(figsize=(9, 8))
    ConfusionMatrixDisplay(cm, display_labels=class_names).plot(
        ax=ax, cmap="Blues", colorbar=False, xticks_rotation=45
    )
    ax.set_title(f"Baseline (rule + template) - test accuracy {acc:.1%} (n={len(test_idx)})")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "01_baseline_confusion_matrix.png", dpi=150)
    plt.close(fig)

    print(f"학습 {len(train_idx)}장 / 테스트 {len(test_idx)}장")
    print(f"near full 임계값: {threshold}% (학습셋 판별 정확도 {train_nf_acc:.4f}, 동점 {len(tied)}개)")
    print(f"테스트 정확도: {acc:.4f} ({summary['test_correct']}/{len(test_idx)})")
    print(f"상관계수 계산 불가(NaN) 건수: {nan_count}")
    print(report_text)
    print(cm)


if __name__ == "__main__":
    main()
