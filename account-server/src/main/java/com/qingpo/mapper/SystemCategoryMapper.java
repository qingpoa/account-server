package com.qingpo.mapper;

import com.qingpo.pojo.category.SystemCategory;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface SystemCategoryMapper {

    /**
     * 查询系统分类列表。
     *
     * @param type 分类类型，1=收入，2=支出，null=全部
     * @return 分类实体集合
     */
    List<SystemCategory> list(Integer type);
}
