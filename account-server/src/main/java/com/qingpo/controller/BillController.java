package com.qingpo.controller;

import com.qingpo.annotation.OperationLog;
import com.qingpo.context.UserContext;
import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.bill.BillQueryDTO;
import com.qingpo.pojo.bill.BillSaveDTO;
import com.qingpo.pojo.bill.BillUpdateDTO;
import com.qingpo.service.BillService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/bill")
public class BillController extends BaseController{

    @Autowired
    private BillService billService;

    @GetMapping("/list")
    public ResponseEntity<Result> list(BillQueryDTO dto) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(billService.list(userId, dto)));
    }

    @PostMapping
    public ResponseEntity<Result> save(@RequestBody BillSaveDTO dto) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(billService.save(userId, dto)));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Result> update(@PathVariable Long id, @RequestBody BillUpdateDTO dto) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        billService.update(userId, id, dto);
        return response(Result.SUCCESS, Result.success());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Result> delete(@PathVariable Long id) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        billService.delete(userId, id);
        return response(Result.SUCCESS, Result.success());
    }

    @GetMapping("/{id}")
    public ResponseEntity<Result> detail(@PathVariable Long id) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(billService.detail(userId, id)));
    }

}
