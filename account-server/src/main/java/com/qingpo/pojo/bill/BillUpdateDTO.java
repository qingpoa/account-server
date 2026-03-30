package com.qingpo.pojo.bill;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 修改账单请求参数。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BillUpdateDTO {
    private Long categoryId;
    private BigDecimal amount;
    private String remark;
    private LocalDateTime recordTime;
}
