package com.qingpo.utils;

import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

import javax.crypto.SecretKey;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;


public class JwtUtils {

    private static final long EXPIRE_TIME = 60 * 60 * 1000L;
    private static final String SECRET = "account-project-jwt-secret-key-2026-safe";
    private static final SecretKey SECRET_KEY =
            Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));

    private JwtUtils() {
    }
    
    // 生成JWT
    public static String generateJwt(Map<String, Object> payload) {
        Date now = new Date();
        Date expireDate = new Date(now.getTime() + EXPIRE_TIME);

        return Jwts.builder()
                .claims(new HashMap<>(payload))
                .issuedAt(now)
                .expiration(expireDate)
                .signWith(SECRET_KEY)
                .compact();
    }
    // 解析JWT
    public static Map<String, Object> parseJwt(String token) {
        Claims claims = Jwts.parser()
                .verifyWith(SECRET_KEY)
                .build()
                .parseSignedClaims(token)
                .getPayload();

        return new HashMap<>(claims);
    }
}
