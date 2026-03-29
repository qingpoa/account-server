package com.qingpo.pojo.budget;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class BudgetListVO {
    private Long id;
    private Long categoryId;
    private String categoryName;
    private Integer budgetCycle;
    private BigDecimal budgetAmount;
    private BigDecimal usedAmount;
    private BigDecimal remainAmount;
    private BigDecimal progress;
}
