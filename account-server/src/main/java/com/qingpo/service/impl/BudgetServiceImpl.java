package com.qingpo.service.impl;

import com.qingpo.annotation.OperationLog;
import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.BudgetMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.budget.BudgetConfig;
import com.qingpo.pojo.budget.BudgetListVO;
import com.qingpo.pojo.budget.BudgetProgressVO;
import com.qingpo.pojo.budget.BudgetSaveDTO;
import com.qingpo.pojo.budget.BudgetSaveVO;
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

    @Override
    public BudgetProgressVO progress(Long userId, Integer cycle) {
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        if (cycle == null || (cycle != 1 && cycle != 2 && cycle != 3)) {
            throw new BusinessException(Result.BAD_REQUEST, "预算周期参数错误");
        }
        List<BudgetListVO> categoryProgress = this.list(userId, cycle);
        BigDecimal totalBudget = BigDecimal.ZERO;
        BigDecimal totalUsed = BigDecimal.ZERO;
        BigDecimal totalRemain = BigDecimal.ZERO;
        int overspendCount = 0;

        for (BudgetListVO budget : categoryProgress) {
            totalBudget = totalBudget.add(budget.getBudgetAmount());
            totalUsed = totalUsed.add(budget.getUsedAmount());
            totalRemain = totalRemain.add(budget.getRemainAmount());
            if (budget.getRemainAmount().compareTo(BigDecimal.ZERO) < 0) {
                overspendCount++;
            }
        }

        return new BudgetProgressVO(
                totalBudget,
                totalUsed,
                totalRemain,
                overspendCount,
                categoryProgress
        );
    }

    @OperationLog(module = "BUDGET", type = "INSERT/UPDATE")
    @Override
    public BudgetSaveVO save(Long userId, BudgetSaveDTO dto) {
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        if (dto == null) {
            throw new BusinessException(Result.BAD_REQUEST, "请求参数不能为空");
        }
        if (dto.getCategoryId() == null) {
            throw new BusinessException(Result.BAD_REQUEST, "分类ID不能为空");
        }
        if (dto.getBudgetCycle() == null || (dto.getBudgetCycle() != 1 && dto.getBudgetCycle() != 2 && dto.getBudgetCycle() != 3)) {
            throw new BusinessException(Result.BAD_REQUEST, "预算周期参数错误");
        }
        if (dto.getBudgetAmount() == null) {
            throw new BusinessException(Result.BAD_REQUEST, "预算金额不能为空");
        }
        if (dto.getBudgetAmount().compareTo(BigDecimal.ZERO) <= 0) {
            throw new BusinessException(Result.BAD_REQUEST, "预算金额必须大于0");
        }
        Integer categoryCount = budgetMapper.countCategoryById(dto.getCategoryId());
        if (categoryCount == null || categoryCount == 0) {
            throw new BusinessException(Result.BAD_REQUEST, "分类不存在");
        }
        BudgetConfig existingBudget = budgetMapper.findByUserIdAndCategoryIdAndCycle(
                userId,
                dto.getCategoryId(),
                dto.getBudgetCycle()
        );
        if (existingBudget != null) {
            int rows;
            if (existingBudget.getIsDeleted() != null && existingBudget.getIsDeleted() == 1) {
                rows = budgetMapper.restoreAndUpdateBudget(existingBudget.getId(), userId, dto.getBudgetAmount());
            } else {
                rows = budgetMapper.updateBudgetAmount(existingBudget.getId(), userId, dto.getBudgetAmount());
            }
            if (rows == 0) {
                throw new BusinessException(Result.SERVER_ERROR, "预算更新失败");
            }
            return new BudgetSaveVO(existingBudget.getId());
        }

        BudgetConfig budgetConfig = new BudgetConfig();
        budgetConfig.setUserId(userId);
        budgetConfig.setCategoryId(dto.getCategoryId());
        budgetConfig.setBudgetCycle(dto.getBudgetCycle());
        budgetConfig.setBudgetAmount(dto.getBudgetAmount());
        budgetConfig.setIsDeleted(0);

        int rows = budgetMapper.insertBudget(budgetConfig);
        if (rows == 0 || budgetConfig.getId() == null) {
            throw new BusinessException(Result.SERVER_ERROR, "预算保存失败");
        }
        return new BudgetSaveVO(budgetConfig.getId());
    }

    @OperationLog(module = "BUDGET", type = "DELETE")
    @Override
    public void delete(Long userId, Long id) {
        if (userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        if (id == null)
            throw new BusinessException(Result.BAD_REQUEST, "参数不能为空");
        BudgetConfig budgetConfig = budgetMapper.findByIdAndUserId(userId, id);
        if (budgetConfig == null)
            throw new BusinessException(Result.NOT_FOUND, "预算不存在");
        int row = budgetMapper.delete(userId, id);
        if (row == 0)
            throw new BusinessException(Result.SERVER_ERROR, "预算删除失败");
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
