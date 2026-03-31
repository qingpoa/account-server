package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.StatMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.stat.StatOverviewVO;
import com.qingpo.service.StatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Service
public class StatServiceImpl implements StatService {

    @Autowired
    private StatMapper statMapper;

    @Override
    public StatOverviewVO overview(Long userId, LocalDateTime startTime, LocalDateTime endTime) {
        if(userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");

        if (startTime == null) {
            startTime = LocalDate.now().withDayOfMonth(1).atStartOfDay();
        }
        if (endTime == null) {
            endTime = LocalDateTime.now();
        }
        if (startTime.isAfter(endTime)) {
            throw new BusinessException(Result.BAD_REQUEST, "开始时间不能晚于结束时间");
        }
        StatOverviewVO overviewVO = statMapper.overview(userId, startTime, endTime);
        if(overviewVO != null) {
            overviewVO.setBalance(overviewVO.getTotalIncome().subtract(overviewVO.getTotalExpense()));
        }

        return overviewVO;
    }
}
