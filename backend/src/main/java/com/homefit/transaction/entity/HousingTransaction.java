package com.homefit.transaction.entity;

import com.homefit.region.entity.Region;
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

    @Column(name = "deal_type", nullable = false, length = 30)
    private String dealType;

    @Column(name = "deposit_amount")
    private Long depositAmount;

    @Column(name = "sale_price_amount")
    private Long salePriceAmount;

    @Column(name = "monthly_rent")
    private Integer monthlyRent;

    @Column(name = "contract_date", nullable = false)
    private LocalDate contractDate;

    @Column(name = "rental_area")
    private Double rentalArea;

    @Column(name = "floor_no")
    private Integer floorNo;

    @Column(name = "building_name", length = 255)
    private String buildingName;

    @Column(name = "built_year")
    private Integer builtYear;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}
