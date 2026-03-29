package com.qingpo.controller;

import com.qingpo.context.UserContext;
import com.qingpo.pojo.Result;
import com.qingpo.service.CategoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/category")
public class CategoryController extends BaseController {

    @Autowired
    private CategoryService categoryService;

    // 获取分类列表
    @GetMapping("/list")
    public ResponseEntity<Result> list(@RequestParam(required = false) Integer type) {
        return response(Result.SUCCESS, Result.success(categoryService.list(type)));
    }
}
