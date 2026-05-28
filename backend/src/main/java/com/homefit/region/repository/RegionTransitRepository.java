package com.homefit.region.repository;

import com.homefit.region.entity.RegionTransit;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;

public interface RegionTransitRepository extends JpaRepository<RegionTransit, Long> {

    List<RegionTransit> findBySigunguIn(Collection<String> sigungus);
}
