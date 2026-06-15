# Schema Guide

이 폴더에는 Step1과 Step2가 참고하는 JSON 스키마를 넣습니다.

코드 기준 경로:

```text
schemas/ko/{category}.json
schemas/en/{category}.json
```

예:

```text
schemas/ko/R1_1.json
schemas/en/R1_1.json
```

## JSON 구조

각 스키마 파일은 최소한 아래 키를 포함해야 합니다.

```json
{
  "Schema": {},
  "Description": "각 필드 설명",
  "few_shot_good_examples": "",
  "few_shot_schema_examples": "",
  "few_shot_seeds": "",
  "few_shot_seeds_eng": ""
}
```

`Step1_build.py`는 주로 `Schema`, `Description`, `few_shot_good_examples`, `few_shot_schema_examples`를 사용합니다.

`Step2_build.py`는 주로 `Schema`, `Description`, `few_shot_seeds` 또는 `few_shot_seeds_eng`를 사용합니다.
