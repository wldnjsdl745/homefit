package com.homefit.region.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "region_commute")
@Getter
@NoArgsConstructor
public class RegionCommute {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sigungu", nullable = false, length = 50)
    private String sigungu;

    @Column(name = "destination_key", nullable = false, length = 30)
    private String destinationKey;

    @Column(name = "avg_minutes", nullable = false)
    private Integer avgMinutes;
}
