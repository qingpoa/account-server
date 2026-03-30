package com.qingpo.pojo.bill;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 新增账单返回对象。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class BillSaveVO {
    private Long id;
    private String overspendAlert;
}
