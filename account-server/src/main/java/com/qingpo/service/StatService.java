package com.qingpo.service;

import com.qingpo.pojo.stat.StatOverviewVO;

import java.time.LocalDateTime;

public interface StatService {
    StatOverviewVO overview(Long userId, LocalDateTime startTime, LocalDateTime endTime);
}
