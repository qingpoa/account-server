package com.qingpo.pojo.bill;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;

import java.time.LocalDateTime;

/**
 * 账单列表查询参数。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BillQueryDTO {
    private Integer pageNum;
    private Integer pageSize;
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;
    private Integer type;
    private Long categoryId;
}
