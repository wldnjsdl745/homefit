package com.homefit.region.repository;

import com.homefit.region.entity.RegionCommute;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;

public interface RegionCommuteRepository extends JpaRepository<RegionCommute, Long> {

    List<RegionCommute> findBySigunguInAndDestinationKey(Collection<String> sigungus, String destinationKey);
}
