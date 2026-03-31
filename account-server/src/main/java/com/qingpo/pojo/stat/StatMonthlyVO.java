package com.qingpo.pojo.stat;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class StatMonthlyVO {
    private String month;
    private BigDecimal income;
    private BigDecimal expense;
}
