package com.homefit.internal.service;

import com.homefit.internal.dto.FilterRegionsRequest;
import com.homefit.internal.dto.FilterRegionsResponse;
import com.homefit.transaction.repository.HousingTransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class RegionFilterService {

    private static final int REGION_LIMIT = 3;

    private final HousingTransactionRepository housingTransactionRepository;
    private final InternalConditionValidator validator;

    @Transactional(readOnly = true)
    public FilterRegionsResponse filter(FilterRegionsRequest request) {
        String dealType = validator.requireDealType(request.conditions());
        long budgetMax = validator.requireBudgetMax(request.conditions());

        return new FilterRegionsResponse(
                housingTransactionRepository.findRegionNamesByDealTypeAndBudget(
                        dealType,
                        budgetMax,
                        PageRequest.of(0, REGION_LIMIT)
                )
        );
    }
}
