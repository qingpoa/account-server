package com.qingpo.mapper;

import com.qingpo.pojo.budget.BudgetListVO;
import com.qingpo.pojo.budget.BudgetUsedVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface BudgetMapper {

    List<BudgetListVO> list(Long userId, Integer cycle);

    List<BudgetUsedVO> sumUsedAmountByCategory(@Param("userId") Long userId,
                                               @Param("categoryIds") List<Long> categoryIds,
                                               @Param("startTime") LocalDateTime startTime,
                                               @Param("endTime") LocalDateTime endTime);
}
