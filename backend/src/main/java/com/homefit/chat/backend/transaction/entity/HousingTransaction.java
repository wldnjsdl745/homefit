package com.homefit.chat.backend.transaction.entity;

import com.homefit.chat.backend.region.entity.Region;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "housing_transactions")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class HousingTransaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "region_id", nullable = false)
    private Region region;

    @Column(name = "deal_type", nullable = false, length = 30))
    private String dealType;

    @Column(name = "deposit_amount")
    private Long depositAmount;

    @Column(name = "monthly_rent")
    private Integer monthlyRent;

    @Column(name = "contract_date", nullable = false)
    private LocalDate contractDate;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}
