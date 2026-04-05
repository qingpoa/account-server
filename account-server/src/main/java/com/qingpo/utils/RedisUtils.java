package com.qingpo.utils;

import cn.hutool.core.lang.TypeReference;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class RedisUtils {
    private final StringRedisTemplate stringRedisTemplate;

    public RedisUtils(StringRedisTemplate stringRedisTemplate) {
        this.stringRedisTemplate = stringRedisTemplate;
    }

    public void set(String key, Object value, long timeout, TimeUnit unit) {
        stringRedisTemplate.opsForValue().set(key, JSONUtil.toJsonStr( value), timeout, unit);
    }

    public void set(String key, String value, long timeout, TimeUnit unit) {
        stringRedisTemplate.opsForValue().set(key, value, timeout, unit);
    }


    public void delete(String key) {
        stringRedisTemplate.delete(key);
    }

    public <T> T get(String key, Class<T> clazz) {
        String value = stringRedisTemplate.opsForValue().get(key);
        if (StrUtil.isBlank( value)) {
            return null;
        }
        return JSONUtil.toBean(value, clazz);
    }

    public <T> T get(String key, TypeReference< T> clazz) {
        String value = stringRedisTemplate.opsForValue().get(key);
        if (StrUtil.isBlank( value)) {
            return null;
        }
        return JSONUtil.toBean(value, clazz, false);
    }

    public String get(String key) {
        String value = stringRedisTemplate.opsForValue().get(key);
        if (StrUtil.isBlank( value)) {
            return null;
        }
        return value;
    }

    public Long increment(String key) {
        return stringRedisTemplate.opsForValue().increment(key);
    }

    public boolean expire(String key, long timeout, TimeUnit unit) {
        Boolean result = stringRedisTemplate.expire(key, timeout, unit);
        return Boolean.TRUE.equals(result);
    }
}
