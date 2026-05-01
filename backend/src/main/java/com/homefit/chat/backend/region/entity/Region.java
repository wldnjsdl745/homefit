package com.homefit.chat.backend.region.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "regions")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Region {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sido", nullable = false, length = 50)
    private String sido;

    @Column(name = "sigungu_code", length = 10)
    private String sigunguCode;

    @Column(name = "sigungu", nullable = false, length = 50)
    private String sigungu;

    @Column(name = "legal_dong_code", length = 10))
    private String legalDongCode;

    @Column(name = "legal_dong_name", length = 50)
    private String legalDongName;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
