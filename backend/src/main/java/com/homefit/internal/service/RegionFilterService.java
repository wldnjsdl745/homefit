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
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.sql.ResultSet;
import java.sql.SQLException;
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
    private final JdbcTemplate jdbcTemplate;

    @Transactional(readOnly = true)
    public FilterRegionsResponse filter(FilterRegionsRequest request) {
        String dealType = validator.requireDealType(request.conditions());
        long budgetMaxInManwon = validator.requireBudgetMax(request.conditions()) / WON_PER_MANWON;
        String commuteDestination = readString(request.conditions(), "commute_destination");
        String preferredRegion = readString(request.conditions(), "preferred_region");
        String ageGroup = readString(request.conditions(), "age_group");
        Set<String> infrastructurePriorities = readStringSet(request.conditions(), "infrastructure_priorities");

        // 1. 단지명이 있으면 아파트 단지 후보를 우선 사용하고, 없으면 법정동 후보로 내려간다.
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

        Map<RegionKey, DemographicInsight> demographics = loadDemographics(sigungus);
        Map<RegionKey, FacilityInsight> facilities = loadFacilities(sigungus);

        // 3. 복합 점수 계산
        long maxDealCount = candidates.stream().mapToLong(ApartmentResult::getDealCount).max().orElse(1L);

        record Scored(
                ApartmentResult apt,
                double score,
                Integer commuteMinutes,
                RegionInsight insight,
                boolean preferredMatch,
                double ageScore,
                double infrastructureScore
        ) {}

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

                    RegionInsight insight = insightFor(apt, demographics, facilities);
                    boolean preferredMatch = matchesPreferredRegion(apt, preferredRegion);
                    double ageScore = ageScore(insight.demographic(), ageGroup);
                    double infrastructureScore = infrastructureScore(
                            insight.facility(),
                            infrastructurePriorities
                    );

                    finalScore += preferredMatch ? 0.20 : 0.0;
                    finalScore += 0.15 * ageScore;
                    finalScore += 0.15 * infrastructureScore;

                    return new Scored(
                            apt,
                            finalScore,
                            commuteMinutes,
                            insight,
                            preferredMatch,
                            ageScore,
                            infrastructureScore
                    );
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
                        s.apt().getDealCount() != null ? s.apt().getDealCount().intValue() : 0,
                        ageProfile(s.insight().demographic()),
                        infrastructureSummary(
                                s.insight().facility(),
                                s.apt().getSigungu(),
                                s.insight().facilityGuFallback()
                        ),
                        recommendationReason(
                                s.preferredMatch(),
                                s.ageScore(),
                                s.infrastructureScore(),
                                s.apt().getDealCount()
                        )
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
            case "sale" -> {
                List<ApartmentResult> apartments = txnRepository.findSaleApartments(budgetMaxInManwon, DATA_SINCE);
                yield apartments.isEmpty()
                        ? txnRepository.findSaleRegions(budgetMaxInManwon, DATA_SINCE)
                        : apartments;
            }
            case "jeonse" -> {
                List<ApartmentResult> apartments = txnRepository.findJeonseApartments(budgetMaxInManwon, DATA_SINCE);
                yield apartments.isEmpty()
                        ? txnRepository.findJeonseRegions(budgetMaxInManwon, DATA_SINCE)
                        : apartments;
            }
            case "monthly_rent" -> {
                Long monthlyRentMax = readLong(conditions, "monthly_rent_max");
                if (monthlyRentMax == null) {
                    yield List.of();
                }
                List<ApartmentResult> apartments = txnRepository.findMonthlyRentApartments(
                        budgetMaxInManwon,
                        monthlyRentMax / WON_PER_MANWON,
                        DATA_SINCE);
                yield apartments.isEmpty()
                        ? txnRepository.findMonthlyRentRegions(
                                budgetMaxInManwon,
                                monthlyRentMax / WON_PER_MANWON,
                                DATA_SINCE)
                        : apartments;
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

    private static Set<String> readStringSet(Map<String, Object> conditions, String key) {
        Object val = conditions.get(key);
        if (!(val instanceof List<?> values)) {
            return Set.of();
        }

        return values.stream()
                .filter(String.class::isInstance)
                .map(String.class::cast)
                .filter(s -> !s.isBlank())
                .collect(Collectors.toSet());
    }

    private Map<RegionKey, DemographicInsight> loadDemographics(Set<String> sigungus) {
        if (sigungus.isEmpty()) {
            return Map.of();
        }

        String placeholders = sigungus.stream().map(s -> "?").collect(Collectors.joining(", "));
        String sql = """
                SELECT sigungu, legal_dong_name, admin_dong_name, population_total,
                       child_ratio, youth_ratio, senior_ratio
                FROM neighborhood_demographics
                WHERE sido = '서울특별시'
                  AND sigungu IN (%s)
                ORDER BY reference_month DESC
                """.formatted(placeholders);

        List<String> params = new ArrayList<>(sigungus);
        Map<RegionKey, DemographicInsight> result = new HashMap<>();

        try {
            jdbcTemplate.query(
                    sql,
                    ps -> bindStrings(ps, params),
                    rs -> {
                        DemographicInsight insight = demographicInsight(rs);
                        String sigungu = rs.getString("sigungu");
                        String legalDong = rs.getString("legal_dong_name");
                        String adminDong = rs.getString("admin_dong_name");

                        putIfAbsent(result, new RegionKey(sigungu, legalDong), insight);
                        putIfAbsent(result, new RegionKey(sigungu, adminDong), insight);
                        putIfAbsent(result, new RegionKey(sigungu, null), insight);
                    }
            );
        } catch (DataAccessException ignored) {
            return Map.of();
        }

        return result;
    }

    private Map<RegionKey, FacilityInsight> loadFacilities(Set<String> sigungus) {
        if (sigungus.isEmpty()) {
            return Map.of();
        }

        String placeholders = sigungus.stream().map(s -> "?").collect(Collectors.joining(", "));
        String sql = """
                SELECT sigungu, legal_dong_name,
                       SUM(CASE WHEN facility_type = 'school' THEN 1 ELSE 0 END) AS school_count,
                       SUM(CASE WHEN facility_type IN ('hospital', 'pharmacy') THEN 1 ELSE 0 END) AS medical_count,
                       SUM(CASE WHEN facility_type = 'gym' THEN 1 ELSE 0 END) AS fitness_count,
                       SUM(CASE WHEN facility_type = 'nightlife' THEN 1 ELSE 0 END) AS nightlife_count,
                       SUM(CASE WHEN facility_type = 'transit' THEN 1 ELSE 0 END) AS transit_count
                FROM nearby_facilities
                WHERE sido = '서울특별시'
                  AND sigungu IN (%s)
                GROUP BY sigungu, legal_dong_name
                """.formatted(placeholders);

        List<String> params = new ArrayList<>(sigungus);
        Map<RegionKey, FacilityInsight> result = new HashMap<>();

        try {
            jdbcTemplate.query(
                    sql,
                    ps -> bindStrings(ps, params),
                    rs -> {
                        String sigungu = rs.getString("sigungu");
                        String legalDong = rs.getString("legal_dong_name");
                        FacilityInsight insight = new FacilityInsight(
                                rs.getInt("school_count"),
                                rs.getInt("medical_count"),
                                rs.getInt("fitness_count"),
                                rs.getInt("nightlife_count"),
                                rs.getInt("transit_count")
                        );
                        if (legalDong != null && !legalDong.isBlank()) {
                            putIfAbsent(result, new RegionKey(sigungu, legalDong), insight);
                        }
                        result.merge(
                                new RegionKey(sigungu, null),
                                insight,
                                RegionFilterService::mergeFacilities
                        );
                    }
            );
        } catch (DataAccessException ignored) {
            return Map.of();
        }

        return result;
    }

    private static void bindStrings(java.sql.PreparedStatement ps, List<String> values)
            throws SQLException {
        for (int i = 0; i < values.size(); i++) {
            ps.setString(i + 1, values.get(i));
        }
    }

    private static DemographicInsight demographicInsight(ResultSet rs) throws SQLException {
        Number populationTotal = (Number) rs.getObject("population_total");
        return new DemographicInsight(
                populationTotal != null ? populationTotal.intValue() : null,
                normalizeRatio(readDouble(rs, "child_ratio")),
                normalizeRatio(readDouble(rs, "youth_ratio")),
                normalizeRatio(readDouble(rs, "senior_ratio"))
        );
    }

    private static <T> void putIfAbsent(Map<RegionKey, T> map, RegionKey key, T value) {
        if (key.sigungu() != null && (key.dong() == null || !key.dong().isBlank())) {
            map.putIfAbsent(key, value);
        }
    }

    private static Double readDouble(ResultSet rs, String column) throws SQLException {
        Number value = (Number) rs.getObject(column);
        return value != null ? value.doubleValue() : null;
    }

    private static RegionInsight insightFor(
            ApartmentResult apt,
            Map<RegionKey, DemographicInsight> demographics,
            Map<RegionKey, FacilityInsight> facilities
    ) {
        RegionKey exact = new RegionKey(apt.getSigungu(), apt.getDong());
        RegionKey guOnly = new RegionKey(apt.getSigungu(), null);
        FacilityInsight exactFacility = facilities.get(exact);
        return new RegionInsight(
                demographics.getOrDefault(exact, demographics.get(guOnly)),
                exactFacility != null ? exactFacility : facilities.get(guOnly),
                exactFacility == null && facilities.containsKey(guOnly)
        );
    }

    private static FacilityInsight mergeFacilities(FacilityInsight left, FacilityInsight right) {
        return new FacilityInsight(
                left.schoolCount() + right.schoolCount(),
                left.medicalCount() + right.medicalCount(),
                left.fitnessCount() + right.fitnessCount(),
                left.nightlifeCount() + right.nightlifeCount(),
                left.transitCount() + right.transitCount()
        );
    }

    private static boolean matchesPreferredRegion(ApartmentResult apt, String preferredRegion) {
        if (preferredRegion == null || preferredRegion.isBlank()) {
            return false;
        }

        String normalized = normalizeRegionText(preferredRegion);
        if (normalized.isBlank()) {
            return false;
        }

        return normalizeRegionText(apt.getSigungu()).contains(normalized)
                || normalizeRegionText(apt.getDong()).contains(normalized)
                || normalizeRegionText(apt.getBuildingName()).contains(normalized);
    }

    private static String normalizeRegionText(String value) {
        if (value == null) {
            return "";
        }
        return value
                .replace(" ", "")
                .replace("근처", "")
                .replace("주변", "")
                .replace("쪽", "")
                .trim();
    }

    private static double ageScore(DemographicInsight demographic, String ageGroup) {
        if (demographic == null || ageGroup == null || ageGroup.equals("any")) {
            return 0.0;
        }
        return switch (ageGroup) {
            case "family" -> clamp(demographic.childRatio() / 0.20);
            case "young_adult" -> clamp(demographic.youthRatio() / 0.35);
            case "senior" -> clamp(demographic.seniorRatio() / 0.30);
            default -> 0.0;
        };
    }

    private static double infrastructureScore(FacilityInsight facility, Set<String> priorities) {
        if (facility == null || priorities == null || priorities.isEmpty()) {
            return 0.0;
        }

        double total = 0.0;
        int count = 0;
        for (String priority : priorities) {
            total += switch (priority) {
                case "school" -> clamp(facility.schoolCount() / 10.0);
                case "medical" -> clamp(facility.medicalCount() / 10.0);
                case "fitness" -> clamp(facility.fitnessCount() / 5.0);
                case "quiet" -> clamp(1.0 - facility.nightlifeCount() / 10.0);
                case "transit" -> clamp(facility.transitCount() / 5.0);
                case "nightlife" -> clamp(facility.nightlifeCount() / 5.0);
                default -> 0.0;
            };
            count++;
        }
        return count == 0 ? 0.0 : total / count;
    }

    private static String ageProfile(DemographicInsight demographic) {
        if (demographic == null) {
            return null;
        }

        return "연령층: 유소년 %.1f%%, 청년 %.1f%%, 고령층 %.1f%%".formatted(
                demographic.childRatio() * 100,
                demographic.youthRatio() * 100,
                demographic.seniorRatio() * 100
        );
    }

    private static String infrastructureSummary(
            FacilityInsight facility,
            String sigungu,
            boolean guFallback
    ) {
        if (facility == null) {
            return null;
        }

        String label = guFallback ? "인프라(%s 전체): ".formatted(sigungu) : "인프라: ";
        return label + "학교 %d, 의료 %d, 운동시설 %d, 유흥시설 %d, 교통 %d".formatted(
                facility.schoolCount(),
                facility.medicalCount(),
                facility.fitnessCount(),
                facility.nightlifeCount(),
                facility.transitCount()
        );
    }

    private static String recommendationReason(
            boolean preferredMatch,
            double ageScore,
            double infrastructureScore,
            Long dealCount
    ) {
        List<String> reasons = new ArrayList<>();
        if (preferredMatch) {
            reasons.add("희망 지역 조건과 맞음");
        }
        if (ageScore > 0.6) {
            reasons.add("선호 연령층과 유사");
        }
        if (infrastructureScore > 0.6) {
            reasons.add("중요 인프라 조건이 좋음");
        }
        if (dealCount != null && dealCount >= 10) {
            reasons.add("최근 거래 표본이 충분함");
        }
        return reasons.isEmpty() ? null : "추천 이유: " + String.join(", ", reasons);
    }

    private static double normalizeRatio(Double ratio) {
        if (ratio == null) {
            return 0.0;
        }
        return ratio > 1.0 ? ratio / 100.0 : ratio;
    }

    private static double clamp(double value) {
        return Math.max(0.0, Math.min(1.0, value));
    }

    private record RegionKey(String sigungu, String dong) {}

    private record DemographicInsight(
            Integer populationTotal,
            double childRatio,
            double youthRatio,
            double seniorRatio
    ) {}

    private record FacilityInsight(
            int schoolCount,
            int medicalCount,
            int fitnessCount,
            int nightlifeCount,
            int transitCount
    ) {}

    private record RegionInsight(
            DemographicInsight demographic,
            FacilityInsight facility,
            boolean facilityGuFallback
    ) {}
}
