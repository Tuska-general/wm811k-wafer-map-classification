# 07 원본 lot 전체 확인: 06 몰림 lot 10개

비유: 06은 출석부에 이름이 있던 학생만 보고 "같은 증상이 많다"고 했다. 07은 반 전체 명단(원본 lot)을 꺼내 나머지 학생의 진단 기록(원본 라벨)까지 본다. 진단 기록이 없는 학생(라벨 없음)은 추측하지 않는다.

## 방법

- 원본 `WM811K.pkl`(811,457행)을 00과 같은 방식으로 읽어, 대상 lot의 행을 모두 뽑았다.
- 대상 = 06에서 K=3 판정이 예측 또는 실제로 하나라도 있는 lot 10개 (06 순서 그림과 같은 lot).
- failureType이 비어 있으면 '라벨 없음'. 라벨 없는 웨이퍼에는 모델을 적용하지 않았다.
- 902장에 있던 웨이퍼는 원본 행 번호로 `data/wafer_lot_map.csv`와 맞췄고, lot·번호·유형이 모두 같음을 확인했다.
- 902장 안 웨이퍼의 라벨도 원본 라벨이라, 원본 전체의 같은 유형 장수는 902장 안 장수보다 줄 수 없다. 그래서 "유지되는가"는 장수보다 **lot 전체(라벨 있는 웨이퍼)에서 그 유형이 차지하는 비율**과 **902장 밖에서 같은 유형이 더 나왔는가**로 본다.

## 핵심 결과 (숫자는 아래 표에서 계산)

- 06 판정 (lot,유형) 11개 중 9개는 그 유형 웨이퍼가 902장 안에 이미 전부 있었다 (902장 밖에서 같은 유형 0장). 더 나온 것은 2개: lot45644 Edge Ring +1, lot46104 Center +1.
- 라벨 있는 웨이퍼의 절반을 넘는 판정 유형은 1개 (lot46104 random 72%). 나머지는 라벨 있는 웨이퍼의 4~20%이다.
- 같은 규칙을 원본 lot 전체에 적용하면 902장 안에서는 안 보이던 반복 유형이 4개 lot에서 새로 생긴다: lot42358 Edge Local, lot45626 Center, lot45644 Center, Edge Ring, lot47510 Edge Ring.
- 원본 lot 전체에서 가장 많은 불량 유형이 06 판정 유형과 다른 lot 4개: lot42358(최다 Edge Local 7장), lot45626(최다 Center 19장), lot45644(최다 Center 4장), lot47510(최다 Edge Ring 5장).
- 대상 lot 원본 250장 중 라벨 없음은 1장이다(이 10개 lot에 한한 숫자).

## 1. lot 단위: 같은 규칙(none이 아닌 같은 유형 3장 이상)을 원본 라벨에 적용

06의 규칙을 그대로 두고, 대상만 902장 안 웨이퍼 → 원본 lot 전체로 넓혔다. 판정에 쓴 유형은 모두 원본 라벨이다.

| lot | 원본 / 902장 안 | 06 판정 (예측 / 실제) | 902장 안 원본 라벨로 판정 | 원본 lot 전체로 판정 | 전체에서 새로 생긴 유형 | 원본 전체 유형 장수 (none 아닌 것) | none | 라벨 없음 |
|---|---|---|---|---|---|---|---|---|
| lot42358 | 25 / 3 | - / Donut | Donut | Donut;Edge Local | Edge Local | Donut 3, Edge Local 7, Scratch 1 | 14 | 0 |
| lot44187 | 25 / 3 | near full / near full | near full | near full | - | near full 3 | 22 | 0 |
| lot45612 | 25 / 5 | Edge Ring / Edge Ring | Edge Ring | Edge Ring | - | Edge Local 1, Edge Ring 5 | 19 | 0 |
| lot45626 | 25 / 5 | Edge Ring / Edge Ring | Edge Ring | Center;Edge Ring | Center | Center 19, Edge Ring 3, random 1 | 2 | 0 |
| lot45644 | 25 / 4 | Edge Ring / - | - | Center;Edge Ring | Center;Edge Ring | Center 4, Edge Local 2, Edge Ring 3, Local 1, random 1 | 14 | 0 |
| lot46104 | 25 / 18 | Center;random / random | random | random | - | Center 1, random 18 | 6 | 0 |
| lot47485 | 25 / 4 | Edge Local / Edge Local | Edge Local | Edge Local | - | Center 1, Edge Local 3, Local 1, Scratch 1 | 19 | 0 |
| lot47500 | 25 / 4 | - / Edge Local | Edge Local | Edge Local | - | Edge Local 3, Scratch 1 | 20 | 1 |
| lot47510 | 25 / 3 | Edge Local / Edge Local | Edge Local | Edge Local;Edge Ring | Edge Ring | Edge Local 3, Edge Ring 5 | 17 | 0 |
| lot47511 | 25 / 4 | Edge Local / Edge Local | Edge Local | Edge Local | - | Edge Local 4, Edge Ring 1, Local 2 | 18 | 0 |

## 2. 06 판정 유형별 요약

| lot | 06 판정 유형 (판정 근거) | 원본 장수 / 902장 안 | 라벨 있음 / 없음 | 그 유형: 902장 안 → 원본 전체 | 라벨 있는 웨이퍼 중 비율 | 902장 밖 라벨 있는 웨이퍼 유형 |
|---|---|---|---|---|---|---|
| lot42358 | Donut (실제) | 25 / 3 | 25 / 0 | 3 → 3 | 12% | Edge Local:7 Scratch:1 none:14 |
| lot44187 | near full (예측+실제) | 25 / 3 | 25 / 0 | 3 → 3 | 12% | none:22 |
| lot45612 | Edge Ring (예측+실제) | 25 / 5 | 25 / 0 | 5 → 5 | 20% | Edge Local:1 none:19 |
| lot45626 | Edge Ring (예측+실제) | 25 / 5 | 25 / 0 | 3 → 3 | 12% | Center:18 none:2 |
| lot45644 | Edge Ring (예측) | 25 / 4 | 25 / 0 | 2 → 3 | 12% | Center:3 Edge Local:2 Edge Ring:1 Local:1 none:14 |
| lot46104 | Center (예측) | 25 / 18 | 25 / 0 | 0 → 1 | 4% | Center:1 none:6 |
| lot46104 | random (예측+실제) | 25 / 18 | 25 / 0 | 18 → 18 | 72% | Center:1 none:6 |
| lot47485 | Edge Local (예측+실제) | 25 / 4 | 25 / 0 | 3 → 3 | 12% | Center:1 Local:1 none:19 |
| lot47500 | Edge Local (실제) | 25 / 4 | 24 / 1 | 3 → 3 | 12% | none:20 |
| lot47510 | Edge Local (예측+실제) | 25 / 3 | 25 / 0 | 3 → 3 | 12% | Edge Ring:5 none:17 |
| lot47511 | Edge Local (예측+실제) | 25 / 4 | 25 / 0 | 4 → 4 | 16% | Edge Ring:1 Local:2 none:18 |

- 대상 lot 10개의 902장 밖 웨이퍼 197장 중 라벨 있는 것 196장, 라벨 없음 1장 (전체 라벨 없음 1장).

lot·유형별 한 줄 설명:

- **lot42358 Donut** (실제): 902장 안 3장 → 원본 전체 3장 (902장 밖에서 0장 더). 라벨 있는 25장 중 12%, 라벨 없음 0장.
- **lot44187 near full** (예측+실제): 902장 안 3장 → 원본 전체 3장 (902장 밖에서 0장 더). 라벨 있는 25장 중 12%, 라벨 없음 0장.
- **lot45612 Edge Ring** (예측+실제): 902장 안 5장 → 원본 전체 5장 (902장 밖에서 0장 더). 라벨 있는 25장 중 20%, 라벨 없음 0장.
- **lot45626 Edge Ring** (예측+실제): 902장 안 3장 → 원본 전체 3장 (902장 밖에서 0장 더). 라벨 있는 25장 중 12%, 라벨 없음 0장.
- **lot45644 Edge Ring** (예측): 902장 안 2장 → 원본 전체 3장 (902장 밖에서 1장 더). 라벨 있는 25장 중 12%, 라벨 없음 0장.
- **lot46104 Center** (예측): 902장 안 0장 → 원본 전체 1장 (902장 밖에서 1장 더). 라벨 있는 25장 중 4%, 라벨 없음 0장.
- **lot46104 random** (예측+실제): 902장 안 18장 → 원본 전체 18장 (902장 밖에서 0장 더). 라벨 있는 25장 중 72%, 라벨 없음 0장.
- **lot47485 Edge Local** (예측+실제): 902장 안 3장 → 원본 전체 3장 (902장 밖에서 0장 더). 라벨 있는 25장 중 12%, 라벨 없음 0장.
- **lot47500 Edge Local** (실제): 902장 안 3장 → 원본 전체 3장 (902장 밖에서 0장 더). 라벨 있는 24장 중 12%, 라벨 없음 1장.
- **lot47510 Edge Local** (예측+실제): 902장 안 3장 → 원본 전체 3장 (902장 밖에서 0장 더). 라벨 있는 25장 중 12%, 라벨 없음 0장.
- **lot47511 Edge Local** (예측+실제): 902장 안 4장 → 원본 전체 4장 (902장 밖에서 0장 더). 라벨 있는 25장 중 16%, 라벨 없음 0장.

## 3. lot별 원본 웨이퍼 번호별 유형

표시: `유형*` = 902장에 있던 웨이퍼, `라벨 없음` = 원본 failureType이 비어 있음, `(원본에 없음)` = 그 번호 행이 원본에 없음. 902장에 있던 웨이퍼는 06의 예측(05 B 모델)도 함께 적었다.

### lot42358  (06 판정 예측: 없음 · 실제: Donut)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | Edge Local | Edge Local | none | none | none | none | Edge Local | none | none | none | Edge Local | none | Edge Local | none | none | Edge Local | none | none | Scratch | Edge Local | none | Donut* | Donut* | none | Donut* |
| 06 예측 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | random | Donut |  | Donut |

### lot44187  (06 판정 예측: near full · 실제: near full)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | none | none | none | none | near full* | none | none | none | none | none | near full* | none | none | none | none | none | none | none | none | none | none | none | none | none | near full* |
| 06 예측 |  |  |  |  | near full |  |  |  |  |  | near full |  |  |  |  |  |  |  |  |  |  |  |  |  | near full |

### lot45612  (06 판정 예측: Edge Ring · 실제: Edge Ring)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | none | none | none | none | Edge Local | Edge Ring* | Edge Ring* | Edge Ring* | none | Edge Ring* | none | none | none | none | none | none | Edge Ring* | none | none | none | none | none | none | none | none |
| 06 예측 |  |  |  |  |  | Edge Ring | Edge Ring | Edge Ring |  | Edge Ring |  |  |  |  |  |  | Edge Ring |  |  |  |  |  |  |  |  |

### lot45626  (06 판정 예측: Edge Ring · 실제: Edge Ring)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | none | Center | Center | none | Center | Center* | Center | Center | Center | Center | Center | Center | Edge Ring* | Edge Ring* | Center | random* | Center | Edge Ring* | Center | Center | Center | Center | Center | Center | Center |
| 06 예측 |  |  |  |  |  | Center |  |  |  |  |  |  | Edge Ring | Edge Ring |  | random |  | Edge Ring |  |  |  |  |  |  |  |

### lot45644  (06 판정 예측: Edge Ring · 실제: 없음)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | Center | Center* | Center | random* | none | none | none | Edge Local | Local | none | none | none | Edge Ring | none | Center | none | none | Edge Ring* | Edge Local | none | none | none | none | none | Edge Ring* |
| 06 예측 |  | Center |  | Edge Ring |  |  |  |  |  |  |  |  |  |  |  |  |  | Edge Ring |  |  |  |  |  |  | Edge Ring |

### lot46104  (06 판정 예측: Center, random · 실제: random)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | none | random* | none | random* | random* | random* | none | random* | random* | Center | none | random* | random* | random* | none | none | random* | random* | random* | random* | random* | random* | random* | random* | random* |
| 06 예측 |  | random |  | random | Center | random |  | Center | Center |  |  | random | Center | random |  |  | Center | random | Center | random | Center | random | Center | random | random |

### lot47485  (06 판정 예측: Edge Local · 실제: Edge Local)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | Edge Local* | Center | none | none | none | none | none | Edge Local* | none | none | none | none | none | Local | none | none | none | none | none | Edge Local* | none | none | none | Scratch* | none |
| 06 예측 | Edge Local |  |  |  |  |  |  | Edge Local |  |  |  |  |  |  |  |  |  |  |  | Edge Local |  |  |  | Scratch |  |

### lot47500  (06 판정 예측: 없음 · 실제: Edge Local)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | none | none | none | none | none | none | none | none | none | none | Edge Local* | none | none | none | none | none | none | 라벨 없음 | Edge Local* | Edge Local* | Scratch* | none | none | none | none |
| 06 예측 |  |  |  |  |  |  |  |  |  |  | Edge Local |  |  |  |  |  |  |  | Edge Ring | Edge Local | Scratch |  |  |  |  |

### lot47510  (06 판정 예측: Edge Local · 실제: Edge Local)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | Edge Local* | Edge Ring | none | none | none | none | none | none | Edge Local* | none | none | Edge Ring | none | none | Edge Ring | none | none | none | none | none | Edge Ring | none | none | Edge Local* | Edge Ring |
| 06 예측 | Edge Local |  |  |  |  |  |  |  | Edge Local |  |  |  |  |  |  |  |  |  |  |  |  |  |  | Edge Local |  |

### lot47511  (06 판정 예측: Edge Local · 실제: Edge Local)

| 번호 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 원본 유형 | none | none | none | Edge Local* | Local | none | none | none | Local | none | none | none | Edge Local* | Edge Local* | none | none | Edge Local* | Edge Ring | none | none | none | none | none | none | none |
| 06 예측 |  |  |  | Edge Local |  |  |  |  |  |  |  |  | Edge Local | Edge Local |  |  | Edge Local |  |  |  |  |  |  |  |  |

## 4. 해석할 때 주의할 점

1. 라벨 없는 웨이퍼는 불량이었는지 정상이었는지 알 수 없다. 그 웨이퍼들까지 같은 유형이었다면 몰림은 더 크고, none이었다면 비율은 더 낮아진다. 오늘은 원본 라벨만 봤으므로 이 부분은 판단하지 않았다.
2. 설비·layer·날짜 정보는 원본에도 없다. lot 전체에서 몰림이 유지돼도 원인(장비·공정)을 특정할 수는 없다.
3. waferIndex가 처리 순서인지 슬롯 번호인지는 원본에 적혀 있지 않다.
4. 원본 라벨 자체가 사람이 붙인 것이라 틀린 라벨이 있을 수 있다(이 프로젝트에서 검증하지 않음).

## 출력 파일

- `results/07_full_lot_wafers.csv`: 대상 lot의 원본 웨이퍼 전체 (원본 행 번호, 원본 라벨, trainTestLabel, 902장 포함 여부, 05 예측)
- `results/07_full_lot_summary.csv`: lot × 06 판정 유형별 숫자
- `results/07_full_lot_types.csv`: lot별 원본 전체·902장 안 유형 장수와 같은 규칙의 판정
- `results/07_full_lot_check.png`: lot별 웨이퍼 번호 1~25 원본 라벨 그림
