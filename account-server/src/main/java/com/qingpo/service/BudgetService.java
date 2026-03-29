package com.qingpo.service;

import com.qingpo.pojo.budget.BudgetListVO;

import java.util.List;

public interface BudgetService {
    List<BudgetListVO> list(Long userId, Integer cycle);
}
