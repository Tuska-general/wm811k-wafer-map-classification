# 06 누적 원인 추리기: 새 웨이퍼의 lot별 패턴 몰림

비유: 한 학생만 기침하면 감기지만, 같은 반 세 명이 같은 증상이면 교실(공정 묶음)을 의심한다. 여기서 반 = lot, 증상 = 예측 불량 유형이다.

## 입력과 규칙

- 새 웨이퍼: 05의 lot fold 0, 185장 / lot 98개 (예측 정확도 143/185 = 77.3%, 사람 확인 필요 54장)
- lot 크기(새 웨이퍼 안에서 장수: lot 수): 1장: 70개, 2장: 13개, 3장: 5개, 4장: 5개, 5장: 2개, 11장: 1개, 15장: 1개, 18장: 1개
- 05 결과표의 lotName·waferIndex·정답이 data/wafer_lot_map.csv와 185장 모두 같음을 확인했다. 또 새 웨이퍼 lot들의 902장 속 웨이퍼는 모두 fold 0에 있다(lot 단위 분할이라서). 즉 lot별 장수는 902장 기준으로는 빠짐없이 센 것이다.
- 판정 규칙(결과 보기 전에 정함): 한 lot 안에서 none이 아닌 같은 유형이 **3장 이상**이면 반복 패턴 lot. 사람 확인 필요 웨이퍼도 예측 유형 그대로 센다(따로 표시만 함).

## 핵심 결과 (K = 3)

- 실제 기준 반복 패턴 lot 9개 중 예측으로 찾은 것 7개, 놓친 것 2개.
- 예측이 반복 패턴 lot으로 표시한 8개 중 실제로도 반복인 것 7개, 잘못 표시한 것 1개.
- 유형까지 맞춘 (lot,유형)은 실제 9쌍 중 7쌍, 예측 9쌍 중 7쌍.
- 놓치거나 잘못 표시한 lot에서 예측이 틀린 웨이퍼 (waferIndex: 예측 → 실제, ?=사람 확인 필요):
  - lot42358 (놓침): 22?: random → Donut
  - lot45644 (잘못 표시): 4?: Edge Ring → random
  - lot46104 (lot은 맞음, 유형 하나 더 표시): 5: Center → random; 8?: Center → random; 9?: Center → random; 13?: Center → random; 17?: Center → random; 19: Center → random; 21: Center → random; 23?: Center → random
  - lot47500 (놓침): 19: Edge Ring → Edge Local

## 1. K = 2 / 3 / 4 에 따라 달라지는 것

| K | 예측 기준 반복 lot | 실제 기준 반복 lot | 맞게 찾은 lot | 놓친 lot | 잘못 표시한 lot | (lot,유형) 맞춤 / 실제 / 예측 |
|---|---|---|---|---|---|---|
| 2 | 17 | 19 | 17 | 2 | 0 | 17 / 20 / 19 |
| 3 (기준) | 8 | 9 | 7 | 2 | 1 | 7 / 9 / 9 |
| 4 | 3 | 3 | 3 | 0 | 0 | 3 / 3 / 4 |

- 맞게 찾은 lot = 예측으로도 실제로도 반복 패턴 lot. 놓친 lot = 실제로는 반복인데 예측으로는 못 찾음. 잘못 표시한 lot = 예측으로는 반복인데 실제로는 아님.
- (lot,유형) 맞춤 = lot과 반복 유형까지 같은 경우. lot은 맞혀도 유형이 다르면 여기서는 틀린 것으로 센다.

**K = 2**
- 맞게 찾은 lot: lot42277, lot42358, lot44184, lot44187, lot45612, lot45624, lot45626, lot45644, lot45647, lot46104, lot46372, lot47485, lot47488, lot47500, lot47503, lot47510, lot47511
- 놓친 lot: lot45893, lot47505
- 잘못 표시한 lot: 없음
- 놓친 (lot,유형): lot45647:Edge Ring, lot45893:Donut, lot47505:Edge Local
- 잘못 표시한 (lot,유형): lot45647:Center, lot46104:Center

**K = 3**
- 맞게 찾은 lot: lot44187, lot45612, lot45626, lot46104, lot47485, lot47510, lot47511
- 놓친 lot: lot42358, lot47500
- 잘못 표시한 lot: lot45644
- 놓친 (lot,유형): lot42358:Donut, lot47500:Edge Local
- 잘못 표시한 (lot,유형): lot45644:Edge Ring, lot46104:Center

**K = 4**
- 맞게 찾은 lot: lot45612, lot46104, lot47511
- 놓친 lot: 없음
- 잘못 표시한 lot: 없음
- 놓친 (lot,유형): 없음
- 잘못 표시한 (lot,유형): lot46104:Center

## 2. 반복 패턴 lot 상세 (K = 3, 예측 또는 실제 기준)

waferIndex 순서 그림: `06_lot_cluster_seq_<lot>.png`, 모아 보기 `06_lot_cluster_seq_all.png`.

| lot | 새 웨이퍼 장수 | 판정(예측 / 실제) | 반복 유형의 waferIndex (예측 판정 기준, 없으면 실제) | 가장 긴 연속 구간 | 그 구간 안 빠진 번호 | 사람 확인 필요 | 예측 맞음 |
|---|---|---|---|---|---|---|---|
| lot46104 | 18 | Center, random / random | Center(예측): 5 8 9 13 17 19 21 23; random(예측): 2 4 6 12 14 18 20 22 24 25 | Center: 2장; random: 2장 | Center: 5개; random: 6개 | 8 | 10/18 |
| lot45612 | 5 | Edge Ring / Edge Ring | Edge Ring(예측): 6 7 8 10 17 | Edge Ring: 3장 | Edge Ring: 7개 | 0 | 5/5 |
| lot45626 | 5 | Edge Ring / Edge Ring | Edge Ring(예측): 13 14 18 | Edge Ring: 2장 | Edge Ring: 2개 | 1 | 5/5 |
| lot45644 | 4 | Edge Ring / - | Edge Ring(예측): 4 18 25 | Edge Ring: 1장 | Edge Ring: 19개 | 1 | 3/4 |
| lot47485 | 4 | Edge Local / Edge Local | Edge Local(예측): 1 8 20 | Edge Local: 1장 | Edge Local: 17개 | 0 | 4/4 |
| lot47500 | 4 | - / Edge Local | Edge Local(실제): 11 19 20 | Edge Local: 2장 | Edge Local: 7개 | 2 | 3/4 |
| lot47511 | 4 | Edge Local / Edge Local | Edge Local(예측): 4 13 14 17 | Edge Local: 2장 | Edge Local: 10개 | 0 | 4/4 |
| lot42358 | 3 | - / Donut | Donut(실제): 22 23 25 | Donut: 2장 | Donut: 1개 | 1 | 2/3 |
| lot44187 | 3 | near full / near full | near full(예측): 5 11 25 | near full: 1장 | near full: 18개 | 0 | 3/3 |
| lot47510 | 3 | Edge Local / Edge Local | Edge Local(예측): 1 9 24 | Edge Local: 1장 | Edge Local: 21개 | 0 | 3/3 |

- 가장 긴 연속 구간 = 반복 유형 웨이퍼의 waferIndex가 1씩 이어지는 가장 긴 길이. 빠진 번호 = 그 유형 웨이퍼의 처음~끝 번호 사이에서 902장에 아예 없는 번호 수 (원본에서는 같은 유형이었을 수도, 아니었을 수도 있어 알 수 없다).

## 3. 해석할 때 주의할 점 (한계)

1. **이 902장은 원본 lot의 일부 웨이퍼만 들어 있다.** WM-811K의 lot은 웨이퍼 25장(waferIndex 1~25)인데, 새 웨이퍼 lot 98개 중 70개는 1장뿐이다. 902장은 유형별로 약 100장씩 고른 부분집합이라, 어떤 lot에 같은 유형이 많이 보이는 것은 실제 공정의 몰림이 아니라 **뽑는 방식** 때문일 수 있다 (예: 00에서 random 100장 중 18장이 lot46104 한 곳, none 100장이 lot 6개에서 나옴). 그래서 여기서 나온 '반복 패턴 lot'은 원인 확정이 아니라 **다시 볼 후보** 목록이다. 반대로 902장에 없는 웨이퍼에 같은 패턴이 더 있었을 수도 있어, 놓친 몰림도 있을 수 있다.
2. **설비·layer·날짜 정보가 없다.** 데이터에는 lotName과 waferIndex뿐이라, 몰림이 보여도 어느 장비·공정 단계·시점 문제인지 이어 볼 수 없다. lot 사이의 시간 순서도 알 수 없다(lot 번호가 시간 순이라는 보장 없음).
3. **waferIndex 연속이 곧 공정 순서라는 보장이 없다.** 원본에는 waferIndex의 뜻(슬롯 번호인지 처리 순서인지)이 적혀 있지 않다. 그림의 '연속'은 번호가 이어진다는 뜻일 뿐이다.
4. **표본이 작다.** 반복 패턴 lot이 몇 개뿐이라 '얼마나 맞게 찾는가'는 몇 개 lot의 결과이고, 다른 fold나 다른 표본에서 같은 비율이 나온다는 근거는 없다.
5. **기준 K는 임의로 정한 값이다.** K를 바꾸면 결과가 달라지는 정도는 1번 표에 그대로 적었다. K=2는 우연히 겹친 2장도 잡고, K=4는 작은 lot의 몰림을 놓친다.
6. 예측 기반 판정은 05 B 모델(정확도 77.3%) 예측을 그대로 쓴다. 사람 확인 필요 웨이퍼를 빼거나 다르게 세는 방식은 쓰지 않았다(규칙을 바꾸지 않음).

## 출력 파일

- `results/06_lot_summary.csv`: lot별 예측(pred_*)·실제(true_*) 유형 장수, 사람 확인 필요 장수와 번호, K=2/3/4 판정(repeat_pred_k*, repeat_true_k*), n_in_902(902장 속 그 lot의 장수)
- `results/06_lot_cluster_heatmap.png`: lot × 유형 히트맵 (예측 / 실제)
- `results/06_lot_cluster_seq_*.png`: 반복 패턴 lot별 waferIndex 순서 그림
