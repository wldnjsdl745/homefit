package com.homefit.internal.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

public record UpsertConditionsResponse(
        @JsonProperty("session_id")
        String sessionId,
        Map<String, Object> conditions
) {
}
