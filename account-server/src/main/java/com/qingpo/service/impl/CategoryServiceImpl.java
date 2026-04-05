package com.qingpo.service.impl;

import cn.hutool.core.lang.TypeReference;
import com.qingpo.mapper.SystemCategoryMapper;
import com.qingpo.pojo.category.SystemCategory;
import com.qingpo.service.CategoryService;
import com.qingpo.utils.RedisUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.TimeUnit;

import static com.qingpo.config.RedisConfig.CATEGORY_LIST_KEY;
import static com.qingpo.config.RedisConfig.CATEGORY_LIST_TTL;

@Slf4j
@Service
public class CategoryServiceImpl implements CategoryService {

    @Autowired
    private SystemCategoryMapper systemCategoryMapper;
    @Autowired
    private RedisUtils redisUtils;

    @Override
    public List<SystemCategory> list(Integer type) {
        if (type != null && type != 1 && type != 2) {
            throw new IllegalArgumentException("参数错误");
        }

        String cacheKey = CATEGORY_LIST_KEY + (type == null ? "all" : type);
        List<SystemCategory> cache = redisUtils.get(cacheKey, new TypeReference<List<SystemCategory>>() {});
        if (cache != null) {
            log.info("从缓存中获取数据");
            return cache;
        }
        cache = systemCategoryMapper.list(type);
        redisUtils.set(cacheKey, cache, CATEGORY_LIST_TTL, TimeUnit.HOURS);
        return cache;
    }
}
