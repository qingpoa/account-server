package com.qingpo.pojo.budget;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 分类已使用金额汇总对象。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BudgetUsedVO {
    private Long categoryId;
    private BigDecimal usedAmount;
}
