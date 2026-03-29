package com.qingpo.service;

import com.qingpo.pojo.budget.BudgetListVO;
import com.qingpo.pojo.budget.BudgetSaveDTO;
import com.qingpo.pojo.budget.BudgetSaveVO;

import java.util.List;

public interface BudgetService {
    List<BudgetListVO> list(Long userId, Integer cycle);

    BudgetSaveVO save(Long userId, BudgetSaveDTO dto);
}
