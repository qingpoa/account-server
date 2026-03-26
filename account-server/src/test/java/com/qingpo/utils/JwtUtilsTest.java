package com.qingpo.utils;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.Test;

import io.jsonwebtoken.JwtException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.test.context.SpringBootTest;

@Slf4j
@SpringBootTest
class JwtUtilsTest {

    @Test
    void shouldGenerateAndParseJwtSuccessfully() {
        Map<String, Object> payload = new HashMap<>();
        payload.put("userId", 1L);
        payload.put("username", "qingpo");
        String token = JwtUtils.generateJwt(payload);
        log.info(token);
        Map<String, Object> parsedClaims = JwtUtils.parseJwt(token);
        log.info("结果 {}",parsedClaims);
        assertNotNull(token);
        assertEquals(1, ((Number) parsedClaims.get("userId")).intValue());
        assertEquals("qingpo", parsedClaims.get("username"));
    }

    @Test
    void shouldSetExpirationToOneHour() {
        Map<String, Object> payload = new HashMap<>();
        payload.put("userId", 1001L);

        String token = JwtUtils.generateJwt(payload);
        Map<String, Object> parsedClaims = JwtUtils.parseJwt(token);

        long issuedAt = ((Number) parsedClaims.get("iat")).longValue();
        long expiration = ((Number) parsedClaims.get("exp")).longValue();
        long duration = expiration - issuedAt;

        assertEquals(60 * 60L, duration);
    }

    @Test
    void shouldThrowExceptionWhenTokenIsTampered() {
        Map<String, Object> payload = new HashMap<>();
        payload.put("userId", 2L);

        String token = JwtUtils.generateJwt(payload);
        String tamperedToken = token.substring(0, token.lastIndexOf('.'));

        assertThrows(JwtException.class, () -> JwtUtils.parseJwt(tamperedToken));
    }

    @Test
    void shouldContainStandardClaims() {
        Map<String, Object> payload = new HashMap<>();
        payload.put("role", "user");

        String token = JwtUtils.generateJwt(payload);
        Map<String, Object> parsedClaims = JwtUtils.parseJwt(token);

        assertEquals("user", parsedClaims.get("role"));
        assertTrue(parsedClaims.containsKey("iat"));
        assertTrue(parsedClaims.containsKey("exp"));
    }
}
