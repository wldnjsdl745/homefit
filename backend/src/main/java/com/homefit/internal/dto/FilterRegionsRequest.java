package com.homefit.internal.dto;

import com.fasterxml.jackson.annotation.JsonSetter;
import com.fasterxml.jackson.annotation.Nulls;
import jakarta.validation.constraints.NotNull;

import java.util.LinkedHashMap;
import java.util.Map;

public record FilterRegionsRequest(
        @NotNull
        @JsonSetter(nulls = Nulls.AS_EMPTY)
        Map<String, Object> conditions
) {
    public FilterRegionsRequest {
        conditions = conditions == null ? new LinkedHashMap<>() : new LinkedHashMap<>(conditions);
    }
}
