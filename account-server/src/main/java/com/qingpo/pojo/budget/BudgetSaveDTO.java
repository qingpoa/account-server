package com.qingpo.pojo.budget;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class BudgetSaveDTO {
    private Long categoryId;
    private Integer budgetCycle;
    private BigDecimal budgetAmount;
}
