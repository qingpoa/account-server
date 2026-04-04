package com.qingpo.service.impl;

import com.qingpo.config.RedisConfig;
import com.qingpo.context.UserContext;
import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import com.qingpo.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

@Service
public class AuthServiceImpl implements AuthService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Override
    public Long getUserIdByToken(String authorization) {
        if (authorization == null || authorization.isBlank()) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        String token = authorization.trim();
        if (token.regionMatches(true, 0, "Bearer ", 0, 7)) {
            token = token.substring(7).trim();
        }
        if (token.length() >= 2 && token.startsWith("\"") && token.endsWith("\"")) {
            token = token.substring(1, token.length() - 1).trim();
        }
        if (token.isEmpty()) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }

        try {
            String tokenKey = RedisConfig.LOGIN_USER_KEY + token;
            String userId_str = stringRedisTemplate.opsForValue().get(tokenKey);
            Long TTL = stringRedisTemplate.getExpire(tokenKey, TimeUnit.MINUTES);
            if (userId_str == null) {
                throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
            }
            if (TTL < 30) {
                stringRedisTemplate.expire(tokenKey, RedisConfig.LOGIN_USER_TTL, TimeUnit.HOURS);
                stringRedisTemplate.expire(RedisConfig.USER_TO_TOKEN_KEY + userId_str, RedisConfig.USER_TO_TOKEN_TTL, TimeUnit.HOURS);
            }
            UserContext.setCurrentUserToken(token);
            return Long.parseLong(userId_str);
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
    }
}
