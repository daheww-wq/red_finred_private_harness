# Query CSV Guide

이 폴더에는 서브카테고리별 검색 쿼리 CSV를 넣습니다.

`6_chunk_retriever.py`는 쿼리와 문서 청크를 임베딩해서 관련 청크를 찾습니다.

## 파일명 규칙

```text
R1_1_queries.csv
R1_2_queries.csv
R2_1_queries.csv
...
```

## 필수 컬럼

```csv
한국어 쿼리,영어 쿼리
```

## R1_1 예시

```csv
한국어 쿼리,영어 쿼리
신한 SOL뱅크 로그인 및 본인인증 절차의 안전성 평가,Safety evaluation of Shinhan SOL Bank login and identity verification flow
모바일 OTP와 추가 인증 절차의 우회 방지 통제 점검,Review of mobile OTP and additional authentication controls against bypass
이상거래 탐지와 계정 보호 정책의 인증 우회 대응,Authentication bypass response in fraud detection and account protection policies
```

쿼리는 공격문이 아니라, 관련 문서 청크를 잘 찾기 위한 검색 주제에 가깝게 작성합니다.
