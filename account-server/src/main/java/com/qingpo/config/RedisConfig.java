package com.qingpo.config;

public class RedisConfig {
    public static final String LOGIN_USER_KEY = "user:token:";
    public static final Long LOGIN_USER_TTL = 1L;

    public static final String USER_TO_TOKEN_KEY = "user:tokens:";
    public static final Long USER_TO_TOKEN_TTL = 5L;

    public static final String CATEGORY_LIST_KEY = "category:list:";
    public static final Long CATEGORY_LIST_TTL = 6L;

    public static final String USER_STAT_VERSION_KEY = "cache:v:user:";
    public static final String STAT_OVERVIEW_KEY = "stat:overview:";
    public static final String STAT_CATEGORY_KEY = "stat:category:";
    public static final String STAT_MONTHLY_KEY = "stat:monthly:";
    public static final String STAT_BUDGET_KEY = "stat:budget:";
    public static final Long STAT_CACHE_TTL = 5L;

}
