package com.homefit.region.repository;

import com.homefit.region.entity.RegionJeonseSafety;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;

public interface RegionJeonseSafetyRepository extends JpaRepository<RegionJeonseSafety, Long> {

    List<RegionJeonseSafety> findBySigunguIn(Collection<String> sigungus);
}
