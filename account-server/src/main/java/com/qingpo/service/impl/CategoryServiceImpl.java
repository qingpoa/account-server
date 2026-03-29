package com.qingpo.service.impl;

import com.qingpo.mapper.SystemCategoryMapper;
import com.qingpo.pojo.category.SystemCategory;
import com.qingpo.service.CategoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CategoryServiceImpl implements CategoryService {

    @Autowired
    private SystemCategoryMapper systemCategoryMapper;

    @Override
    public List<SystemCategory> list(Integer type) {
        if (type != null && type != 1 && type != 2) {
            throw new IllegalArgumentException("参数错误");
        }
        return systemCategoryMapper.list(type);
    }
}
