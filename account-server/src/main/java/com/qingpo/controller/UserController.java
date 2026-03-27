package com.qingpo.controller;

import com.qingpo.context.UserContext;
import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.user.User;
import com.qingpo.pojo.user.UserLoginV;
import com.qingpo.service.UserService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/user")
public class UserController {

    @Autowired
    private UserService userService;
    // 获取用户信息
    @GetMapping("/info")
    public ResponseEntity<Result> getUserInfo() {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(userService.getUserInfo(userId)));
    }
    // 用户登录
    @PostMapping("/login")
    public ResponseEntity<Result> login(@RequestBody User user) {
        if (user == null
                || user.getUsername() == null || user.getUsername().isBlank()
                || user.getPassword() == null || user.getPassword().isBlank()) {
            return response(Result.BAD_REQUEST, Result.error(Result.BAD_REQUEST, "用户名或密码不能为空"));
        }
        log.info("正在请求用户登录: username={}", user.getUsername());
        UserLoginV login = userService.login(user);
        if (login != null) {
            return response(Result.SUCCESS, Result.success(login));
        }
        return response(Result.BAD_REQUEST, Result.error(Result.BAD_REQUEST, "用户名或密码错误"));
    }

    // 用户注册
    @PostMapping("/register")
    public ResponseEntity<Result> register(@RequestBody User user) {
        if (user == null
                || user.getUsername() == null || user.getUsername().isBlank()
                || user.getPassword() == null || user.getPassword().isBlank()) {
            return response(Result.BAD_REQUEST, Result.error(Result.BAD_REQUEST, "用户名或密码不能为空"));
        }
        return response(Result.SUCCESS, Result.success(userService.register(user)));

    }



    private ResponseEntity<Result> response(Integer status, Result result) {
        return ResponseEntity.status(status).body(result);
    }
}
