package com.qingpo.controller;

import com.qingpo.pojo.Result;
import org.springframework.http.ResponseEntity;

/**
 * 控制层公共父类，统一封装响应结果。
 */
public abstract class BaseController {

    protected ResponseEntity<Result> response(Integer status, Result result) {
        return ResponseEntity.status(status).body(result);
    }
}
