package com.qingpo.controller;

import com.qingpo.pojo.Result;
import com.qingpo.service.CategoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Set;

@RestController
@RequestMapping("/category")
public class CategoryController {

    @Autowired
    private CategoryService categoryService;

    // 获取分类列表
    @GetMapping("/list")
    public ResponseEntity<Result> list(@RequestParam(required = false) Integer type) {
        return response(200, Result.success(categoryService.list(type)));
    }

    private ResponseEntity<Result> response(Integer status, Result result) {
        return ResponseEntity.status(status).body(result);
    }
}
