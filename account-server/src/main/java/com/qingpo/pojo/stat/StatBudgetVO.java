package com.qingpo.pojo.stat;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class StatBudgetVO {
    private String categoryName;
    private BigDecimal budgetAmount;
    private BigDecimal usedAmount;
    private BigDecimal progress;
}
