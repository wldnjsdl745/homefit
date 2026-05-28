package com.homefit.facility.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "nearby_facilities")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class NearbyFacility {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "source_key", nullable = false, length = 80)
    private String sourceKey;

    @Column(name = "facility_type", nullable = false, length = 40)
    private String facilityType;

    @Column(name = "subtype", length = 120)
    private String subtype;

    @Column(name = "name", nullable = false, length = 255)
    private String name;

    @Column(name = "sido", length = 50)
    private String sido;

    @Column(name = "sigungu", length = 50)
    private String sigungu;

    @Column(name = "legal_dong_name", length = 50)
    private String legalDongName;

    @Column(name = "road_address", length = 500)
    private String roadAddress;

    @Column(name = "lot_address", length = 500)
    private String lotAddress;

    @Column(name = "lat", precision = 10, scale = 7)
    private BigDecimal lat;

    @Column(name = "lng", precision = 10, scale = 7)
    private BigDecimal lng;

    @Column(name = "status", length = 80)
    private String status;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
