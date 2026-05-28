package com.homefit.transaction.repository;

import com.homefit.transaction.entity.HousingTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;

public interface HousingTransactionRepository extends JpaRepository<HousingTransaction, Long> {

    @Query(nativeQuery = true, value = """
            SELECT r.sigungu                         AS sigungu,
                   r.legal_dong_name                 AS dong,
                   ht.building_name                  AS buildingName,
                   COUNT(*)                          AS dealCount,
                   ROUND(AVG(ht.sale_price_amount))  AS avgPrice,
                   MIN(ht.sale_price_amount)          AS minPrice,
                   MAX(ht.sale_price_amount)          AS maxPrice,
                   ROUND(AVG(ht.rental_area), 1)     AS avgArea,
                   MAX(ht.built_year)                AS builtYear
            FROM housing_transactions ht
            JOIN regions r ON ht.region_id = r.id
            WHERE ht.deal_type = 'sale'
              AND r.sido = '서울특별시'
              AND ht.sale_price_amount IS NOT NULL
              AND ht.sale_price_amount <= :budgetMax
              AND ht.contract_date >= :since
              AND ht.building_name IS NOT NULL
              AND ht.building_name != ''
            GROUP BY r.sigungu, r.legal_dong_name, ht.building_name
            ORDER BY COUNT(*) DESC
            LIMIT 60
            """)
    List<ApartmentResult> findSaleApartments(
            @Param("budgetMax") Long budgetMaxInManwon,
            @Param("since") LocalDate since
    );

    @Query(nativeQuery = true, value = """
            SELECT r.sigungu                         AS sigungu,
                   r.legal_dong_name                 AS dong,
                   NULL                              AS buildingName,
                   COUNT(*)                          AS dealCount,
                   ROUND(AVG(ht.sale_price_amount))  AS avgPrice,
                   MIN(ht.sale_price_amount)          AS minPrice,
                   MAX(ht.sale_price_amount)          AS maxPrice,
                   ROUND(AVG(ht.rental_area), 1)     AS avgArea,
                   MAX(ht.built_year)                AS builtYear
            FROM housing_transactions ht
            JOIN regions r ON ht.region_id = r.id
            WHERE ht.deal_type = 'sale'
              AND r.sido = '서울특별시'
              AND ht.sale_price_amount IS NOT NULL
              AND ht.sale_price_amount <= :budgetMax
              AND ht.contract_date >= :since
            GROUP BY r.sigungu, r.legal_dong_name
            ORDER BY COUNT(*) DESC
            LIMIT 60
            """)
    List<ApartmentResult> findSaleRegions(
            @Param("budgetMax") Long budgetMaxInManwon,
            @Param("since") LocalDate since
    );

    @Query(nativeQuery = true, value = """
            SELECT r.sigungu                        AS sigungu,
                   r.legal_dong_name                AS dong,
                   ht.building_name                 AS buildingName,
                   COUNT(*)                         AS dealCount,
                   ROUND(AVG(ht.deposit_amount))    AS avgPrice,
                   MIN(ht.deposit_amount)           AS minPrice,
                   MAX(ht.deposit_amount)           AS maxPrice,
                   ROUND(AVG(ht.rental_area), 1)    AS avgArea,
                   MAX(ht.built_year)               AS builtYear
            FROM housing_transactions ht
            JOIN regions r ON ht.region_id = r.id
            WHERE ht.deal_type = 'jeonse'
              AND r.sido = '서울특별시'
              AND ht.deposit_amount IS NOT NULL
              AND ht.deposit_amount <= :budgetMax
              AND ht.contract_date >= :since
              AND ht.building_name IS NOT NULL
              AND ht.building_name != ''
            GROUP BY r.sigungu, r.legal_dong_name, ht.building_name
            ORDER BY COUNT(*) DESC
            LIMIT 60
            """)
    List<ApartmentResult> findJeonseApartments(
            @Param("budgetMax") Long budgetMaxInManwon,
            @Param("since") LocalDate since
    );

    @Query(nativeQuery = true, value = """
            SELECT r.sigungu                        AS sigungu,
                   r.legal_dong_name                AS dong,
                   NULL                             AS buildingName,
                   COUNT(*)                         AS dealCount,
                   ROUND(AVG(ht.deposit_amount))    AS avgPrice,
                   MIN(ht.deposit_amount)           AS minPrice,
                   MAX(ht.deposit_amount)           AS maxPrice,
                   ROUND(AVG(ht.rental_area), 1)    AS avgArea,
                   MAX(ht.built_year)               AS builtYear
            FROM housing_transactions ht
            JOIN regions r ON ht.region_id = r.id
            WHERE ht.deal_type = 'jeonse'
              AND r.sido = '서울특별시'
              AND ht.deposit_amount IS NOT NULL
              AND ht.deposit_amount <= :budgetMax
              AND ht.contract_date >= :since
            GROUP BY r.sigungu, r.legal_dong_name
            ORDER BY COUNT(*) DESC
            LIMIT 60
            """)
    List<ApartmentResult> findJeonseRegions(
            @Param("budgetMax") Long budgetMaxInManwon,
            @Param("since") LocalDate since
    );

    @Query(nativeQuery = true, value = """
            SELECT r.sigungu                        AS sigungu,
                   r.legal_dong_name                AS dong,
                   ht.building_name                 AS buildingName,
                   COUNT(*)                         AS dealCount,
                   ROUND(AVG(ht.deposit_amount))    AS avgPrice,
                   MIN(ht.deposit_amount)           AS minPrice,
                   MAX(ht.deposit_amount)           AS maxPrice,
                   ROUND(AVG(ht.rental_area), 1)    AS avgArea,
                   MAX(ht.built_year)               AS builtYear
            FROM housing_transactions ht
            JOIN regions r ON ht.region_id = r.id
            WHERE ht.deal_type = 'monthly_rent'
              AND r.sido = '서울특별시'
              AND ht.deposit_amount IS NOT NULL
              AND ht.deposit_amount <= :budgetMax
              AND ht.monthly_rent IS NOT NULL
              AND ht.monthly_rent <= :monthlyRentMax
              AND ht.contract_date >= :since
              AND ht.building_name IS NOT NULL
              AND ht.building_name != ''
            GROUP BY r.sigungu, r.legal_dong_name, ht.building_name
            ORDER BY COUNT(*) DESC
            LIMIT 60
            """)
    List<ApartmentResult> findMonthlyRentApartments(
            @Param("budgetMax") Long budgetMaxInManwon,
            @Param("monthlyRentMax") Long monthlyRentMaxInManwon,
            @Param("since") LocalDate since
    );

    @Query(nativeQuery = true, value = """
            SELECT r.sigungu                        AS sigungu,
                   r.legal_dong_name                AS dong,
                   NULL                             AS buildingName,
                   COUNT(*)                         AS dealCount,
                   ROUND(AVG(ht.deposit_amount))    AS avgPrice,
                   MIN(ht.deposit_amount)           AS minPrice,
                   MAX(ht.deposit_amount)           AS maxPrice,
                   ROUND(AVG(ht.rental_area), 1)    AS avgArea,
                   MAX(ht.built_year)               AS builtYear
            FROM housing_transactions ht
            JOIN regions r ON ht.region_id = r.id
            WHERE ht.deal_type = 'monthly_rent'
              AND r.sido = '서울특별시'
              AND ht.deposit_amount IS NOT NULL
              AND ht.deposit_amount <= :budgetMax
              AND ht.monthly_rent IS NOT NULL
              AND ht.monthly_rent <= :monthlyRentMax
              AND ht.contract_date >= :since
            GROUP BY r.sigungu, r.legal_dong_name
            ORDER BY COUNT(*) DESC
            LIMIT 60
            """)
    List<ApartmentResult> findMonthlyRentRegions(
            @Param("budgetMax") Long budgetMaxInManwon,
            @Param("monthlyRentMax") Long monthlyRentMaxInManwon,
            @Param("since") LocalDate since
    );
}
