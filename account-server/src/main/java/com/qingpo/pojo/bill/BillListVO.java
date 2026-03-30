package com.qingpo.pojo.bill;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 账单列表项返回对象。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BillListVO {
    private Long id;
    private BigDecimal amount;
    private Integer type;
    private String categoryName;
    private String remark;
    private LocalDateTime recordTime;
    private Integer isAiGenerated;
}
