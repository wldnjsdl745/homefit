package com.homefit.internal.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record FilterRegionsResponse(
        List<String> regions,
        @JsonProperty("region_details") List<RegionDetail> regionDetails
) {}
