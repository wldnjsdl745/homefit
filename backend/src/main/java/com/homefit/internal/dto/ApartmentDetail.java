package com.homefit.internal.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApartmentDetail(
        String sigungu,
        String dong,
        String name,
        @JsonProperty("avg_price_manwon") Long avgPriceManwon,
        @JsonProperty("min_price_manwon") Long minPriceManwon,
        @JsonProperty("max_price_manwon") Long maxPriceManwon,
        @JsonProperty("avg_area_sqm") Double avgAreaSqm,
        @JsonProperty("built_year") Integer builtYear,
        @JsonProperty("commute_minutes") Integer commuteMinutes,
        @JsonProperty("deal_count") Integer dealCount
) {}
