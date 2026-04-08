package com.qingpo.interceptor;

import com.qingpo.context.UserContext;
import com.qingpo.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.jspecify.annotations.NonNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;


@Component
public class LoginCheckInterceptor implements HandlerInterceptor {


    @Autowired
    private AuthService authService;

    @Override
    public boolean preHandle(HttpServletRequest request, @NonNull HttpServletResponse response, @NonNull Object handler) {
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }
        String authorization = request.getHeader("Authorization");
        if (authorization == null || authorization.isBlank()) {
            authorization = request.getHeader("token");
        }
        Long userId = authService.getUserIdByToken(authorization);
        UserContext.setCurrentUserId(userId);
        return true;
    }

    @Override
    public void afterCompletion(@NonNull HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        UserContext.clear();
    }
}
