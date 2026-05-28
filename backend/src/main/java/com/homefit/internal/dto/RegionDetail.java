package com.homefit.internal.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record RegionDetail(
        String name,
        @JsonProperty("commute_minutes") Integer commuteMinutes,
        @JsonProperty("safety_grade") String safetyGrade
) {}
