package com.qingpo.pojo.bill;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 新增账单请求参数。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BillSaveDTO {
    private Long categoryId;
    private BigDecimal amount;
    private Integer type;
    private String remark;
    private LocalDateTime recordTime;
    private Integer isAiGenerated;
}
