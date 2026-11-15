# 포트폴리오 슬라이드용 그림

`scripts/09_portfolio_maps.py`로 그렸어요. 분석·판정·확률은 다시 계산하지 않았고, 기존 results 파일과 32×32 이미지는 그대로예요.

색: 웨이퍼 바깥 = 검정(#000000), 정상 칩 = 흰색(#FFFFFF), 불량 칩 = 빨강(#E63946). 격자선·글자 없음.

## 1) 유형별 예시 (원본 칩 단위 맵, 800×800)

고른 기준: 01과 같은 7:3 학습셋 안에서, 32×32 결함 마스크가 그 유형 평균(템플릿)과 상관계수가 가장 높은 웨이퍼. none은 결함 픽셀이 가장 적은 웨이퍼(같으면 파일 순서 첫 번째).
확대: 칩 1칸을 정수배(800 ÷ 긴 변, 내림)로 nearest 확대하고, 남는 가장자리는 검정으로 채웠어요.

| 그림 | 유형 | 파일 | lot | 웨이퍼 번호 | 원본 크기(행×열) | 템플릿 상관 |
|---|---|---|---|---|---|---|
| center.png | Center | Center/761305.jpg | lot45501 | 16 | 39×37 | 0.718 |
| donut.png | Donut | Donut/683018.jpg | lot42332 | 16 | 35×31 | 0.837 |
| edge_local.png | Edge Local | Edge Local/810673.jpg | lot47510 | 1 | 26×30 | 0.652 |
| edge_ring.png | Edge Ring | Edge Ring/764165.jpg | lot45617 | 19 | 33×32 | 0.848 |
| local.png | Local | Local/783000.jpg | lot46386 | 18 | 42×44 | 0.496 |
| scratch.png | Scratch | Scratch/810765.jpg | lot47513 | 18 | 26×30 | 0.409 |
| near_full.png | near full | near full/731778.jpg | lot44307 | 18 | 33×29 | 0.981 |
| none.png | none | none/757418.jpg | lot45344 | 4 | 39×37 | - |
| random.png | random | random/764598.jpg | lot45635 | 2 | 34×34 | 0.672 |

## 2) 평균 히트맵 (32×32 → 800×800)

01 분류기 템플릿과 같은 계산값: 7:3 학습셋(test_size=0.3, random_state=42, stratify)에서 유형별 결함 마스크 평균. near full은 분류기 템플릿에 없어서(01은 near full을 비율 규칙으로 판정) 같은 방식으로 따로 평균을 냈어요.
색: 0 = 흰색 → 그 그림의 최댓값 = 빨강, 연속(그림마다 자기 최댓값 기준). 웨이퍼 바깥(검정) = 그 유형 학습 이미지의 절반 넘게 배경인 칸. 32 × 25 = 800, nearest 확대.

| 그림 | 학습 장수 | 최댓값(결함 비율) |
|---|---|---|
| heatmap_center.png | 70 | 0.529 |
| heatmap_donut.png | 71 | 0.662 |
| heatmap_edge_local.png | 72 | 0.486 |
| heatmap_edge_ring.png | 71 | 0.761 |
| heatmap_local.png | 70 | 0.200 |
| heatmap_scratch.png | 70 | 0.229 |
| heatmap_near_full.png | 67 | 1.000 |
| heatmap_none.png | 70 | 0.800 |
| heatmap_random.png | 70 | 0.714 |

## 3) 알림 카드 (05v2 한국어 카드와 같은 웨이퍼·판정·문구, 맵 색만 3색)

- card_nearfull.png: near full/676749.jpg, results/05_alert_all.csv와 판정 일치 확인
- card_scratch.png: Scratch/800573.jpg, results/05_alert_all.csv와 판정 일치 확인
