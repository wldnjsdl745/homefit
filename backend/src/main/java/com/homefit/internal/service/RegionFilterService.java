package com.homefit.internal.service;

import com.homefit.internal.dto.FilterRegionsRequest;
import com.homefit.internal.dto.FilterRegionsResponse;
import com.homefit.internal.dto.RegionDetail;
import com.homefit.region.entity.RegionCommute;
import com.homefit.region.entity.RegionJeonseSafety;
import com.homefit.region.entity.RegionTransit;
import com.homefit.region.repository.RegionCommuteRepository;
import com.homefit.region.repository.RegionJeonseSafetyRepository;
import com.homefit.region.repository.RegionTransitRepository;
import com.homefit.transaction.repository.HousingTransactionRepository;
import com.homefit.transaction.repository.RegionCount;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RegionFilterService {

    private static final int RESULT_LIMIT = 5;
    private static final long WON_PER_MANWON = 10_000L;
    private static final double MAX_COMMUTE_MINUTES = 60.0;

    private final HousingTransactionRepository txnRepository;
    private final RegionTransitRepository transitRepository;
    private final RegionCommuteRepository commuteRepository;
    private final RegionJeonseSafetyRepository safetyRepository;
    private final InternalConditionValidator validator;

    @Transactional(readOnly = true)
    public FilterRegionsResponse filter(FilterRegionsRequest request) {
        String dealType = validator.requireDealType(request.conditions());
        long budgetMaxInManwon = validator.requireBudgetMax(request.conditions()) / WON_PER_MANWON;
        String commuteDestination = readString(request.conditions(), "commute_destination");

        // 1. 가격 기준 후보 구 조회
        List<RegionCount> candidates = fetchCandidates(dealType, budgetMaxInManwon, request.conditions());
        if (candidates.isEmpty()) {
            return new FilterRegionsResponse(List.of(), List.of());
        }

        Set<String> sigungus = candidates.stream()
                .map(RegionCount::getSigungu)
                .collect(Collectors.toSet());

        // 2. 보조 데이터 로딩
        Map<String, Double> transitScoreByGu = transitRepository.findBySigunguIn(sigungus).stream()
                .collect(Collectors.toMap(RegionTransit::getSigungu, RegionTransit::getTransitScore));

        Map<String, Integer> commuteMinutesByGu = commuteDestination != null
                ? commuteRepository.findBySigunguInAndDestinationKey(sigungus, commuteDestination).stream()
                        .collect(Collectors.toMap(RegionCommute::getSigungu, RegionCommute::getAvgMinutes))
                : Map.of();

        Map<String, String> safetyGradeByGu = "jeonse".equals(dealType)
                ? safetyRepository.findBySigunguIn(sigungus).stream()
                        .collect(Collectors.toMap(RegionJeonseSafety::getSigungu, RegionJeonseSafety::getSafetyGrade))
                : Map.of();

        // 3. 복합 점수 계산
        long maxCount = candidates.stream().mapToLong(RegionCount::getCount).max().orElse(1L);

        record Scored(String sigungu, double score, Integer commuteMinutes, String safetyGrade) {}

        List<Scored> scored = candidates.stream()
                .map(rc -> {
                    double priceScore = (double) rc.getCount() / maxCount;
                    double transitScore = transitScoreByGu.getOrDefault(rc.getSigungu(), 0.0) / 100.0;

                    double finalScore;
                    if (commuteDestination != null) {
                        int minutes = commuteMinutesByGu.getOrDefault(rc.getSigungu(), 60);
                        double commuteScore = 1.0 - Math.min(minutes, (int) MAX_COMMUTE_MINUTES) / MAX_COMMUTE_MINUTES;
                        finalScore = 0.5 * priceScore + 0.3 * commuteScore + 0.2 * transitScore;
                    } else {
                        finalScore = 0.7 * priceScore + 0.3 * transitScore;
                    }

                    return new Scored(
                            rc.getSigungu(),
                            finalScore,
                            commuteMinutesByGu.get(rc.getSigungu()),
                            safetyGradeByGu.get(rc.getSigungu())
                    );
                })
                .sorted(Comparator.comparingDouble(Scored::score).reversed())
                .limit(RESULT_LIMIT)
                .toList();

        // 4. 응답 구성
        List<String> regions = scored.stream().map(Scored::sigungu).toList();
        List<RegionDetail> details = scored.stream()
                .map(s -> new RegionDetail(s.sigungu(), s.commuteMinutes(), s.safetyGrade()))
                .toList();

        return new FilterRegionsResponse(regions, details);
    }

    private List<RegionCount> fetchCandidates(
            String dealType, long budgetMaxInManwon, Map<String, Object> conditions) {
        return switch (dealType) {
            case "sale" -> txnRepository.findSaleRegions(budgetMaxInManwon);
            case "monthly_rent" -> {
                Long monthlyRentMax = readLong(conditions, "monthly_rent_max");
                yield monthlyRentMax != null
                        ? txnRepository.findMonthlyRentRegions(budgetMaxInManwon, monthlyRentMax / WON_PER_MANWON)
                        : txnRepository.findJeonseRegions(budgetMaxInManwon);
            }
            default -> txnRepository.findJeonseRegions(budgetMaxInManwon);
        };
    }

    private static String readString(Map<String, Object> conditions, String key) {
        Object val = conditions.get(key);
        return val instanceof String s && !s.isBlank() ? s : null;
    }

    private static Long readLong(Map<String, Object> conditions, String key) {
        Object val = conditions.get(key);
        return val instanceof Number n ? n.longValue() : null;
    }
}
