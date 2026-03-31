package com.qingpo.pojo.stat;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class StatCategoryVO {
    private String categoryName;
    private BigDecimal amount;
    private BigDecimal proportion;
}
