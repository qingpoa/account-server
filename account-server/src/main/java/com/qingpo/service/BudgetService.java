package com.qingpo.service;

import com.qingpo.pojo.budget.BudgetListVO;
import com.qingpo.pojo.budget.BudgetProgressVO;
import com.qingpo.pojo.budget.BudgetSaveDTO;
import com.qingpo.pojo.budget.BudgetSaveVO;

import java.util.List;

public interface BudgetService {
    List<BudgetListVO> list(Long userId, Integer cycle);

    BudgetProgressVO progress(Long userId, Integer cycle);

    BudgetSaveVO save(Long userId, BudgetSaveDTO dto);

    void delete(Long userId, Long id);
}
