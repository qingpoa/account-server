package com.qingpo.config;

public class RedisConfig {
    public static final String LOGIN_USER_KEY = "user:token:";
    public static final Long LOGIN_USER_TTL = 1L;
    public static final String USER_TO_TOKEN_KEY = "user:tokens:";
    public static final Long USER_TO_TOKEN_TTL = 5L;
}
