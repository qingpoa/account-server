package com.qingpo.controller;

import com.qingpo.pojo.Result;
import com.qingpo.pojo.User;
import com.qingpo.pojo.UserLoginV;
import com.qingpo.service.AuthService;
import com.qingpo.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.apache.el.parser.Token;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/user")
public class UserController {

    @Autowired
    private UserService userService;

    @Autowired
    private AuthService authService;

    //获取用户信息（只返回部分字段）
    @GetMapping("/info")
    public Result getUserInfo(HttpServletRequest request) {
        String authorization = request.getHeader("Authorization");
        if (authorization == null || authorization.isBlank()) {
            authorization = request.getHeader("token");
        }
        Long userId = authService.getUserIdByToken(authorization);
        return Result.success(userService.getUserInfo(userId));
    }

    @PostMapping("/login")
    public Result login(@RequestBody User user) {
        log.info("正在请求用户登录:{}", user);
        if (user == null) {
            return Result.error("用户名或密码不能为空");
        }
        UserLoginV login = userService.login(user);
        if (login != null) {
            return Result.success(login);
        }else {
            return Result.error(400,"用户名或密码错误");
        }
    }

}
