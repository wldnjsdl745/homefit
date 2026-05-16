from abc import ABC, abstractmethod
from uuid import uuid4

import httpx

from app.schemas import (
    Conditions,
    FilterRegionsRequest,
    FilterRegionsResponse,
    UpsertConditionsRequest,
    UpsertConditionsResponse,
)
from app.services.merge_service import MergeService


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
    def __init__(self, base_url: str, timeout_ms: int):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_ms / 1000

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
        return UpsertConditionsResponse.model_validate(response.json())

    async def filter_regions(self, conditions: Conditions) -> FilterRegionsResponse:
        payload = FilterRegionsRequest(conditions=conditions)
        response = await self._post_with_retry(
            "/internal/filter",
            payload.model_dump(mode="json"),
        )
        return FilterRegionsResponse.model_validate(response.json())

    async def _post_with_retry(self, path: str, payload: dict) -> httpx.Response:
        last_error: httpx.HTTPError | None = None

        for _ in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.base_url}{path}", json=payload)
                    response.raise_for_status()
                    return response
            except httpx.HTTPError as error:
                last_error = error

        if last_error is not None:
            raise last_error

        raise RuntimeError("HTTP retry loop exited unexpectedly.")


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
        # Region recommendation stays a backend responsibility. preference_text is intentionally
        # ignored by the mock filter until the real backend defines how to use it.
        if conditions.budget_max is not None and conditions.budget_max < 60_000_000:
            return FilterRegionsResponse(regions=[])

        if conditions.deal_type == "jeonse":
            return FilterRegionsResponse(regions=["분당", "성남", "경기도"])

        return FilterRegionsResponse(regions=["봉천동", "신림동", "사당동"])
