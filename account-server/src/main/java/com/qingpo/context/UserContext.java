package com.qingpo.context;

public class UserContext {

    private static final ThreadLocal<Long> CURRENT_USER = new ThreadLocal<>();
    private static final ThreadLocal<String> CURRENT_USER_TOKEN = new ThreadLocal<>();

    private UserContext() {
    }

    public static void setCurrentUserId(Long userId) {
        CURRENT_USER.set(userId);
    }

    public static void setCurrentUserToken(String token) {
        CURRENT_USER_TOKEN.set(token);
    }

    public static Long getCurrentUserId() {
        return CURRENT_USER.get();
    }

    public static String getCurrentUserToken() {
        return CURRENT_USER_TOKEN.get();
    }

    public static void clear() {
        CURRENT_USER.remove();
        CURRENT_USER_TOKEN.remove();
    }
}
