package com.homefit.region.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Entity
@Table(name = "region_jeonse_safety")
@Getter
@NoArgsConstructor
public class RegionJeonseSafety {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sigungu", nullable = false, unique = true, length = 50)
    private String sigungu;

    @Column(name = "accident_rate", nullable = false)
    private Double accidentRate;

    @Column(name = "safety_grade", nullable = false, length = 1)
    private String safetyGrade;

    @Column(name = "reference_date", nullable = false)
    private LocalDate referenceDate;
}
