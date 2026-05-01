package com.homefit.chat.backend.transaction.repository;

import com.homefit.chat.backend.transaction.entity.HousingTransaction;
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
                :budgetMax is null
                or (
                  ht.depositAmount is not null
                  and ht.depositAmount <= :budgetMax
                )
              )
            group by ht.region.sido, ht.region.sigungu
            order by count(ht.id) desc
            """)
    List<String> findRegionNamesByDealTypeAndBudget(
            @Param("dealType") String dealType,
            @Param("budgetMax") Long budgetMax,
            Pageable pageable
    );
}
