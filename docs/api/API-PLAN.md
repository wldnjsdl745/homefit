# API 변경 계획

- 작성일: `2026-05-16`
- 대상 문서: [`API.md`](./API.md)
- 목적: 매매 데이터 추가에 따른 API 명세 변경 사항 정리

---

## 1. 변경 배경

DB에 기존 전세(`jeonse`), 월세(`monthly_rent`) 외에 매매(`sale`) 데이터가 추가되었습니다.

따라서 `docs/api/API.md` API 명세서에 아래 주요 변경 사항을 반영해야 합니다.

---

## 2. 주요 변경 사항

## 2.1 `deal_type` 허용값에 `sale` 추가

기존 거래 유형인 전세(`jeonse`), 월세(`monthly_rent`) 외에 매매(`sale`)를 추가합니다.

변경 후 허용 거래 유형:

| 값 | 의미 |
|---|---|
| `jeonse` | 전세 |
| `monthly_rent` | 월세 |
| `sale` | 매매 |

---

## 2.2 condition item에 `monthly_rent_max` 추가

월세 계산을 위해 condition item에 `monthly_rent_max`를 추가합니다.

예시:

```json
{
  "budget_max": 200000000,
  "deal_type": "monthly_rent",
  "monthly_rent_max": 800000
}
```

규칙:

- 월세(`monthly_rent`) 조건이면 사용자가 직접 입력한 월세 예산을 `monthly_rent_max`로 전달합니다.
- 전세(`jeonse`)와 매매(`sale`) 조건이면 `monthly_rent_max`는 `null`입니다.
- API 입력값은 원 단위입니다.
- BE는 DB 조회 시 `monthly_rent_max / 10000`으로 만원 단위 변환 후 비교합니다.
- BE는 `monthly_rent <= monthly_rent_max_in_manwon` 조건으로 입력한 월세 금액 이하의 지역을 필터링합니다.

---

## 2.3 서울 내부 추천 제한

추천 결과는 서울 내부 지역만 반환합니다.

규칙:

- BE는 서울 지역 거래 데이터만 필터링 대상에 포함합니다.
- `regions`에는 서울 내부 지역명만 반환합니다.
- 추천 후보는 서울 지역 데이터로만 구성합니다.

