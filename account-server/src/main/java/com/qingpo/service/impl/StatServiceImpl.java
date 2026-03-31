package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.BudgetMapper;
import com.qingpo.mapper.StatMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.budget.BudgetListVO;
import com.qingpo.pojo.budget.BudgetUsedVO;
import com.qingpo.pojo.stat.StatBudgetVO;
import com.qingpo.pojo.stat.StatCategoryVO;
import com.qingpo.pojo.stat.StatMonthlyVO;
import com.qingpo.pojo.stat.StatOverviewVO;
import com.qingpo.service.StatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class StatServiceImpl implements StatService {

    private static final DateTimeFormatter YEAR_MONTH_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM");

    @Autowired
    private StatMapper statMapper;

    @Autowired
    private BudgetMapper budgetMapper;

    @Override
    public StatOverviewVO overview(Long userId, LocalDateTime startTime, LocalDateTime endTime) {
        if (userId == null)
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
        if (overviewVO != null) {
            overviewVO.setBalance(overviewVO.getTotalIncome().subtract(overviewVO.getTotalExpense()));
        }

        return overviewVO;
    }

    @Override
    public List<StatCategoryVO> category(Long userId, Integer type, LocalDateTime startTime, LocalDateTime endTime) {
        if (userId == null)
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
        if (list != null && !list.isEmpty()) {
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

    @Override
    public List<StatMonthlyVO> monthly(Long userId, Integer year) {
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        if (year == null || year < 1900 || year > 9999) {
            throw new BusinessException(Result.BAD_REQUEST, "统计年份参数错误");
        }

        LocalDateTime startTime = LocalDate.of(year, 1, 1).atStartOfDay();
        LocalDateTime endTime = startTime.plusYears(1);
        List<StatMonthlyVO> dbList = statMapper.monthly(userId, startTime, endTime);
        Map<String, StatMonthlyVO> monthlyMap = dbList == null ? Collections.emptyMap() : dbList.stream()
                .collect(Collectors.toMap(StatMonthlyVO::getMonth, item -> item));

        List<StatMonthlyVO> result = new ArrayList<>();
        for (int month = 1; month <= 12; month++) {
            String monthKey = String.format("%04d-%02d", year, month);
            result.add(monthlyMap.getOrDefault(
                    monthKey,
                    new StatMonthlyVO(monthKey, BigDecimal.ZERO, BigDecimal.ZERO)
            ));
        }
        return result;
    }

    @Override
    public List<StatBudgetVO> budget(Long userId, Integer cycle, String time) {
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        if (cycle == null || (cycle != 1 && cycle != 2 && cycle != 3)) {
            throw new BusinessException(Result.BAD_REQUEST, "预算周期参数错误");
        }

        LocalDateTime[] timeRange = resolveBudgetTimeRange(cycle, time);
        List<BudgetListVO> budgetList = budgetMapper.list(userId, cycle);
        if (budgetList == null || budgetList.isEmpty()) {
            return Collections.emptyList();
        }

        List<Long> categoryIds = budgetList.stream()
                .map(BudgetListVO::getCategoryId)
                .distinct()
                .toList();

        List<BudgetUsedVO> usedList = budgetMapper.sumUsedAmountByCategory(
                userId,
                categoryIds,
                timeRange[0],
                timeRange[1]
        );
        Map<Long, BigDecimal> usedMap = usedList.stream().collect(Collectors.toMap(
                BudgetUsedVO::getCategoryId,
                BudgetUsedVO::getUsedAmount
        ));

        List<StatBudgetVO> result = new ArrayList<>();
        for (BudgetListVO budget : budgetList) {
            BigDecimal usedAmount = usedMap.getOrDefault(budget.getCategoryId(), BigDecimal.ZERO);
            BigDecimal progress = BigDecimal.ZERO;
            if (budget.getBudgetAmount().compareTo(BigDecimal.ZERO) > 0) {
                progress = usedAmount.multiply(BigDecimal.valueOf(100))
                        .divide(budget.getBudgetAmount(), 2, RoundingMode.HALF_UP);
            }
            result.add(new StatBudgetVO(
                    budget.getCategoryName(),
                    budget.getBudgetAmount(),
                    usedAmount,
                    progress
            ));
        }
        return result;
    }

    private LocalDateTime[] resolveBudgetTimeRange(Integer cycle, String time) {
        if (time == null || time.isBlank()) {
            return getCurrentCycleTimeRange(cycle);
        }

        try {
            switch (cycle) {
                case 1 -> {
                    YearMonth yearMonth = YearMonth.parse(time, YEAR_MONTH_FORMATTER);
                    LocalDate startDate = yearMonth.atDay(1);
                    return new LocalDateTime[]{startDate.atStartOfDay(), startDate.plusMonths(1).atStartOfDay()};
                }
                case 2 -> {
                    LocalDate startDate;
                    if (time.matches("\\d{4}-Q[1-4]")) {
                        int year = Integer.parseInt(time.substring(0, 4));
                        int quarter = Integer.parseInt(time.substring(6));
                        startDate = LocalDate.of(year, (quarter - 1) * 3 + 1, 1);
                    } else if (time.matches("\\d{4}-[1-4]")) {
                        int year = Integer.parseInt(time.substring(0, 4));
                        int quarter = Integer.parseInt(time.substring(5));
                        startDate = LocalDate.of(year, (quarter - 1) * 3 + 1, 1);
                    } else if (time.matches("\\d{4}-\\d{2}")) {
                        YearMonth yearMonth = YearMonth.parse(time, YEAR_MONTH_FORMATTER);
                        int startMonth = ((yearMonth.getMonthValue() - 1) / 3) * 3 + 1;
                        startDate = LocalDate.of(yearMonth.getYear(), startMonth, 1);
                    } else {
                        throw new BusinessException(Result.BAD_REQUEST, "统计时间格式错误");
                    }
                    return new LocalDateTime[]{startDate.atStartOfDay(), startDate.plusMonths(3).atStartOfDay()};
                }
                case 3 -> {
                    int year;
                    if (time.matches("\\d{4}")) {
                        year = Integer.parseInt(time);
                    } else if (time.matches("\\d{4}-\\d{2}")) {
                        year = Integer.parseInt(time.substring(0, 4));
                    } else {
                        throw new BusinessException(Result.BAD_REQUEST, "统计时间格式错误");
                    }
                    LocalDate startDate = LocalDate.of(year, 1, 1);
                    return new LocalDateTime[]{startDate.atStartOfDay(), startDate.plusYears(1).atStartOfDay()};
                }
                default -> throw new BusinessException(Result.BAD_REQUEST, "预算周期参数错误");
            }
        } catch (DateTimeParseException | NumberFormatException e) {
            throw new BusinessException(Result.BAD_REQUEST, "统计时间格式错误");
        }
    }

    private LocalDateTime[] getCurrentCycleTimeRange(Integer budgetCycle) {
        LocalDate today = LocalDate.now();
        LocalDate startDate;
        LocalDate endDate;

        switch (budgetCycle) {
            case 1 -> {
                startDate = today.withDayOfMonth(1);
                endDate = startDate.plusMonths(1);
            }
            case 2 -> {
                int startMonth = ((today.getMonthValue() - 1) / 3) * 3 + 1;
                startDate = LocalDate.of(today.getYear(), startMonth, 1);
                endDate = startDate.plusMonths(3);
            }
            case 3 -> {
                startDate = LocalDate.of(today.getYear(), 1, 1);
                endDate = startDate.plusYears(1);
            }
            default -> throw new BusinessException(Result.BAD_REQUEST, "预算周期参数错误");
        }

        return new LocalDateTime[]{startDate.atStartOfDay(), endDate.atStartOfDay()};
    }
}
