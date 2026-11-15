# 웨이퍼 불량맵 자동 분류 (WM-811K 902장)

공개 데이터 WM-811K 중 902장으로 웨이퍼 불량맵 9개 유형을 분류하고, 정확도가 믿을 만한지 다시 검증한 개인 프로젝트예요. 분류 결과를 현장에 적용하는 형태(알림 카드, lot 몰림 탐지)도 시범으로 만들었어요.

- 대표 정확도: **77.5% ± 2.0** (lot 단위 분할, 5묶음 × 무작위 설정 10종 = 50회 평균)
- 모든 숫자는 `scripts/`의 스크립트를 실행해 `results/`, `results2/`에 저장된 값이에요.

## 데이터

- WM-811K 원본: 웨이퍼 811,457장. 칩(die)마다 테스트한 합격/불합격을 웨이퍼 위치에 표시한 맵이에요.
- 이번에 쓴 것: Kaggle에 공개된 서브셋 902장. 9개 유형별로 약 100장씩 골라 놓은 자료예요.
  - 이미지는 **32×32 픽셀**이에요. 원본 맵은 칩 1개 = 1칸인 격자이고, 크기가 제품마다 달라요(예: 세로 39 × 가로 37칸, 칩 1,109개). 이걸 32×32로 늘리거나 줄인 것이라 픽셀 1개가 칩 1개와 같지 않아요.
- 902장을 모두 원본과 대조해서 lot 번호와 웨이퍼 번호를 확보했어요(`data/wafer_lot_map.csv`, 불일치 0건, lot 520개).
- 출처, 라이선스, 맵의 의미를 확인한 과정은 [`DATA_SOURCE.md`](DATA_SOURCE.md)에 정리했어요.

데이터 파일은 용량과 재배포 조건 때문에 저장소에 넣지 않았어요. 실행하려면 아래 위치에 직접 받아 두세요.

| 위치 | 내용 | 받는 곳 |
|---|---|---|
| `WM811k Dataset/<유형>/*.jpg` | 902장 이미지 | Kaggle "WM811k Silicon Wafer Map Dataset Image" (CC BY-SA 4.0) |
| `data/raw/MIR-WM811K.zip` | 원본 WM-811K (00, 05v2, 07, 08, 09에서 사용) | 인터넷 아카이브에 보존된 MIR Lab 파일 (주소는 `DATA_SOURCE.md` 4-1절) |

## 슬라이드 내용과 파일 연결

| 슬라이드 | 내용 | 스크립트 | 결과 파일 |
|---|---|---|---|
| 2. 데이터 | 902장과 원본 대조, lot 정보 | `00_source_check.py` | `results/00_source_check_summary.txt`, `data/wafer_lot_map.csv` |
| 3. 분류 방법 ① | 규칙 기반 66.1% (7:3 분할 1회) | `01_baseline.py` | `results/01_baseline_report.txt` |
| 3. 분류 방법 ② | RandomForest 77.5% (7:3 분할 1회) | `03_randomforest.py` | `results/03_randomforest_report.md` |
| 3. 분류 방법 ③ | 모양 특징 추가 79.3% (7:3 분할 1회) | `03b_randomforest_aug.py` | `results/03b_report.md` |
| 4. 검증 결과 | lot 단위 50회: 65.7 / 75.9 / **77.5%** | `04_lot_split.py` | `results/04_lot_split_summary.md` |
| 4. 검증 결과 | 7:3 분할 테스트 271장 중 131장이 학습과 같은 lot | `04_lot_split.py` | `results/04_lot_split_7030_overlap.csv` |
| 5. 유의점 | 웨이퍼 윤곽만으로 유형 59.0%, 칩 개수 그룹 95.3% | `08_product_check.py` | `results2/08_report.md`, `results2/08_interpretation.md` |
| 6-1. 알림 카드 | 확신도 0.5 이상 131장 정확도 93.9%, 나머지 54장은 사람 확인 | `05_alert.py`, `05v2_alert_cards_origmap.py` | `results/05_alert_summary.md`, `results/05_alert_metrics.json` |
| 6-2. lot 몰림 탐지 | 몰린 lot 9개 중 7개 검출 (K=3) | `06_lot_cluster.py` | `results/06_lot_cluster_report.md` |
| 6-2. 원본 lot 확인 | 902장 밖의 더 큰 몰림 (예: lot45626 Center 19장) | `07_full_lot_check.py` | `results/07_full_lot_report.md` |
| 그림 | 유형별 예시 맵, 평균 위치, 알림 카드 | `09_portfolio_maps.py` | `results/portfolio_maps/` |

- 02(`02_missed12_investigate.py`)는 규칙 기반 분류가 불량을 none으로 놓친 12장의 원인을 조사한 기록이에요.
- 6-1, 6-2의 시범 적용은 50회 검증과 같은 방식으로 나눈 테스트 묶음 1개(fold 0, 185장, lot 98개)에 모델을 **한 번** 학습시켜 적용한 결과예요(RandomForest random_state=42). 50회 평균이 아니에요.
- lot 몰림 탐지는 판정을 모두 마친 뒤 lot별로 센 사후 집계예요. 실시간 경보는 아니에요.

## 실행

WSL Ubuntu, Python 3.12에서 실행했어요.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/01_baseline.py      # 이후 번호 순서대로
```

- 분할 조건은 고정이에요: 7:3 분할은 `test_size=0.3, random_state=42, stratify`, lot 분할은 `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`.
- 05, 06, 07의 한글 그림은 Windows의 맑은 고딕(`/mnt/c/Windows/Fonts/malgun.ttf`)을 WSL에서 읽어요. 다른 환경에서는 스크립트 안의 글꼴 경로를 바꿔야 해요.
- `results/`는 01~07과 09, `results2/`는 05v2와 08의 결과예요.

## 한계

- 유형별로 약 100장씩 고른 자료라 정상 웨이퍼가 대부분인 실제 생산과 구성이 달라요. 현장 정확도는 따로 확인해야 해요.
- 웨이퍼 윤곽만으로 59.0%를 맞혀요. 77.5% 중 일부는 불량이 아니라 칩 개수(제품)를 알아본 결과일 수 있고, 그 비중은 나누지 못했어요.
- 공정 조건, 설비, 이력 정보가 없어서 불량 원인이나 조치는 분석할 수 없어요.

## 수행 방식

분석 방향 설정, 결과 검토, 후속 분석 결정은 작성자가 했고, 코드 작성과 방법 제안은 AI 코딩 도구(Claude Code)가 했어요. `CLAUDE.md`는 AI에게 준 프로젝트 규칙이에요(실제 실행 결과만 보고, 분할 조건 고정 등).

## 인용

- [1] Ming-Ju Wu, Jyh-Shing Roger Jang, and Jui-Long Chen, "Wafer Map Failure Pattern Recognition and Similarity Ranking for Large-Scale Data Sets," *IEEE Transactions on Semiconductor Manufacturing*, vol. 28, no. 1, pp. 1-12, Feb. 2015, doi: 10.1109/TSM.2014.2364237.
- [2] MIR-WM811K: Dataset for wafer map failure pattern recognition, 2015, http://mirlab.org/dataset/public/
- Kaggle 서브셋: "WM811k Silicon Wafer Map Dataset Image" (Muhammad Junayed), CC BY-SA 4.0
