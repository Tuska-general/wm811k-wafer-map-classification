# 데이터 출처 (DATA_SOURCE)

> 마지막 확인: 2026-11-06 (4차 갱신). 표의 숫자는 로컬 파일을 직접 세거나 읽어서 확인한 값이에요.
> 확인하지 못한 항목은 "확인 필요"로 남겨 뒀어요.

## 1. 데이터 이름

WM-811K 웨이퍼 맵 이미지 (9개 유형, 902장 서브셋)

- Kaggle 데이터셋 제목: *WM811k Silicon Wafer Map Dataset Image* (올린 사람: Muhammad Junayed)

## 2. 받은 곳

- 받은 페이지(토론 글): https://www.kaggle.com/datasets/muhammedjunayed/wm811k-silicon-wafer-map-dataset-image/discussion/599874
- 데이터셋 본 페이지: https://www.kaggle.com/datasets/muhammedjunayed/wm811k-silicon-wafer-map-dataset-image
- 처음 받은 파일: `C:\Users\허창빈\Downloads\archive.zip` (1,006,403바이트, 902장)
  - SHA-256: `2c21af753f39668d253fd7d2e36e0010b6058224ea443dece77f9f1c150afb6f`
  - 안쪽 폴더 이름: `WM811k_Dataset/`
- 프로젝트 폴더의 파일: `WM811k Dataset.zip` (1,037,027바이트, 902장)
  - SHA-256: `fecc626921730c9303ddc754b561667dc7b99498f87ca251a4af4420a36dcedd`
  - 안쪽 폴더 이름: `WM811k Dataset/`
- 두 zip은 해시가 다르지만, 안에 든 이미지 902장은 파일 이름과 내용(바이트)이 모두 같아요(2026-11-06 비교). 바깥 폴더 이름만 다르고, 다시 압축하는 과정에서 zip 파일 자체가 달라진 걸로 보여요.
- 압축 파일과 풀린 폴더(`WM811k Dataset/`)는 용량 때문에 git에 올리지 않아요(`.gitignore`).

## 3. 받은 날짜

2026-06-23

- 근거: 브라우저 다운로드 기록과 `C:\Users\허창빈\Downloads\archive.zip`의 수정 시각 2026-06-23 16:13(KST).
- 프로젝트 폴더의 `WM811k Dataset.zip`은 수정 시각이 2026-08-26 16:33(KST)인데, 위 파일을 나중에 다시 압축한 사본이에요(2절 참고).

## 4. 원본 데이터

- 원본: WM-811K (MIR Lab 공개 데이터, Jyh-Shing Roger Jang 교수 연구실)
  - Kaggle 데이터셋 설명에 적힌 원 출처 주소: http://mirlab.org/dataSet/public/
  - MIR Lab 공개 데이터 목록에는 `MIR-WM811K`라는 이름으로 올라와 있고, 웨이퍼 맵 분류용이며 아래 원 논문에 쓰였다고 적혀 있어요.
- 원 논문:
  - Ming-Ju Wu, Jyh-Shing R. Jang, Jui-Long Chen,
    "Wafer Map Failure Pattern Recognition and Similarity Ranking for Large-Scale Data Sets,"
    *IEEE Transactions on Semiconductor Manufacturing*, vol. 28, no. 1, pp. 1–12, 2015년 2월.
  - DOI: [10.1109/TSM.2014.2364237](https://doi.org/10.1109/TSM.2014.2364237)
  - 논문에 따르면 실제 공정에서 나온 웨이퍼 맵 811,457장으로 만든 공개 데이터셋이에요.
- 이 서브셋을 만든 쪽의 관련 논문 (Kaggle 페이지 기재):
  - Muhammad Junayed, Tanzeem Tahmeed Reza, Md. Saiful Islam, "Enhancing Defect Recognition: Convolutional Neural Networks for Silicon Wafer Map Analysis," 2024 3rd ICAEEE, pp. 1-6, 2024.
  - DOI: 10.1109/ICAEEE62219.2024.10561853
  - 올린 사람의 GitHub 저장소: https://github.com/MD-Junayed000/WM811k-Silicon-Wafer-Map-Dataset-and-Defect-Detection-Using-CNNs-with-Grad-CAM (`WM811k_Dataset.rar`, `grad.m`, MATLAB 노트북, README에 논문 PDF 링크)

## 5. 라이선스

- 받은 페이지(토론 글)에는 라이선스 표기가 없어요.
- 데이터셋 본 페이지의 License 칸에는 **CC BY-SA 4.0**으로 적혀 있어요 (2026-11-06 확인).
  - CC BY-SA 4.0은 출처를 밝히고, 이 데이터를 고쳐서 다시 배포할 때는 같은 라이선스로 배포하라는 조건이에요.
- 원본 WM-811K(MIR Lab) 자체의 이용 조건: **원본 zip 안의 `readme.txt`에 명시돼 있어요**
  - 다운로드 페이지(http://mirlab.org/dataSet/public/)는 2026-11-06 기준 404(없는 페이지)예요. 인터넷 아카이브 사본(2026-06-09 저장)에도 조건 문구는 없어요.
  - 대신 인터넷 아카이브에 남은 원본 `MIR-WM811K.zip`(2022-06-17 저장, 344,542,743바이트: http://web.archive.org/web/20220617223043/http://mirlab.org/dataSet/public/MIR-WM811K.zip)을 확인했어요. 그 안의 `MATLAB/readme.txt`와 `Python/readme.txt`에 같은 조건이 적혀 있어요.
  - 원문 요지:
    > Copyright 2015 Jyh-Shing Roger Jang. Redistribution and use of this data set, with or without modification, are permitted provided that the following conditions are met:
    > 1. Redistribution in any form must retain the above copyright notice and this list of conditions.
    > 2. Redistribution and use in any form must be accompanied by the following two citations:
    >    [1] Ming-Ju Wu, Jyh-Shing Roger Jang, and Jui-Long Chen, "Wafer Map Failure Pattern Recognition and Similarity Ranking for Large-Scale Data Sets," IEEE Transactions on Semiconductor Manufacturing, vol. 28, no. 1, pp. 1-12, Feb. 2015, doi: 10.1109/TSM.2014.2364237.
    >    [2] MIR-WM811K: Dataset for wafer map failure pattern recognition, 2015 http://mirlab.org/dataset/public/
  - 쉽게 말하면, 고쳐 쓰든 그대로 쓰든 사용과 재배포가 허용돼요. 다만 **사용할 때는 [1] 논문과 [2] 데이터셋을 둘 다 인용**해야 하고, 재배포할 때는 저작권 문구와 조건을 함께 넣어야 해요.
  - 참고: 받은 Kaggle zip(902장)에는 이 저작권 문구나 조건 파일이 들어 있지 않아요.

## 6. 구성

9개 폴더, 총 902장. 폴더 이름은 받은 그대로예요(대소문자, 띄어쓰기 포함).

| 폴더(유형) | 장수 |
|---|---:|
| Center | 100 |
| Donut | 102 |
| Edge Local | 103 |
| Edge Ring | 102 |
| Local | 100 |
| Scratch | 100 |
| near full | 95 |
| none | 100 |
| random | 100 |
| **합계** | **902** |

- 실제 폴더를 세고, zip 안 목록도 따로 세서 두 결과가 같은 걸 확인했어요.
- 파일 이름은 `641447.jpg`처럼 숫자예요(범위 640,687 ~ 811,440). **이 숫자는 원본 WM-811K의 행 번호(0부터 셈)예요.** (2026-11-06 확인)
  - 근거 1: 파일 번호를 원본 `WM811K.pkl`의 행 번호로 놓고 그 행의 `failureType`과 폴더 이름을 대조했더니 **902장 모두 일치**했어요. 1부터 세는 걸로 가정하면 187장만 맞았어요.
  - 근거 2: 유형마다 2장씩, 18장을 골라 원본 맵을 32×32로 줄이고 이미지와 비교했어요. 자기 번호의 맵과는 상관계수가 0.975~0.991로 나왔고, 같은 유형의 다른 맵과는 0.760~0.904로 더 낮았어요. 이미지가 그 번호의 웨이퍼를 그린 게 맞다는 뜻이에요.
  - 덧붙여 902장 모두 원본에서 `trainTestLabel = Test`로 표시된 행이에요. 이 프로젝트는 원본 분할을 쓰지 않고 902장을 다시 7:3으로 나눠요(8절).
  - 폴더 이름과 원본 표기의 대응: Center=Center, Donut=Donut, Edge Local=Edge-Loc, Edge Ring=Edge-Ring, Local=Loc, Scratch=Scratch, near full=Near-full, none=none, random=Random
- 각 이미지 옆에 `*.jpg:Zone.Identifier` 파일이 902개 있는데, Windows가 다운로드할 때 붙이는 표시 파일이라 데이터가 아니에요.

## 7. 원본과의 차이

| 항목 | 원본 WM-811K | 이 서브셋 |
|---|---|---|
| 규모 | 811,457장 | 902장 (일부만 이미지로 만든 것) |
| 형태 | 웨이퍼마다 크기가 다른 2차원 숫자 배열. 칸 값 0=웨이퍼 밖, 1=정상, 2=불량 | 이미지 파일 |
| 크기 | 웨이퍼마다 다름 (이 902장의 원본은 26×26 ~ 41×45 등 여러 크기) | 902장 모두 32×32 픽셀 |
| 형식 | `MIR-WM811K.zip` 안에 MATLAB용 `WM811K.mat`(3,596,549,129바이트)과 Python용 `WM811K.pkl`(pandas 표, 2,022,961,642바이트) 두 가지 | 902장 모두 JPEG(`.jpg`), RGB 3채널 컬러 |
| 표 항목 | `dieSize`, `failureType`, `lotName`, `trainTestLabel`, `waferIndex`, `waferMap` | 폴더 이름(유형)과 파일 번호(행 번호)만 남음 |
| 라벨 | 811,457행 중 172,950행에만 유형이 붙어 있고, 638,507행은 라벨 없음(`0`) | 9개 유형 모두 라벨 있음 |

- 확인 방법: Pillow로 902장을 모두 열어서 크기·형식·색 모드를 셌어요. 원본은 인터넷 아카이브의 `MIR-WM811K.zip`에서 `WM811K.pkl`만 받아 표 구조와 값을 셌어요.
- 원본 zip 구성: `MATLAB/`(`WM811K.mat`, `example.m`, `readme.txt`, MathWorks 튜토리얼 저장본, 스크린샷), `Python/`(`WM811K.pkl`, `example.py`, `readme.txt`, 스크린샷)
- 원본 유형별 행 수: none 147,431 / Edge-Ring 9,680 / Edge-Loc 5,189 / Center 4,294 / Loc 3,593 / Scratch 1,193 / Random 866 / Donut 555 / Near-full 149
- **Kaggle 설명과 다른 점**: 페이지에는 "32×32 `.png`"라고 적혀 있지만, 실제로 받은 파일은 모두 `.jpg`(JPEG)예요.
- JPEG는 압축하면서 색이 조금씩 뭉개져요. 예를 들어 첫 번째 이미지 한 장(32×32=1,024칸)에 서로 다른 색이 1,022가지 나와요. 원본은 칸마다 "웨이퍼 밖 / 정상 / 불량" 세 가지 값뿐이라, 이미지 색이 원본 값을 정확히 그대로 담고 있지는 않아요.
- 받은 zip에 처음부터 902장, 32×32 JPEG로 들어 있었어요. 이 프로젝트에서는 압축만 풀었고, 장수를 고르거나 크기를 바꾸지 않았어요.
- 그러니까 902장을 고르고 32×32 이미지로 만든 건 Kaggle에 올린 사람이에요.
- Kaggle 설명에 있는 MATLAB 코드(`grad.m`), `README.md`, 논문 PDF는 받은 zip에 없어요.

### 7-1. 서브셋을 만든 방법 (2026-11-06, 원본과 대조해 거꾸로 확인)

**만든 사람이 밝힌 내용**
- 논문 초록: "각 유형에서 무작위 추출(random sampling)로 모두 902장을 뽑았다."
- 논문 본문(올린 사람이 GitHub에 공유한 PDF)에는 뽑은 기준, 이미지로 바꾼 방법, 크기 조정 방법이 나와 있지 않아요. 데이터 증강을 하지 않았다는 점과 70/10/20 분할만 적혀 있어요.
- GitHub README: "이미지는 32×32 픽셀로 크기를 조정했다(resized)"는 한 줄만 있어요.

**실제로 어떻게 뽑혔는지 (원본 `WM811K.pkl` 행 번호로 확인)**
- 902장 모두 원본에서 `Test`로 표시된 행이에요. 라벨이 붙은 행 172,950개 중 Test는 118,595개(약 69%)라서, 전체에서 무작위로 뽑았다면 902장이 전부 Test일 가능성은 사실상 없어요.
- 유형별로 원본의 Test 행을 순서대로 늘어놓고 보면, **대부분 연속된 구간을 통째로 가져온 모양**이에요. 초록의 "무작위 추출"과는 맞지 않아요.

| 유형 | 선택 / 원본 Test 행 수 | 뽑힌 모양 | 로트 수 (최다 로트 장수) |
|---|---|---|---|
| Near-full | 95 / 95 | Test 행 전부 | 83 (4) |
| Random | 100 / 257 | 연속 100행 (Test 순번 156~255) | 55 (18) |
| Scratch | 100 / 693 | 연속 100행 (Test 순번 588~687) | 88 (3) |
| none | 100 / 110,701 | 거의 연속(간격 최대 2), 로트 6개에서만 | 6 (21) |
| Donut | 102 / 146 | 거의 연속(간격 1이 98번) | 78 (5) |
| Edge-Loc | 103 / 2,772 | 거의 연속(간격 1이 95번) | 42 (8) |
| Loc | 100 / 1,973 | 거의 연속(간격 1이 75번) | 91 (3) |
| Edge-Ring | 102 / 1,126 | 앞쪽 11행 + 몇 개의 연속 구간 | 52 (15) |
| Center | 100 / 832 | 비교적 흩어짐(간격 중앙값 12) | 93 (3) |

- 연속 구간 안에서 일부 행이 빠진 이유(예: Donut은 135행 구간에서 102장만 있음)는 **확인 필요**예요.

**이미지로 바꾼 방법 (재현 시도 결과)**
- 색: 원본 값 0/1/2가 각각 보라(평균 RGB 65,8,79), 청록(39,143,130), 노랑(245,231,48)으로 칠해져 있어요. Python 그림 도구 matplotlib의 기본 색표 **viridis**의 양 끝과 가운데 색(68,1,84 / 33,145,140 / 253,231,37)과 같아요. `plt.imshow(waferMap)`처럼 기본 설정으로 그린 것으로 보여요.
- JPEG 설정: 902장 모두 같은 압축표를 썼어요. 품질 75, 색 정보 4:2:0 압축, JFIF 기본 헤더예요. Python 이미지 도구 Pillow의 기본 저장 설정과 같아요.
- 크기 조정: 정확한 방법은 **재현하지 못했어요 (확인 필요)**.
  - 비교 기준선: 실제 이미지를 JPEG로 한 번 더 저장하면 평균 오차가 약 1.3(0~255 기준)이에요.
  - 가장 가까운 후보는 "viridis로 색칠 → Pillow bicubic으로 32×32 → JPEG 저장"인데, 평균 오차가 약 12.7로 기준선의 10배쯤 돼요. bilinear, lanczos, OpenCV식 linear, matplotlib으로 32×32 직접 그리기, 크게 키워 JPEG로 저장한 뒤 줄이기, 흐림 효과 추가도 시험했지만 모두 12.7보다 컸어요.
  - 실제 이미지는 원본을 그대로 줄인 것보다 눈에 띄게 흐리고 색 얼룩이 많아요. 그래서 위 후보들 말고 다른 처리 단계(예: 화면 캡처나 여러 번의 변환)가 더 있었을 수 있어요.
- 이 분석은 자동 비교로 추정한 거예요. 만든 사람이 직접 확인해 준 내용은 아니에요.

## 8. 이 프로젝트에서의 사용

- 웨이퍼 맵 불량 유형 분류 재현 및 확장 실험
- 결과를 지원서 포트폴리오에 인용
- 학습/테스트 분할: `test_size=0.3`, `random_state=42`, `stratify` 고정 (프로젝트 규칙)
- 포트폴리오에 인용할 때 적을 것:
  1. 원 논문 [1] Wu, Jang, Chen (2015), doi: 10.1109/TSM.2014.2364237 (원본 조건상 필수)
  2. 데이터셋 [2] MIR-WM811K: Dataset for wafer map failure pattern recognition, 2015, http://mirlab.org/dataset/public/ (원본 조건상 필수)
  3. 서브셋 출처: Kaggle "WM811k Silicon Wafer Map Dataset Image" (Muhammad Junayed), CC BY-SA 4.0
