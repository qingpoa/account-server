package com.qingpo.pojo.bill;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 账单详情返回对象。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BillDetailVO {
    private Long id;
    private BigDecimal amount;
    private Integer type;
    private Long categoryId;
    private String categoryName;
    private String remark;
    private LocalDateTime recordTime;
}
