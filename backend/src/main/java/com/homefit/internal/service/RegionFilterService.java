package com.homefit.internal.service;

import com.homefit.internal.dto.ApartmentDetail;
import com.homefit.internal.dto.FilterRegionsRequest;
import com.homefit.internal.dto.FilterRegionsResponse;
import com.homefit.region.entity.RegionCommute;
import com.homefit.region.entity.RegionTransit;
import com.homefit.region.repository.RegionCommuteRepository;
import com.homefit.region.repository.RegionTransitRepository;
import com.homefit.transaction.repository.ApartmentResult;
import com.homefit.transaction.repository.HousingTransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RegionFilterService {

    private static final int RESULT_LIMIT = 5;
    private static final long WON_PER_MANWON = 10_000L;
    private static final LocalDate DATA_SINCE = LocalDate.of(2025, 1, 1);
    private static final double MAX_COMMUTE_MINUTES = 60.0;

    private final HousingTransactionRepository txnRepository;
    private final RegionTransitRepository transitRepository;
    private final RegionCommuteRepository commuteRepository;
    private final InternalConditionValidator validator;

    @Transactional(readOnly = true)
    public FilterRegionsResponse filter(FilterRegionsRequest request) {
        String dealType = validator.requireDealType(request.conditions());
        long budgetMaxInManwon = validator.requireBudgetMax(request.conditions()) / WON_PER_MANWON;
        String commuteDestination = readString(request.conditions(), "commute_destination");

        // 1. 아파트 후보 조회 (가격 기준, 최대 60건)
        List<ApartmentResult> candidates = fetchCandidates(dealType, budgetMaxInManwon, request.conditions());
        if (candidates.isEmpty()) {
            return new FilterRegionsResponse(List.of(), List.of(), List.of());
        }

        // 2. 구 단위 보조 데이터 로딩
        Set<String> sigungus = candidates.stream()
                .map(ApartmentResult::getSigungu)
                .collect(Collectors.toSet());

        Map<String, Double> transitScoreByGu = transitRepository.findBySigunguIn(sigungus).stream()
                .collect(Collectors.toMap(RegionTransit::getSigungu, RegionTransit::getTransitScore));

        Map<String, Integer> commuteMinutesByGu = commuteDestination != null
                ? commuteRepository.findBySigunguInAndDestinationKey(sigungus, commuteDestination).stream()
                        .collect(Collectors.toMap(RegionCommute::getSigungu, RegionCommute::getAvgMinutes))
                : Map.of();

        // 3. 복합 점수 계산
        long maxDealCount = candidates.stream().mapToLong(ApartmentResult::getDealCount).max().orElse(1L);

        record Scored(ApartmentResult apt, double score, Integer commuteMinutes) {}

        List<Scored> scored = candidates.stream()
                .map(apt -> {
                    double transitScore = transitScoreByGu.getOrDefault(apt.getSigungu(), 0.0) / 100.0;
                    double popularityScore = Math.log(apt.getDealCount() + 1) / Math.log(maxDealCount + 1);

                    double finalScore;
                    Integer commuteMinutes = null;

                    if (commuteDestination != null) {
                        int minutes = commuteMinutesByGu.getOrDefault(apt.getSigungu(), 60);
                        commuteMinutes = minutes;
                        double commuteScore = 1.0 - Math.min(minutes, (int) MAX_COMMUTE_MINUTES) / MAX_COMMUTE_MINUTES;
                        finalScore = 0.5 * commuteScore + 0.3 * transitScore + 0.2 * popularityScore;
                    } else {
                        finalScore = 0.6 * transitScore + 0.4 * popularityScore;
                    }

                    return new Scored(apt, finalScore, commuteMinutes);
                })
                .sorted(Comparator.comparingDouble(Scored::score).reversed())
                .limit(RESULT_LIMIT)
                .toList();

        // 4. 응답 구성
        List<ApartmentDetail> apartments = scored.stream()
                .map(s -> new ApartmentDetail(
                        s.apt().getSigungu(),
                        s.apt().getDong(),
                        s.apt().getBuildingName(),
                        s.apt().getAvgPrice(),
                        s.apt().getMinPrice(),
                        s.apt().getMaxPrice(),
                        s.apt().getAvgArea(),
                        s.apt().getBuiltYear(),
                        s.commuteMinutes(),
                        s.apt().getDealCount() != null ? s.apt().getDealCount().intValue() : 0
                ))
                .toList();

        List<String> regions = apartments.stream()
                .map(ApartmentDetail::sigungu)
                .distinct()
                .toList();

        return new FilterRegionsResponse(regions, List.of(), apartments);
    }

    private List<ApartmentResult> fetchCandidates(
            String dealType, long budgetMaxInManwon, Map<String, Object> conditions) {
        return switch (dealType) {
            case "sale" -> txnRepository.findSaleApartments(budgetMaxInManwon, DATA_SINCE);
            case "jeonse" -> txnRepository.findJeonseApartments(budgetMaxInManwon, DATA_SINCE);
            case "monthly_rent" -> {
                Long monthlyRentMax = readLong(conditions, "monthly_rent_max");
                yield monthlyRentMax != null
                        ? txnRepository.findMonthlyRentApartments(
                                budgetMaxInManwon,
                                monthlyRentMax / WON_PER_MANWON,
                                DATA_SINCE)
                        : txnRepository.findJeonseApartments(budgetMaxInManwon, DATA_SINCE);
            }
            default -> txnRepository.findJeonseApartments(budgetMaxInManwon, DATA_SINCE);
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
