package com.homefit.region.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "region_transit")
@Getter
@NoArgsConstructor
public class RegionTransit {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sigungu", nullable = false, unique = true, length = 50)
    private String sigungu;

    @Column(name = "subway_count", nullable = false)
    private Integer subwayCount;

    @Column(name = "transit_score", nullable = false)
    private Double transitScore;
}
