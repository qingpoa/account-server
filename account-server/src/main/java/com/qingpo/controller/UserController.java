package com.qingpo.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.qingpo.pojo.Result;
import com.qingpo.service.UserService;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@RestController
@RequestMapping("/user")
public class UserController {

    @Autowired
    private UserService userService;

    //获取用户信息（只返回部分字段）
    @GetMapping("/info/{id}")
    public Result getUserInfo(@PathVariable String id) {
        log.info("正在请求 id:{}", id);
        return Result.success(userService.getUserInfo(Integer.valueOf(id)));
    }

}
