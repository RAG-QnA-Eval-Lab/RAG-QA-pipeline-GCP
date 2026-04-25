# QA 평가 데이터셋 작성 가이드

> RAG 파이프라인 평가에 사용할 QA 데이터셋을 수동으로 작성하거나 검수할 때 참고하는 문서.

---

## 1. 파일 위치 및 포맷

- **경로**: `data/eval/qa_pairs.json`
- **인코딩**: UTF-8, JSON
- **자동 생성 스크립트**: `python scripts/generate_qa.py` (LLM 기반 자동 생성)

---

## 2. 전체 구조

```json
{
  "version": "1.0",
  "generated_at": "2026-04-21T15:23:58+00:00",
  "model": "manual",
  "domain": "youth_policy",
  "categories": ["housing", "employment", "education", "welfare", "startup", "finance"],
  "total_count": 100,
  "difficulty_distribution": {
    "easy": 40,
    "medium": 40,
    "hard": 20
  },
  "qa_type_distribution": {
    "factual": 50,
    "reasoning": 30,
    "comparison": 20
  },
  "samples": [
    { ... },
    { ... }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `version` | string | 데이터셋 버전 (`"1.0"`) |
| `generated_at` | string | 생성/수정 일시 (ISO 8601) |
| `model` | string | 생성 방법. LLM 자동 생성 시 모델 ID, 수동 작성 시 `"manual"` |
| `domain` | string | 항상 `"youth_policy"` |
| `categories` | string[] | 포함된 카테고리 목록 |
| `total_count` | int | `samples` 배열의 총 개수 |
| `difficulty_distribution` | object | 난이도별 개수 (목표: easy 40%, medium 40%, hard 20%) |
| `qa_type_distribution` | object | 질문 유형별 개수 (목표: factual 50%, reasoning 30%, comparison 20%) |
| `samples` | object[] | QA 쌍 배열 |

---

## 3. 개별 QA 쌍 (sample) 필드

```json
{
  "id": "q001",
  "question": "청년 월세 한시 특별지원 신청 자격은?",
  "ground_truth": "만 19~34세 독립거주 무주택 청년으로, 청년가구 소득이 기준 중위소득 60% 이하이고 원가구 소득이 기준 중위소득 100% 이하인 경우 신청 가능하다.",
  "difficulty": "easy",
  "qa_type": "factual",
  "category": "housing",
  "policy_title": "청년 월세 한시 특별지원",
  "policy_id": "20260101001234567890",
  "reference_doc": "data_portal_policies.json",
  "reference_source": "data_portal"
}
```

### 필수 필드

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | string | 고유 식별자. `q001`부터 순번 | `"q101"` |
| `question` | string | 질문. 실제 청년이 할 법한 자연스러운 한국어 | `"청년 전세자금 대출 금리는?"` |
| `ground_truth` | string | 정답. 정책 원본에 근거한 2~5문장 | (아래 작성 규칙 참조) |
| `difficulty` | string | 난이도: `"easy"`, `"medium"`, `"hard"` | `"medium"` |
| `qa_type` | string | 질문 유형: `"factual"`, `"reasoning"`, `"comparison"` | `"factual"` |
| `category` | string | 정책 카테고리 (아래 목록 참조) | `"housing"` |

### 선택 필드 (권장)

| 필드 | 타입 | 설명 |
|------|------|------|
| `policy_title` | string | 근거 정책명 |
| `policy_id` | string | 근거 정책 ID (data_portal 등에서 부여된 ID) |
| `reference_doc` | string | 근거 파일명 (data/policies/raw/ 내 파일) |
| `reference_source` | string | 데이터 출처: `"data_portal"`, `"youthgo"`, `"kosaf"`, `"manual"` |

---

## 4. 카테고리

| 값 | 한국어 | 예시 정책 |
|----|--------|----------|
| `housing` | 주거 | 청년 월세 지원, 전세자금 대출, 매입임대 |
| `employment` | 취업/고용 | 국민취업지원제도, 일경험 프로그램 |
| `startup` | 창업 | 청년창업사관학교, 초기창업패키지 |
| `education` | 교육 | 국가장학금, 학자금 대출 |
| `welfare` | 복지 | 건강검진, 문화패스, 심리상담 |
| `finance` | 금융 | 청년도약계좌, 청년내일저축계좌 |

---

## 5. 난이도 기준

| 난이도 | 기준 | 예시 |
|--------|------|------|
| `easy` | 정책 텍스트에서 **직접 찾을 수 있는** 단순 사실 질문 | "신청 기간은?", "지원 금액은?" |
| `medium` | 정책 텍스트를 **종합/해석**해야 답할 수 있는 질문 | "신청 자격을 모두 갖추려면?", "지원 절차는?" |
| `hard` | **여러 정책 비교**하거나 **추론**이 필요한 질문 | "A와 B 정책을 동시에 받을 수 있나?", "어떤 정책이 더 유리한가?" |

목표 비율: easy 40% / medium 40% / hard 20%

---

## 6. 질문 유형 (qa_type)

| 유형 | 설명 | 예시 |
|------|------|------|
| `factual` | 사실 확인 (자격, 조건, 금액, 기간 등) | "신청 자격은?", "지원 금액은 얼마?" |
| `reasoning` | 조건 조합이나 판단이 필요 | "소득 분위가 5분위인 경우 지원 가능한가?" |
| `comparison` | 2개 이상 정책 간 비교 | "국가장학금 1유형과 2유형의 차이는?" |

목표 비율: factual 50% / reasoning 30% / comparison 20%

---

## 7. ground_truth 작성 규칙

이 필드가 평가의 정답 기준이 되므로 가장 중요합니다.

### 지켜야 할 것

- **정책 원본에 근거**: 반드시 `data/policies/raw/`에 있는 정책 텍스트에서 발췌하거나 요약
- **2~5문장**: 너무 짧으면 평가 불가, 너무 길면 노이즈
- **구체적 수치 포함**: 금액, 기간, 연령, 소득 기준 등 정량 정보가 있으면 반드시 포함
- **완결성**: 질문에 대한 답이 빠짐없이 포함되어야 함

### 피해야 할 것

- 정책 원본에 없는 내용을 추가하지 않기 (환각 방지)
- "~라고 합니다", "~인 것 같습니다" 같은 불확실한 표현 사용하지 않기
- 지나치게 긴 답변 (문단 단위) 작성하지 않기

### 예시

```
좋은 예:
  Q: "청년도약계좌 정부기여금 매칭 비율은?"
  A: "개인소득 기준 중위소득 50% 이하는 월 납입액의 6%, 50~100%는 3%, 100~180%는 미매칭이다. 
      정부기여금은 월 최대 2.4만원이다."

나쁜 예:
  Q: "청년도약계좌 정부기여금 매칭 비율은?"
  A: "정부기여금이 있습니다."  ← 너무 짧고 구체성 없음
```

---

## 8. ID 부여 규칙

- 형식: `q` + 3자리 순번 (예: `q001`, `q042`, `q150`)
- 기존 데이터셋에 추가할 때는 마지막 ID 다음 번호부터 시작
- 현재 마지막 ID: `q100` → 새로 추가 시 `q101`부터

---

## 9. 수동 추가 절차

### 9-1. 직접 JSON 편집

1. `data/eval/qa_pairs.json`을 열어 `samples` 배열 끝에 QA 쌍 추가
2. 상단 메타데이터 업데이트:
   - `total_count` 증가
   - `difficulty_distribution`, `qa_type_distribution` 값 조정
   - `generated_at`을 현재 시각으로 갱신
3. JSON 유효성 검사: `python -m json.tool data/eval/qa_pairs.json > /dev/null`

### 9-2. LLM 자동 생성 후 검수

```bash
# 50개 추가 생성 (기존 100개에 누적)
python scripts/generate_qa.py --count 50

# 드라이런으로 선택된 정책만 확인
python scripts/generate_qa.py --dry-run
```

생성 후 반드시 수동 검수:
- ground_truth가 정책 원본과 일치하는지 확인
- 질문이 모호하거나 중복되지 않는지 확인
- 난이도/카테고리 라벨이 적절한지 확인

---

## 10. 검증

데이터셋 유효성은 기존 테스트로 확인할 수 있습니다:

```bash
pytest tests/test_generate_qa.py -v
```

### 수동 체크리스트

- [ ] 모든 sample에 필수 필드 7개 존재 (`id`, `question`, `ground_truth`, `difficulty`, `qa_type`, `category`, `reference_source` 또는 `reference_doc`)
- [ ] `id`가 고유한지 확인 (중복 없음)
- [ ] `difficulty`가 `easy`/`medium`/`hard` 중 하나
- [ ] `qa_type`이 `factual`/`reasoning`/`comparison` 중 하나
- [ ] `category`가 6개 카테고리 중 하나
- [ ] `ground_truth`가 2문장 이상
- [ ] 상단 `total_count`가 실제 `samples` 배열 길이와 일치
- [ ] JSON 파싱 에러 없음

---

## 11. 평가 파이프라인에서의 사용

이 데이터셋은 다음과 같이 사용됩니다:

```
qa_pairs.json
    │
    ├──→ RAGAS v0.4: question + ground_truth + context + answer → 정량 점수
    ├──→ LLM Judge: question + context + answer → 정성 점수 (1-5)
    └──→ DeepEval:  question + context + answer → Hallucination Score
```

- `question`: RAG 파이프라인에 입력하여 검색 + 답변 생성
- `ground_truth`: RAGAS ContextRecall 등에서 정답 기준으로 사용
- `category`, `difficulty`: 결과 분석 시 그룹핑 기준
