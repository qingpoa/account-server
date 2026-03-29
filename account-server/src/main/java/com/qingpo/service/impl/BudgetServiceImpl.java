package com.qingpo.service.impl;

import com.qingpo.mapper.BudgetMapper;
import com.qingpo.pojo.budget.BudgetListVO;
import com.qingpo.pojo.budget.BudgetUsedVO;
import com.qingpo.service.BudgetService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class BudgetServiceImpl implements BudgetService {

    @Autowired
    private BudgetMapper budgetMapper;
    @Override
    public List<BudgetListVO> list(Long userId, Integer cycle) {
        if (cycle != null && cycle != 1 && cycle != 2 && cycle != 3) {
            throw new IllegalArgumentException("参数错误");
        }
        List<BudgetListVO> budgetListVOList = budgetMapper.list(userId, cycle);
        if (budgetListVOList == null || budgetListVOList.isEmpty()) {
            return Collections.emptyList();
        }

        Map<Integer, List<BudgetListVO>> groupedBudgetMap = budgetListVOList.stream()
                .collect(Collectors.groupingBy(BudgetListVO::getBudgetCycle));

        for (Map.Entry<Integer, List<BudgetListVO>> entry : groupedBudgetMap.entrySet()) {
            Integer budgetCycle = entry.getKey();
            List<BudgetListVO> currentCycleBudgetList = entry.getValue();
            LocalDateTime[] timeRange = getCurrentCycleTimeRange(budgetCycle);
            List<Long> categoryIds = currentCycleBudgetList.stream()
                    .map(BudgetListVO::getCategoryId)
                    .distinct()
                    .toList();

            List<BudgetUsedVO> currentCycleUsedList = budgetMapper.sumUsedAmountByCategory(
                    userId,
                    categoryIds,
                    timeRange[0],
                    timeRange[1]
            );
            Map<Long, BigDecimal> currentCycleUsedMap = currentCycleUsedList.stream()
                    .collect(Collectors.toMap(
                            BudgetUsedVO::getCategoryId,
                            BudgetUsedVO::getUsedAmount
                    ));

            for (BudgetListVO budget : currentCycleBudgetList) {
                BigDecimal usedAmount = currentCycleUsedMap.getOrDefault(
                        budget.getCategoryId(),
                        BigDecimal.ZERO
                );
                BigDecimal budgetAmount = budget.getBudgetAmount();
                BigDecimal remainAmount = budgetAmount.subtract(usedAmount);
                BigDecimal progress = BigDecimal.ZERO;

                if (budgetAmount.compareTo(BigDecimal.ZERO) > 0) {
                    progress = usedAmount
                            .multiply(BigDecimal.valueOf(100))
                            .divide(budgetAmount, 2, java.math.RoundingMode.HALF_UP);
                }

                budget.setUsedAmount(usedAmount);
                budget.setRemainAmount(remainAmount);
                budget.setProgress(progress);
            }
        }

        return budgetListVOList;
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
            default -> throw new IllegalArgumentException("预算周期参数错误");
        }

        return new LocalDateTime[]{startDate.atStartOfDay(), endDate.atStartOfDay()};
    }
}

