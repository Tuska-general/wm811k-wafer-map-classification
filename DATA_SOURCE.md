# 데이터 출처 (DATA_SOURCE)

> 마지막 확인: 2026-11-06. 표의 숫자는 로컬 파일을 직접 세거나 읽어서 확인한 값이에요.
> 확인하지 못한 항목은 "확인 필요"로 남겨 뒀어요.

## 1. 데이터 이름

WM-811K 웨이퍼 맵 이미지 (9개 유형, 902장 서브셋)

- Kaggle 데이터셋 제목: *WM811k Silicon Wafer Map Dataset Image* (올린 사람: Muhammad Junayed)

## 2. 받은 곳

- 받은 페이지(토론 글): https://www.kaggle.com/datasets/muhammedjunayed/wm811k-silicon-wafer-map-dataset-image/discussion/599874
- 데이터셋 본 페이지: https://www.kaggle.com/datasets/muhammedjunayed/wm811k-silicon-wafer-map-dataset-image
- 로컬 파일: `WM811k Dataset.zip` (1,037,027바이트)
  - SHA-256: `fecc626921730c9303ddc754b561667dc7b99498f87ca251a4af4420a36dcedd`
  - 압축 파일과 풀린 폴더(`WM811k Dataset/`)는 용량 때문에 git에 올리지 않아요(`.gitignore`).

## 3. 받은 날짜

2026년 6월 (6/23 분석 이전)

- 참고: 지금 폴더에 있는 zip 파일의 수정 시각은 2026-08-26 16:33(KST)이에요. 다시 내려받았거나 복사하면서 시각이 바뀌었을 수 있어요. 실제 최초 다운로드 날짜는 **확인 필요**.

## 4. 원본 데이터

- 원본: WM-811K (대만 국립칭화대 MIR Lab 공개 데이터)
  - Kaggle 데이터셋 설명에 적힌 원 출처 주소: http://mirlab.org/dataSet/public/
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
- 원본 WM-811K(MIR Lab) 자체의 이용 조건: **확인 필요**

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
- 파일 이름은 `641447.jpg`처럼 숫자예요. 이 숫자가 원본 WM-811K의 행 번호인지는 **확인 필요**.
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
- 902장을 어떤 기준으로 골랐는지, 원본 배열을 어떤 방법으로 32×32로 줄였는지는 **확인 필요**.
- Kaggle 설명에 있는 MATLAB 코드(`grad.m`), `README.md`, 논문 PDF는 받은 zip에 없어요.

## 8. 이 프로젝트에서의 사용

- 웨이퍼 맵 불량 유형 분류 재현 및 확장 실험
- 결과를 지원서 포트폴리오에 인용
- 학습/테스트 분할: `test_size=0.3`, `random_state=42`, `stratify` 고정 (프로젝트 규칙)
- 포트폴리오에 인용할 때는 원 논문(Wu et al., 2015)과 Kaggle 데이터셋 출처, 라이선스(CC BY-SA 4.0)를 함께 적는 게 안전해요.
