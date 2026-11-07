# 03 RandomForest: baseline / A / B 비교 (8월 방식 재현)

> 작성: 2026-11-07. 스크립트: `scripts/03_randomforest.py`. 이 문서의 숫자는 모두 이 스크립트를 실행한 출력이에요.
> 분할은 01과 같아요(test_size=0.3, random_state=42, stratify, 학습 631장 / 테스트 271장). 스크립트가 baseline 예측을 다시 계산하고, `01_baseline_test_predictions.csv`와 271장 모두 같은지 먼저 확인해요.

## 1. 결과 요약

| 항목 | baseline | A | B |
|---|---:|---:|---:|
| 정확도 | 66.1% (179/271) | 77.5% (210/271) | **77.5% (210/271)** |
| 8월 보고 정확도 | 66.1% | 77.5% | 79.3% |
| F1 Center | 0.688 | 0.741 | 0.717 |
| F1 Donut | 0.812 | 0.885 | 0.857 |
| F1 Edge Local | 0.529 | 0.793 | 0.821 |
| F1 Edge Ring | 0.700 | 0.903 | 0.889 |
| F1 Local | 0.229 | 0.597 | 0.562 |
| F1 Scratch | 0.364 | 0.554 | 0.576 |
| F1 near full | 0.949 | 0.949 | 0.949 |
| F1 none | 0.800 | 0.857 | 0.857 |
| F1 random | 0.586 | 0.733 | 0.774 |
| macro F1 | 0.629 | 0.779 | 0.778 |

- baseline과 A는 8월 숫자와 같아요.
- **B는 8월(79.3%)과 달라요.** 이번 실행은 77.5%(210/271)로 A와 같아요. 8월의 79.3%는 271장 중 215장에 해당해서, 5장 차이예요. 숫자를 맞추려고 방법을 바꾸지 않았어요.
- 모양 특징 3개를 넣으면 Edge Local·Scratch·random의 F1은 올랐지만 Center·Donut·Edge Ring·Local은 내려가서, 전체 정확도는 그대로예요.

## 2. B가 8월과 다른 이유 후보 (확인 안 됨)

모양 특징을 계산할 때 사용자가 정하지 않은 예외가 생각보다 자주 생겨요. 아래처럼 정했는데, 8월 코드가 다르게 처리했다면 결과가 달라질 수 있어요.

| 경우 | 이번 처리 | 학습셋 | 테스트셋 |
|---|---|---:|---:|
| 결함 픽셀 0개 | 덩어리 0개, 비율 0, 신장도 1.0 | 6장 | 1장 |
| 가장 큰 덩어리가 1픽셀 (공분산 계산 불가) | 신장도 1.0 | 17장 | 19장 |
| 가장 큰 덩어리가 한 줄 (최소 고유값 0) | 신장도 50 (상한) | 76장 | 26장 |

- 테스트셋 271장 중 46장(17%)이 1픽셀 또는 한 줄 경우예요. 이 처리 방식이 8월과 다르면 B 결과가 달라질 수 있어요. 다만 이게 5장 차이의 원인인지는 **확인하지 않았어요.**
- 그 밖의 후보: 신장도에서 좌표 공분산을 계산한 방식, sklearn/scipy 버전(지금 sklearn 1.9.1, scipy 1.18.1), 특징 순서. 8월 코드가 있으면 바로 대조할 수 있어요.
- 참고(8월 방식 그대로): 학습 이미지의 상관계수 특징은 그 이미지 자신이 평균에 들어간 템플릿으로 계산돼요. 그래서 학습셋 특징이 테스트셋보다 조금 더 "잘 맞는" 쪽으로 나와요. 테스트 정보가 학습에 들어가는 누수는 아니에요.
- 상관계수 계산 불가(마스크 표준편차 0)는 결함 픽셀 0개인 이미지뿐이었고(학습 6장, 테스트 1장), 8월처럼 -1.0으로 넣었어요.

## 3. B의 특징 중요도

RandomForest의 불순도 감소 기준(`feature_importances_`)이에요. `results/03_feature_importance_B.csv`

| 순위 | 특징 | 중요도 |
|---:|---|---:|
| 1 | 결함 면적 비율 | 0.141 |
| 2 | 상관계수 Edge Ring | 0.137 |
| 3 | 상관계수 none | 0.113 |
| 4 | 상관계수 Center | 0.108 |
| 5 | 상관계수 Local | 0.094 |
| 6 | 상관계수 random | 0.089 |
| 7 | 상관계수 Donut | 0.088 |
| 8 | 상관계수 Edge Local | 0.076 |
| 9 | 상관계수 Scratch | 0.067 |
| 10 | 결함 덩어리 개수 | 0.040 |
| 11 | 가장 큰 덩어리 비율 | 0.027 |
| 12 | 가장 큰 덩어리 신장도 | 0.022 |

새로 넣은 모양 특징 3개는 중요도 10~12위예요. 정확도가 오르지 않은 결과와도 맞아요.

## 4. 02 보고서의 12장 (baseline에서 불량인데 none으로 예측)

`results/03_missed12_predictions.csv`. 순서는 02 보고서와 같아요(결함 픽셀 적은 순).

| 파일 | 정답 | 결함 픽셀 | baseline | A | B |
|---|---|---:|---|---|---|
| Center/773253.jpg | Center | 0 | none | Local | Local |
| Scratch/809507.jpg | Scratch | 2 | none | Local | Local |
| Center/776169.jpg | Center | 6 | none | Local | Local |
| Center/761994.jpg | Center | 13 | none | **Center ✓** | **Center ✓** |
| Edge Ring/766504.jpg | Edge Ring | 19 | none | none | none |
| Scratch/801807.jpg | Scratch | 19 | none | none | none |
| Edge Local/810215.jpg | Edge Local | 30 | none | Edge Ring | Edge Ring |
| Local/792182.jpg | Local | 31 | none | Scratch | Scratch |
| Donut/758427.jpg | Donut | 34 | none | Scratch | Scratch |
| Edge Local/810592.jpg | Edge Local | 70 | none | **Edge Local ✓** | **Edge Local ✓** |
| Local/791996.jpg | Local | 77 | none | random | random |
| Scratch/807903.jpg | Scratch | 86 | none | random | random |

- A와 B 모두 12장 중 **2장만 맞혔어요**(Center 761994, Edge Local 810592). A와 B의 예측은 12장 모두 같아요.
- 8장은 none에서 벗어났지만 다른 틀린 유형으로 갔어요. 2장(Edge Ring 766504, Scratch 801807)은 그대로 none이에요.
- 02 보고서 5절 포인트와 대조:
  - 결함 0개인 Center 773253(상관계수 모두 -1.0) → Local로 예측돼요.
  - 근소한 차이로 none이 된 4장 중 1장(810592)만 맞혔어요. 766504는 그대로 none, 810215는 Edge Ring, 791996은 random이에요.
  - 실제 유형 상관이 낮던 2장(809507, 792182)은 예상대로 못 맞혔어요.
  - none 상관이 크게 앞선 2장 중 801807은 그대로 none이고, 758427은 Scratch로 갔어요.

## 5. 저장한 파일

| 파일 | 내용 |
|---|---|
| `scripts/03_randomforest.py` | 실험 스크립트 (01 함수를 불러 쓰고 01 결과와 일치 확인) |
| `results/03_comparison.csv`, `03_comparison.md` | baseline/A/B 정확도와 유형별 F1 표 |
| `results/03_feature_importance_B.csv` | B의 특징 중요도 |
| `results/03_missed12_predictions.csv` | 12장의 예측과 모양 특징값 |
| `results/03_randomforest_report.txt` | 세 모델의 상세 분류 리포트와 혼동행렬 |
| `results/03_randomforest_metrics.json` | 전체 지표, 예외 처리 건수, 설정값 |
