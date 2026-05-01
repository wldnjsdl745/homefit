package com.homefit.chat.backend.region.repository;

import com.homefit.chat.backend.region.entity.Region;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface RegionRepository extends JpaRepository<Region, Long> {

    Optional<Region> findBySidoAndSigunguCodeAndLegalDongCode(
            String sido,
            String sigunguCode,
            String legalDongCode
    );
}
