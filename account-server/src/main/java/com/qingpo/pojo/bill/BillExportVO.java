package com.qingpo.pojo.bill;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class BillExportVO {

    @ExcelProperty("账单ID")
    private Long id;

    @ExcelProperty("金额")
    private BigDecimal amount;

    @ExcelProperty("类型")
    private String typeName;

    @ExcelProperty("分类名称")
    private String categoryName;

    @ExcelProperty("备注")
    private String remark;

    @ExcelProperty("记录时间")
    private String recordTime;

    @ExcelProperty("是否AI生成")
    private String isAiGenerated;
}
