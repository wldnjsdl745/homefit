package com.homefit.transaction.repository;

import com.homefit.transaction.entity.HousingTransaction;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface HousingTransactionRepository extends JpaRepository<HousingTransaction, Long> {

    @Query("""
            select ht.region.sigungu
            from HousingTransaction ht
            where ht.dealType = :dealType
              and (
                :budgetMaxInManwon is null
                or (
                  :dealType = 'sale'
                  and ht.salePriceAmount is not null
                  and ht.salePriceAmount <= :budgetMaxInManwon
                )
                or (
                  :dealType <> 'sale'
                  and
                  ht.depositAmount is not null
                  and ht.depositAmount <= :budgetMaxInManwon
                )
              )
            group by ht.region.sido, ht.region.sigungu
            order by count(ht.id) desc
            """)
    List<String> findRegionNamesByDealTypeAndBudget(
            @Param("dealType") String dealType,
            @Param("budgetMaxInManwon") Long budgetMaxInManwon,
            Pageable pageable
    );
}
