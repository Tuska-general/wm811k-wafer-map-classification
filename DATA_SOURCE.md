# 데이터 출처 (DATA_SOURCE)

> 마지막 확인: 2026-11-06 (2차 갱신). 표의 숫자는 로컬 파일을 직접 세거나 읽어서 확인한 값이에요.
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
  - "Enhancing Defect Recognition: Convolutional Neural Networks for Silicon Wafer Map Analysis," ICAEEE 2024.
  - DOI: 10.1109/ICAEEE62219.2024.10561853

## 5. 라이선스

- 받은 페이지(토론 글)에는 라이선스 표기가 없어요.
- 데이터셋 본 페이지의 License 칸에는 **CC BY-SA 4.0**으로 적혀 있어요 (2026-11-06 확인).
  - CC BY-SA 4.0은 출처를 밝히고, 이 데이터를 고쳐서 다시 배포할 때는 같은 라이선스로 배포하라는 조건이에요.
- 원본 WM-811K(MIR Lab) 자체의 이용 조건: **페이지에 명시 없음**
  - 2026-11-06 기준 http://mirlab.org/dataSet/public/ 은 404(없는 페이지)로 열리지 않아요.
  - 인터넷 아카이브 사본(2026-06-09 저장: http://web.archive.org/web/20260609012331/http://mirlab.org/dataset/public/)을 보면, "MIR lab이 공개 다운로드용으로 준비한 자료 목록"이라는 안내와 데이터 설명, 원 논문 정보, `MIR-WM811K.zip` 다운로드 링크만 있어요. 라이선스, 이용 약관, 저작권 문구는 없어요.
  - 다운로드 파일(`MIR-WM811K.zip`) 안에 따로 이용 조건이 들어 있는지는 **확인 필요** (현재 링크가 열리지 않아 내려받지 못했어요).
  - 정리하면, 원본은 "공개 다운로드"로 배포됐지만 조건이 적혀 있지 않아요. 그래서 인용할 때 원 논문(Wu et al., 2015)을 출처로 밝히는 게 안전해요.

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
- 파일 이름은 `641447.jpg`처럼 숫자예요. 이 숫자가 원본 WM-811K의 행 번호인지는 **확인 필요** (받은 페이지에 설명이 없어요).
- 각 이미지 옆에 `*.jpg:Zone.Identifier` 파일이 902개 있는데, Windows가 다운로드할 때 붙이는 표시 파일이라 데이터가 아니에요.

## 7. 원본과의 차이

| 항목 | 원본 WM-811K | 이 서브셋 |
|---|---|---|
| 규모 | 811,457장 | 902장 (일부만 이미지로 만든 것) |
| 형태 | 웨이퍼마다 크기가 다른 2차원 숫자 배열 (원본 배포 형식 상세는 확인 필요) | 이미지 파일 |
| 크기 | 웨이퍼마다 다름 | 902장 모두 32×32 픽셀 |
| 형식 | — | 902장 모두 JPEG(`.jpg`), RGB 3채널 컬러 |

- 확인 방법: Pillow로 902장을 모두 열어서 크기·형식·색 모드를 셌어요.
- **Kaggle 설명과 다른 점**: 페이지에는 "32×32 `.png`"라고 적혀 있지만, 실제로 받은 파일은 모두 `.jpg`(JPEG)예요.
- JPEG는 압축하면서 색이 조금씩 뭉개져요. 예를 들어 첫 번째 이미지 한 장(32×32=1,024칸)에 서로 다른 색이 1,022가지 나와요. 원본은 칸마다 "웨이퍼 밖 / 정상 / 불량" 세 가지 값뿐이라, 이미지 색이 원본 값을 정확히 그대로 담고 있지는 않아요.
- 받은 zip에 처음부터 902장, 32×32 JPEG로 들어 있었어요. 이 프로젝트에서는 압축만 풀었고, 장수를 고르거나 크기를 바꾸지 않았어요.
- 그러니까 902장을 고르고 32×32 이미지로 만든 건 Kaggle에 올린 사람이에요. Kaggle 설명에는 "WM811k에서 뽑은 균형 잡힌 서브셋"이라고만 적혀 있어요. 어떤 기준으로 골랐는지, 원본 배열을 어떤 방법으로 이미지로 바꿨는지는 **확인 필요** (만든 사람의 ICAEEE 2024 논문에 나와 있을 수 있어요).
- Kaggle 설명에 있는 MATLAB 코드(`grad.m`), `README.md`, 논문 PDF는 받은 zip에 없어요.

## 8. 이 프로젝트에서의 사용

- 웨이퍼 맵 불량 유형 분류 재현 및 확장 실험
- 결과를 지원서 포트폴리오에 인용
- 학습/테스트 분할: `test_size=0.3`, `random_state=42`, `stratify` 고정 (프로젝트 규칙)
- 포트폴리오에 인용할 때는 원 논문(Wu et al., 2015)과 Kaggle 데이터셋 출처, 라이선스(CC BY-SA 4.0)를 함께 적는 게 안전해요.
