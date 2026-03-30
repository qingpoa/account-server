package com.qingpo.pojo.bill;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 账单实体类，对应 bill 表。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class Bill {
    private Long id;
    private Long userId;
    private Long categoryId;
    private BigDecimal amount;
    private Integer type;
    private String remark;
    private LocalDateTime recordTime;
    private Integer isAiGenerated;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private Integer isDeleted;
}
