package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import com.qingpo.service.AuthService;
import com.qingpo.utils.JwtUtils;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class AuthServiceImpl implements AuthService {

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
            Map<String, Object> claims = JwtUtils.parseJwt(token);
            Object userId = claims.get("userId");
            if (!(userId instanceof Number number)) {
                throw new BusinessException(Result.UNAUTHORIZED, "token无效");
            }
            return number.longValue();
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
    }
}
