package com.qingpo.pojo.budget;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class BudgetProgressVO {
    private BigDecimal totalBudget;
    private BigDecimal totalUsed;
    private BigDecimal totalRemain;
    private Integer overspendCount;
    private List<BudgetListVO> categoryProgress;
}
