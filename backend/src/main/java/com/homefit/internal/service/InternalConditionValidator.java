package com.homefit.internal.service;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Set;

@Component
public class InternalConditionValidator {

    private static final long MAX_BUDGET = 10_000_000_000L;
    private static final Set<String> DEAL_TYPES = Set.of("jeonse", "monthly_rent", "sale");

    public void validatePartial(Map<String, Object> conditions) {
        Object budgetMax = conditions.get("budget_max");
        if (budgetMax != null) {
            readBudgetMax(conditions);
        }

        Object dealType = conditions.get("deal_type");
        if (dealType != null) {
            readDealType(conditions);
        }
    }

    public long requireBudgetMax(Map<String, Object> conditions) {
        Object value = conditions.get("budget_max");
        if (value == null) {
            throw new InvalidInternalApiRequestException("conditions.budget_max is required.");
        }

        return readBudgetMax(conditions);
    }

    public String requireDealType(Map<String, Object> conditions) {
        Object value = conditions.get("deal_type");
        if (value == null) {
            throw new InvalidInternalApiRequestException("conditions.deal_type is required.");
        }

        return readDealType(conditions);
    }

    private long readBudgetMax(Map<String, Object> conditions) {
        Object value = conditions.get("budget_max");
        if (!(value instanceof Number number)) {
            throw new InvalidInternalApiRequestException("conditions.budget_max must be a number.");
        }

        long budgetMax = number.longValue();
        if (budgetMax <= 0 || budgetMax > MAX_BUDGET || number.doubleValue() != budgetMax) {
            throw new InvalidInternalApiRequestException("conditions.budget_max must be a positive integer up to 10000000000.");
        }

        return budgetMax;
    }

    private String readDealType(Map<String, Object> conditions) {
        Object value = conditions.get("deal_type");
        if (!(value instanceof String dealType) || !DEAL_TYPES.contains(dealType)) {
            throw new InvalidInternalApiRequestException("conditions.deal_type must be jeonse, monthly_rent, or sale.");
        }

        return dealType;
    }
}
