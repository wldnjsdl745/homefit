package com.homefit.internal.api;

import com.homefit.internal.dto.FilterRegionsRequest;
import com.homefit.internal.dto.FilterRegionsResponse;
import com.homefit.internal.dto.UpsertConditionsRequest;
import com.homefit.internal.dto.UpsertConditionsResponse;
import com.homefit.internal.service.ConditionHistoryService;
import com.homefit.internal.service.RegionFilterService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal")
@RequiredArgsConstructor
public class InternalApiController {

    private final ConditionHistoryService conditionHistoryService;
    private final RegionFilterService regionFilterService;

    @PostMapping("/upsert-conditions")
    public UpsertConditionsResponse upsertConditions(
            @Valid @RequestBody UpsertConditionsRequest request
    ) {
        return conditionHistoryService.upsert(request);
    }

    @PostMapping("/filter")
    public FilterRegionsResponse filterRegions(
            @Valid @RequestBody FilterRegionsRequest request
    ) {
        return regionFilterService.filter(request);
    }
}
