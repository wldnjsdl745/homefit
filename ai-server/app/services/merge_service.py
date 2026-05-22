from app.schemas import Conditions


class MergeService:
    def merge(self, current: Conditions, raw: Conditions) -> Conditions:
        current_data = current.model_dump(exclude_none=True)
        raw_data = raw.model_dump(exclude_none=True)
        return Conditions(**{**current_data, **raw_data})
