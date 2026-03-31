package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.StatMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.stat.StatCategoryVO;
import com.qingpo.pojo.stat.StatOverviewVO;
import com.qingpo.service.StatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

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

    @Override
    public List<StatCategoryVO> category(Long userId, Integer type, LocalDateTime startTime, LocalDateTime endTime) {
        if(userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        if (type == null || (type != 1 && type != 2)) {
            throw new BusinessException(Result.BAD_REQUEST, "统计类型参数错误");
        }

        if (startTime == null) {
            startTime = LocalDate.now().withDayOfMonth(1).atStartOfDay();
        }
        if (endTime == null) {
            endTime = LocalDateTime.now();
        }
        if (startTime.isAfter(endTime)) {
            throw new BusinessException(Result.BAD_REQUEST, "开始时间不能晚于结束时间");
        }

        List<StatCategoryVO> list = statMapper.category(userId, type, startTime, endTime);
        if(list != null && !list.isEmpty()) {
            BigDecimal total = list.stream().map(StatCategoryVO::getAmount).reduce(BigDecimal.ZERO, BigDecimal::add);
            for (StatCategoryVO item : list) {
                if (total.compareTo(BigDecimal.ZERO) > 0) {
                    item.setProportion(item.getAmount().multiply(BigDecimal.valueOf(100)).divide(total, 2, RoundingMode.HALF_UP));
                } else {
                    item.setProportion(BigDecimal.ZERO);
                }
            }
        }

        return list;
    }
}
