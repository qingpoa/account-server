package com.qingpo.pojo.budget;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 预算配置实体类，对应 budget_config 表。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BudgetConfig {
    private Long id;
    private Long userId;
    private Long categoryId;
    private Integer budgetCycle;
    private BigDecimal budgetAmount;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private Integer isDeleted;
}
