package com.qingpo.service.impl;

import com.qingpo.annotation.OperationLog;
import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.BillMapper;
import com.qingpo.pojo.PageResult;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.budget.BudgetConfig;
import com.qingpo.pojo.bill.Bill;
import com.qingpo.pojo.bill.BillListVO;
import com.qingpo.pojo.bill.BillQueryDTO;
import com.qingpo.pojo.bill.BillSaveDTO;
import com.qingpo.pojo.bill.BillSaveVO;
import com.qingpo.pojo.category.SystemCategory;
import com.qingpo.service.BillService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

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

    @Override
    public void update(Long userId, Long id, BillSaveDTO dto) {
        if (userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        if (id == null)
            throw new BusinessException(Result.BAD_REQUEST, "ID不能为空");
        Bill bill = billMapper.getById(id,userId);

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
