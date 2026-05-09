package com.homefit.internal.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSetter;
import com.fasterxml.jackson.annotation.Nulls;
import jakarta.validation.constraints.NotNull;

import java.util.LinkedHashMap;
import java.util.Map;

public record UpsertConditionsRequest(
        @JsonProperty("session_id")
        String sessionId,

        @NotNull
        @JsonSetter(nulls = Nulls.AS_EMPTY)
        Map<String, Object> raw,

        @NotNull
        @JsonSetter(nulls = Nulls.AS_EMPTY)
        Map<String, Object> conditions
) {
    public UpsertConditionsRequest {
        raw = raw == null ? new LinkedHashMap<>() : new LinkedHashMap<>(raw);
        conditions = conditions == null ? new LinkedHashMap<>() : new LinkedHashMap<>(conditions);
    }
}
