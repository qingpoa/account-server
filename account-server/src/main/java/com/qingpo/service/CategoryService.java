package com.qingpo.service;

import com.qingpo.pojo.category.SystemCategory;

import java.util.List;

public interface CategoryService {

    // 获取系统预设分类列表
    List<SystemCategory> list(Integer type);
}
