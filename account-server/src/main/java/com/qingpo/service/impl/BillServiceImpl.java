package com.qingpo.service.impl;

import com.qingpo.annotation.OperationLog;
import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.BillMapper;
import com.qingpo.pojo.PageResult;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.bill.*;
import com.qingpo.pojo.budget.BudgetConfig;
import com.qingpo.pojo.category.SystemCategory;
import com.qingpo.service.BillService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

@Service
public class BillServiceImpl implements BillService {

    @Autowired
    private BillMapper billMapper;


    @Override
    public PageResult<BillListVO> list(Long userId, BillQueryDTO dto) {

        if (userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        if (dto == null)
            throw new BusinessException(Result.BAD_REQUEST, "请求参数不能为空");
        if (dto.getPageNum() == null || dto.getPageSize() == null || dto.getPageNum() < 1 || dto.getPageSize() < 1)
            throw new BusinessException(Result.BAD_REQUEST, "页码和页大小不能为空且必须大于0");
        if (dto.getType() != null && dto.getType() != 1 && dto.getType() != 2)
            throw new BusinessException(Result.BAD_REQUEST, "账单类型参数错误");
        Long total = billMapper.count(userId, dto);
        int offset = (dto.getPageNum() - 1) * dto.getPageSize();
        return new PageResult<>(total, billMapper.list(userId, dto, offset, dto.getPageSize()));
    }

    @OperationLog(module = "BILL", type = "INSERT")
    @Override
    public BillSaveVO save(Long userId, BillSaveDTO dto) {
        if (userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        if (dto == null)
            throw new BusinessException(Result.BAD_REQUEST, "请求参数不能为空");
        if (dto.getCategoryId() == null)
            throw new BusinessException(Result.BAD_REQUEST, "分类ID不能为空");
        if (dto.getAmount() == null || dto.getAmount().compareTo(BigDecimal.ZERO) <= 0)
            throw new BusinessException(Result.BAD_REQUEST, "金额必须大于0");
        if (dto.getType() == null || (dto.getType() != 1 && dto.getType() != 2))
            throw new BusinessException(Result.BAD_REQUEST, "账单类型参数错误");
        if (dto.getRecordTime() == null)
            dto.setRecordTime(LocalDateTime.now());
        if (dto.getIsAiGenerated() == null)
            dto.setIsAiGenerated(0);
        Integer categoryCount = billMapper.countCategoryById(dto.getCategoryId());
        if (categoryCount == null || categoryCount == 0)
            throw new BusinessException(Result.BAD_REQUEST, "分类不存在");
        SystemCategory category = billMapper.getCategoryById(dto.getCategoryId());
        if (category == null || category.getType() == null || !category.getType().equals(dto.getType()))
            throw new BusinessException(Result.BAD_REQUEST, "账单类型与分类类型不一致");

        Bill bill = new Bill();
        bill.setUserId(userId);
        bill.setCategoryId(dto.getCategoryId());
        bill.setAmount(dto.getAmount());
        bill.setType(dto.getType());
        bill.setRemark(dto.getRemark());
        bill.setRecordTime(dto.getRecordTime());
        bill.setIsAiGenerated(dto.getIsAiGenerated());
        bill.setIsDeleted(0);

        int rows = billMapper.insertBill(bill);
        if (rows == 0 || bill.getId() == null)
            throw new BusinessException(Result.SERVER_ERROR, "新增账单失败");

        String overspendAlert = buildOverspendAlert(userId, category, bill);
        return new BillSaveVO(bill.getId(), overspendAlert);
    }

    @OperationLog(module = "BILL", type = "UPDATE")
    @Override
    public void update(Long userId, Long id, BillUpdateDTO dto) {
        if (userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        if (id == null)
            throw new BusinessException(Result.BAD_REQUEST, "ID不能为空");
        if (dto == null)
            return;
        if (dto.getCategoryId() == null && dto.getAmount() == null && dto.getRemark() == null && dto.getRecordTime() == null) {
            return;
        }
        Bill bill = billMapper.getById(id, userId);
        if (dto.getAmount() != null && dto.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
            throw new BusinessException(Result.BAD_REQUEST, "金额必须大于0");
        }
        if (dto.getCategoryId() != null) {
            SystemCategory category = billMapper.getCategoryById(dto.getCategoryId());
            if (category == null) {
                throw new BusinessException(Result.BAD_REQUEST, "分类不存在");
            }
            if (category.getType() == null || !category.getType().equals(bill.getType())) {
                throw new BusinessException(Result.BAD_REQUEST, "账单类型与分类类型不一致");
            }
        }
        if (isUnchanged(dto, bill)) {
            return;
        }

        int row = billMapper.update(id, userId, dto);
        if (row == 0) {
            throw new BusinessException(Result.SERVER_ERROR, "更新账单失败");
        }


    }

    @OperationLog(module = "BILL", type = "DELETE")
    @Override
    public void delete(Long userId, Long id) {
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        if (id == null) {
            throw new BusinessException(Result.BAD_REQUEST, "ID不能为空");
        }

        Bill bill = billMapper.getById(id, userId);
        if (bill == null) {
            throw new BusinessException(Result.NOT_FOUND, "账单不存在");
        }

        int rows = billMapper.delete(id, userId);
        if (rows == 0) {
            throw new BusinessException(Result.SERVER_ERROR, "账单删除失败");
        }

    }




    private static boolean isUnchanged(BillUpdateDTO dto, Bill bill) {
        if (bill == null) {
            throw new BusinessException(Result.NOT_FOUND, "账单不存在");
        }

        Long targetCategoryId = dto.getCategoryId() != null ? dto.getCategoryId() : bill.getCategoryId();
        BigDecimal targetAmount = dto.getAmount() != null ? dto.getAmount() : bill.getAmount();
        String targetRemark = dto.getRemark() != null ? dto.getRemark() : bill.getRemark();
        LocalDateTime targetRecordTime = dto.getRecordTime() != null ? dto.getRecordTime() : bill.getRecordTime();

        return bill.getCategoryId().equals(targetCategoryId)
                        && bill.getAmount().compareTo(targetAmount) == 0
                        && Objects.equals(bill.getRemark(), targetRemark)
                        && bill.getRecordTime().equals(targetRecordTime);
    }

    private String buildOverspendAlert(Long userId, SystemCategory category, Bill bill) {
        if (bill.getType() == null || bill.getType() != 2) {
            return null;
        }

        List<BudgetConfig> budgets = billMapper.listActiveBudgetsByUserIdAndCategoryId(userId, bill.getCategoryId());
        if (budgets == null || budgets.isEmpty()) {
            return null;
        }

        List<String> alerts = new ArrayList<>();
        for (BudgetConfig budget : budgets) {
            LocalDateTime[] timeRange = getCycleTimeRange(budget.getBudgetCycle(), bill.getRecordTime());
            BigDecimal usedAmount = billMapper.sumExpenseByCategoryAndTimeRange(
                    userId,
                    bill.getCategoryId(),
                    timeRange[0],
                    timeRange[1]
            );
            if (usedAmount == null) {
                usedAmount = BigDecimal.ZERO;
            }

            BigDecimal budgetAmount = budget.getBudgetAmount();
            if (budgetAmount == null || budgetAmount.compareTo(BigDecimal.ZERO) <= 0) {
                continue;
            }

            String cycleLabel = getCycleLabel(budget.getBudgetCycle());
            if (usedAmount.compareTo(budgetAmount) >= 0) {
                alerts.add(category.getName() + cycleLabel + "预算已超支");
            } else {
                BigDecimal warningLine = budgetAmount.multiply(new BigDecimal("0.8"));
                if (usedAmount.compareTo(warningLine) >= 0) {
                    alerts.add(category.getName() + cycleLabel + "预算已使用80%以上");
                }
            }
        }

        if (alerts.isEmpty()) {
            return null;
        }
        return String.join("；", alerts);
    }

    private LocalDateTime[] getCycleTimeRange(Integer budgetCycle, LocalDateTime recordTime) {
        LocalDate baseDate = recordTime.toLocalDate();
        LocalDate startDate;
        LocalDate endDate;

        switch (budgetCycle) {
            case 1 -> {
                startDate = baseDate.withDayOfMonth(1);
                endDate = startDate.plusMonths(1);
            }
            case 2 -> {
                int startMonth = ((baseDate.getMonthValue() - 1) / 3) * 3 + 1;
                startDate = LocalDate.of(baseDate.getYear(), startMonth, 1);
                endDate = startDate.plusMonths(3);
            }
            case 3 -> {
                startDate = LocalDate.of(baseDate.getYear(), 1, 1);
                endDate = startDate.plusYears(1);
            }
            default -> throw new BusinessException(Result.BAD_REQUEST, "预算周期参数错误");
        }

        return new LocalDateTime[]{startDate.atStartOfDay(), endDate.atStartOfDay()};
    }

    private String getCycleLabel(Integer budgetCycle) {
        return switch (budgetCycle) {
            case 1 -> "月度";
            case 2 -> "季度";
            case 3 -> "年度";
            default -> "未知周期";
        };
    }
}
