package com.qingpo.service;

import com.qingpo.pojo.stat.StatCategoryVO;
import com.qingpo.pojo.stat.StatOverviewVO;

import java.time.LocalDateTime;
import java.util.List;

public interface StatService {
    StatOverviewVO overview(Long userId, LocalDateTime startTime, LocalDateTime endTime);

    List<StatCategoryVO> category(Long userId, Integer type, LocalDateTime startTime, LocalDateTime endTime);
}
