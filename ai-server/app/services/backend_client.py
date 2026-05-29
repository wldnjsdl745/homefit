from abc import ABC, abstractmethod
from typing import Optional
from uuid import uuid4

import httpx
from pydantic import ValidationError

from app.schemas import (
    ApartmentDetail,
    Conditions,
    ErrorResponse,
    FilterRegionsRequest,
    FilterRegionsResponse,
    UpsertConditionsRequest,
    UpsertConditionsResponse,
)
from app.services.merge_service import MergeService


class BackendClientError(RuntimeError):
    def __init__(self, error: ErrorResponse):
        super().__init__(f"{error.code}: {error.message}")
        self.error = error


class BackendClient(ABC):
    @abstractmethod
    async def upsert_conditions(
        self,
        session_id: str | None,
        raw: Conditions,
        conditions: Conditions,
    ) -> UpsertConditionsResponse:
        raise NotImplementedError

    @abstractmethod
    async def filter_regions(self, conditions: Conditions) -> FilterRegionsResponse:
        raise NotImplementedError


class HttpBackendClient(BackendClient):
    def __init__(self, base_url: str, timeout_ms: int, filter_timeout_ms: Optional[int] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_ms / 1000
        self.filter_timeout = (filter_timeout_ms if filter_timeout_ms is not None else timeout_ms) / 1000

    async def upsert_conditions(
        self,
        session_id: str | None,
        raw: Conditions,
        conditions: Conditions,
    ) -> UpsertConditionsResponse:
        payload = UpsertConditionsRequest(
            session_id=session_id,
            raw=raw,
            conditions=conditions,
        )
        response = await self._post_with_retry(
            "/internal/upsert-conditions",
            payload.model_dump(mode="json"),
        )
        try:
            return UpsertConditionsResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise BackendClientError(
                ErrorResponse(
                    code="AI-BE-003",
                    message="Backend 응답을 해석하지 못했어요. 잠시 후 다시 시도해주세요.",
                    detail=str(exc),
                )
            ) from exc

    async def filter_regions(self, conditions: Conditions) -> FilterRegionsResponse:
        payload = FilterRegionsRequest(conditions=conditions)
        response = await self._post_with_retry(
            "/internal/filter",
            payload.model_dump(mode="json"),
            timeout=self.filter_timeout,
        )
        try:
            return FilterRegionsResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise BackendClientError(
                ErrorResponse(
                    code="AI-BE-003",
                    message="Backend 응답을 해석하지 못했어요. 잠시 후 다시 시도해주세요.",
                    detail=str(exc),
                )
            ) from exc

    async def _post_with_retry(
        self,
        path: str,
        payload: dict,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        last_error: httpx.HTTPError | None = None

        for _ in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                    response = await client.post(f"{self.base_url}{path}", json=payload)
                    if response.status_code >= 400:
                        try:
                            body = response.json()
                            raise BackendClientError(
                                ErrorResponse(
                                    code=body.get("code", "AI-BE-001"),
                                    message=body.get("message", "Backend 오류가 발생했어요."),
                                    detail=body.get("detail", str(response.status_code)),
                                )
                            )
                        except (KeyError, ValueError):
                            pass
                    response.raise_for_status()
                    return response
            except BackendClientError:
                raise
            except httpx.HTTPStatusError as error:
                raise self._to_status_error(path, error) from error
            except httpx.HTTPError as error:
                last_error = error

        if last_error is not None:
            raise BackendClientError(
                ErrorResponse(
                    code="AI-BE-001",
                    message="Backend에 연결할 수 없어요. 잠시 후 다시 시도해주세요.",
                    detail=f"{path}: {last_error}",
                )
            ) from last_error

        raise BackendClientError(
            ErrorResponse(
                code="AI-BE-004",
                message="Backend 요청 처리 중 알 수 없는 문제가 발생했어요.",
                detail=f"{path}: HTTP retry loop exited unexpectedly.",
            )
        )

    @staticmethod
    def _to_status_error(path: str, error: httpx.HTTPStatusError) -> BackendClientError:
        status = error.response.status_code
        try:
            backend_error = ErrorResponse.model_validate(error.response.json())
            detail = f"{path}: HTTP {status}; {backend_error.code}; {backend_error.detail}"
        except (ValueError, ValidationError):
            detail = f"{path}: HTTP {status}; {error.response.text[:300]}"

        if 400 <= status < 500:
            return BackendClientError(
                ErrorResponse(
                    code="AI-BE-002",
                    message="요청 조건을 처리할 수 없어요. 입력값을 다시 확인해주세요.",
                    detail=detail,
                )
            )

        return BackendClientError(
            ErrorResponse(
                code="AI-BE-001",
                message="Backend가 일시적으로 응답하지 않아요. 잠시 후 다시 시도해주세요.",
                detail=detail,
            )
        )


class MockBackendClient(BackendClient):
    def __init__(self, merge_service: MergeService | None = None):
        self.merge_service = merge_service or MergeService()
        self.sessions: dict[str, Conditions] = {}

    async def upsert_conditions(
        self,
        session_id: str | None,
        raw: Conditions,
        conditions: Conditions,
    ) -> UpsertConditionsResponse:
        next_session_id = session_id or str(uuid4())
        previous = self.sessions.get(next_session_id, conditions)
        merged = self.merge_service.merge(previous, raw)
        self.sessions[next_session_id] = merged
        return UpsertConditionsResponse(session_id=next_session_id, conditions=merged)

    async def filter_regions(self, conditions: Conditions) -> FilterRegionsResponse:
        if conditions.budget_max is not None and conditions.budget_max < 60_000_000:
            return FilterRegionsResponse(regions=[], region_details=[], apartments=[])

        dest = conditions.commute_destination
        commute_minutes = 20 if dest else None

        if conditions.deal_type == "jeonse":
            apts = [
                ApartmentDetail(
                    sigungu="마포구",
                    dong="합정동",
                    name="마포 한강 자이",
                    avg_price_manwon=50_000,
                    avg_area_sqm=59.0,
                    built_year=2018,
                    commute_minutes=commute_minutes,
                ),
                ApartmentDetail(
                    sigungu="성동구",
                    dong="성수동",
                    name="서울숲 리버뷰",
                    avg_price_manwon=55_000,
                    avg_area_sqm=84.0,
                    built_year=2021,
                    commute_minutes=commute_minutes,
                ),
                ApartmentDetail(
                    sigungu="광진구",
                    dong="구의동",
                    name="광진 e편한세상",
                    avg_price_manwon=45_000,
                    avg_area_sqm=59.0,
                    built_year=2016,
                    commute_minutes=commute_minutes,
                ),
            ]
        elif conditions.deal_type == "monthly_rent":
            apts = [
                ApartmentDetail(
                    sigungu="관악구",
                    dong="신림동",
                    name="관악 두산위브",
                    avg_price_manwon=5_000,
                    avg_area_sqm=45.0,
                    built_year=2010,
                    commute_minutes=commute_minutes,
                ),
                ApartmentDetail(
                    sigungu="동작구",
                    dong="사당동",
                    name="사당 래미안",
                    avg_price_manwon=6_000,
                    avg_area_sqm=59.0,
                    built_year=2014,
                    commute_minutes=commute_minutes,
                ),
            ]
        elif conditions.deal_type == "sale":
            apts = [
                ApartmentDetail(
                    sigungu="노원구",
                    dong="상계동",
                    name="상계주공9단지",
                    avg_price_manwon=45_000,
                    avg_area_sqm=59.0,
                    built_year=1991,
                    commute_minutes=commute_minutes,
                ),
                ApartmentDetail(
                    sigungu="도봉구",
                    dong="창동",
                    name="창동 주공19단지",
                    avg_price_manwon=40_000,
                    avg_area_sqm=49.0,
                    built_year=1993,
                    commute_minutes=commute_minutes,
                ),
            ]
        else:
            apts = [
                ApartmentDetail(
                    sigungu="마포구",
                    dong="공덕동",
                    name="공덕 SK리더스뷰",
                    avg_price_manwon=52_000,
                    avg_area_sqm=59.0,
                    built_year=2015,
                    commute_minutes=commute_minutes,
                ),
            ]

        regions = list({a.sigungu for a in apts})
        return FilterRegionsResponse(regions=regions, region_details=[], apartments=apts)
