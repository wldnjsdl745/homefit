package com.homefit.transaction.repository;

import com.homefit.transaction.entity.HousingTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface HousingTransactionRepository extends JpaRepository<HousingTransaction, Long> {

    // 전세 — deposit_amount 기준 필터
    @Query("""
            SELECT ht.region.sigungu AS sigungu, COUNT(ht.id) AS count
            FROM HousingTransaction ht
            WHERE ht.dealType = 'jeonse'
              AND ht.region.sido = '서울특별시'
              AND ht.depositAmount IS NOT NULL
              AND ht.depositAmount <= :budgetMax
            GROUP BY ht.region.sigungu
            """)
    List<RegionCount> findJeonseRegions(@Param("budgetMax") Long budgetMaxInManwon);

    // 월세 — 보증금 + 월세 동시 필터
    @Query("""
            SELECT ht.region.sigungu AS sigungu, COUNT(ht.id) AS count
            FROM HousingTransaction ht
            WHERE ht.dealType = 'monthly_rent'
              AND ht.region.sido = '서울특별시'
              AND ht.depositAmount IS NOT NULL
              AND ht.depositAmount <= :budgetMax
              AND ht.monthlyRent IS NOT NULL
              AND ht.monthlyRent <= :monthlyRentMax
            GROUP BY ht.region.sigungu
            """)
    List<RegionCount> findMonthlyRentRegions(
            @Param("budgetMax") Long budgetMaxInManwon,
            @Param("monthlyRentMax") Long monthlyRentMaxInManwon
    );

    // 매매 — sale_price_amount 기준 필터
    @Query("""
            SELECT ht.region.sigungu AS sigungu, COUNT(ht.id) AS count
            FROM HousingTransaction ht
            WHERE ht.dealType = 'sale'
              AND ht.region.sido = '서울특별시'
              AND ht.salePriceAmount IS NOT NULL
              AND ht.salePriceAmount <= :budgetMax
            GROUP BY ht.region.sigungu
            """)
    List<RegionCount> findSaleRegions(@Param("budgetMax") Long budgetMaxInManwon);
}
