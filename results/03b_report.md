# 03b: 8월 모양 특징 코드로 B 다시 돌리기

> 작성: 2026-11-07. 스크립트: `scripts/03b_randomforest_aug.py`. 숫자는 모두 이 스크립트를 실행한 출력이에요.
> `03_randomforest.py`와 그 결과 파일은 바꾸지 않았어요. 분할·템플릿·상관계수·RandomForest 설정은 03과 같아요.
> 모양 특징 함수는 8월 대화 기록의 원문을 그대로 붙여 넣었어요. 신장도는 8월처럼 특징을 만들 때 min(신장도, 50)으로 잘랐어요.

## 1. 결론

**8월 코드와 8월 특징 순서로 돌리면 B는 79.3%(215/271)로, 8월 결과와 같아요.**

03(77.5%)과의 차이 5장을 나눠 보면 이래요.

| 조합 | 예외 처리 | 특징 순서 | 정확도 | 03 대비 |
|---|---|---|---:|---:|
| B_03 (03 결과 재현) | 03 | 03 | 77.5% (210/271) | – |
| edge_only | **8월** | 03 | 77.9% (211/271) | +1장 |
| order_only | 03 | **8월** | 79.7% (216/271) | +6장 |
| B_aug (본 결과) | **8월** | **8월** | **79.3% (215/271)** | +5장 |

- **차이는 대부분 특징 순서에서 와요.** 순서만 바꾸면 +6장, 예외 처리만 바꾸면 +1장이에요. 둘 다 바꾸면 +5장이라 단순 합(+7)도 아니에요.
- 특징 순서는 정보를 바꾸지 않아요. 같은 12개 숫자를 열 순서만 바꿔 넣은 거예요. 그런데도 결과가 바뀌는 건, RandomForest가 나무마다 특징을 무작위로 골라 쓰기 때문이에요. random_state=42로 고정해도 "몇 번째 열을 고를지"가 고정될 뿐이라, 열 순서가 바뀌면 사실상 다른 무작위 결과가 나와요.
- 그래서 이 데이터에서는 **열 순서만 바꿔도 정확도가 몇 장(최대 6장, 2.2%p) 움직여요.** A(77.5%)와 B(79.3%)의 차이도 5장이라, 이 흔들림과 크기가 비슷해요. "모양 특징을 넣어서 1.8%p 올랐다"고 말하려면 random_state를 여러 개로 돌려 평균을 봐야 확실해요(아직 안 했어요).

## 2. 예외 처리 차이 (03 vs 8월)

모양 특징 3개 중 **신장도만** 달라요. 덩어리 개수와 최대 덩어리 비율은 902장 모두 같아요.

| 경우 | 03 | 8월 |
|---|---|---|
| 결함 0개 | 1.0 | 0.0 |
| 가장 큰 덩어리 1픽셀 | 1.0 | 0.0 |
| 가장 큰 덩어리 2픽셀 | 50 (한 줄로 봄) | 0.0 (3픽셀 미만) |
| 3픽셀 이상 한 줄 | 50 | 50 (고유값을 1e-6으로 자른 뒤 50에서 자름) |

- 신장도가 다른 이미지: 학습 57장, 테스트 33장
- 조합끼리 테스트 예측이 다른 장수: B_03과 edge_only 4장, B_03과 order_only 8장, B_03과 B_aug 9장

## 3. 유형별 F1

| 항목 | 03 예외 + 03 순서 | 8월 예외 + 03 순서 | 03 예외 + 8월 순서 | 8월 예외 + 8월 순서 |
|---|---:|---:|---:|---:|
| 정확도 | 77.5% (210/271) | 77.9% (211/271) | 79.7% (216/271) | 79.3% (215/271) |
| F1 Center | 0.717 | 0.731 | 0.778 | 0.755 |
| F1 Donut | 0.857 | 0.857 | 0.839 | 0.871 |
| F1 Edge Local | 0.821 | 0.842 | 0.862 | 0.862 |
| F1 Edge Ring | 0.889 | 0.903 | 0.903 | 0.903 |
| F1 Local | 0.562 | 0.562 | 0.571 | 0.594 |
| F1 Scratch | 0.576 | 0.559 | 0.594 | 0.585 |
| F1 near full | 0.949 | 0.949 | 0.949 | 0.949 |
| F1 none | 0.857 | 0.852 | 0.897 | 0.857 |
| F1 random | 0.774 | 0.794 | 0.806 | 0.794 |
| macro F1 | 0.778 | 0.783 | 0.800 | 0.797 |

## 4. B_aug 특징 중요도

`results/03b_feature_importance_B_aug.csv`. 순서는 03의 B와 거의 같아요. 모양 특징 3개는 여전히 10~12위예요.

| 순위 | 특징 | 중요도 |
|---:|---|---:|
| 1 | 결함 면적 비율 | 0.146 |
| 2 | 상관계수 Edge Ring | 0.136 |
| 3 | 상관계수 none | 0.111 |
| 4 | 상관계수 Local | 0.098 |
| 5 | 상관계수 Center | 0.097 |
| 6 | 상관계수 random | 0.090 |
| 7 | 상관계수 Donut | 0.085 |
| 8 | 상관계수 Edge Local | 0.078 |
| 9 | 상관계수 Scratch | 0.069 |
| 10 | 결함 덩어리 개수 | 0.037 |
| 11 | 가장 큰 덩어리 비율 | 0.029 |
| 12 | 가장 큰 덩어리 신장도 | 0.023 |

## 5. 02 보고서의 12장

`results/03b_missed12_predictions.csv`

| 파일 | 정답 | B_03 | edge_only | order_only | B_aug |
|---|---|---|---|---|---|
| Center/773253.jpg | Center | Local | Local | Local | Local |
| Scratch/809507.jpg | Scratch | Local | Local | Local | Local |
| Center/776169.jpg | Center | Local | Local | Local | Local |
| Center/761994.jpg | Center | **Center ✓** | **Center ✓** | **Center ✓** | **Center ✓** |
| Edge Ring/766504.jpg | Edge Ring | none | Scratch | none | none |
| Scratch/801807.jpg | Scratch | none | none | none | none |
| Edge Local/810215.jpg | Edge Local | Edge Ring | **Edge Local ✓** | Edge Ring | Edge Ring |
| Local/792182.jpg | Local | Scratch | Scratch | Scratch | Scratch |
| Donut/758427.jpg | Donut | Scratch | Scratch | Scratch | Scratch |
| Edge Local/810592.jpg | Edge Local | **Edge Local ✓** | **Edge Local ✓** | **Edge Local ✓** | **Edge Local ✓** |
| Local/791996.jpg | Local | random | random | random | random |
| Scratch/807903.jpg | Scratch | random | random | random | random |

- B_aug도 12장 중 2장만 맞혀요. 03의 B와 12장 예측이 모두 같아요. 79.3%로 오른 5장은 이 12장 밖에서 나왔어요.

## 6. 저장한 파일

| 파일 | 내용 |
|---|---|
| `scripts/03b_randomforest_aug.py` | 8월 모양 특징 원문 + 4가지 조합 실행 (B_03이 03 결과와 같은지 먼저 확인) |
| `results/03b_comparison.csv`, `03b_comparison.md` | 4가지 조합의 정확도와 유형별 F1 |
| `results/03b_feature_importance_B_aug.csv` | B_aug 특징 중요도 |
| `results/03b_missed12_predictions.csv` | 12장 예측(4가지) + 8월식 모양 특징값 |
| `results/03b_test_predictions.csv` | 테스트 271장 전체 예측(4가지) |
| `results/03b_report.txt` | 상세 분류 리포트와 혼동행렬 |
| `results/03b_metrics.json` | 전체 지표, 특징값이 다른 장수, 조합 간 예측 차이 |
