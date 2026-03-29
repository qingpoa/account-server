package com.qingpo.pojo.category;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 系统预设分类对象。
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class SystemCategory {
    private Long id;
    private String name;
    private Integer type;
    private String icon;
    private Integer sort;
}
