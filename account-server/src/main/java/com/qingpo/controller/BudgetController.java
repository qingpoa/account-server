package com.qingpo.controller;


import com.qingpo.context.UserContext;
import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.budget.BudgetSaveDTO;
import com.qingpo.service.BudgetService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/budget")
public class BudgetController extends BaseController {

    @Autowired
    private BudgetService budgetService;

    // 获取预算列表
    @GetMapping("/list")
    public ResponseEntity<Result> list(@RequestParam(required = false) Integer cycle) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(budgetService.list(userId, cycle)));
    }

    // 获取预算进度统计
    @GetMapping("/progress")
    public ResponseEntity<Result> progress(@RequestParam Integer cycle) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(budgetService.progress(userId, cycle)));
    }

    // 保存或修改预算
    @PostMapping
    public ResponseEntity<Result> save(@RequestBody BudgetSaveDTO dto) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(budgetService.save(userId, dto)));
    }

    // 删除预算
    @DeleteMapping("/{id}")
    public ResponseEntity<Result> delete(@PathVariable Long id) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        budgetService.delete(userId, id);
        return response(Result.SUCCESS, Result.success());
    }

}
