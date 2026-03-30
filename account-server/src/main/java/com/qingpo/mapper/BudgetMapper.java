package com.qingpo.mapper;

import com.qingpo.pojo.budget.BudgetConfig;
import com.qingpo.pojo.budget.BudgetListVO;
import com.qingpo.pojo.budget.BudgetUsedVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface BudgetMapper {

    List<BudgetListVO> list(Long userId, Integer cycle);

    Integer countCategoryById(@Param("categoryId") Long categoryId);

    BudgetConfig findByUserIdAndCategoryIdAndCycle(@Param("userId") Long userId,
                                                   @Param("categoryId") Long categoryId,
                                                   @Param("budgetCycle") Integer budgetCycle);

    int insertBudget(BudgetConfig budgetConfig);

    int updateBudgetAmount(@Param("id") Long id,
                           @Param("userId") Long userId,
                           @Param("budgetAmount") java.math.BigDecimal budgetAmount);

    int restoreAndUpdateBudget(@Param("id") Long id,
                               @Param("userId") Long userId,
                               @Param("budgetAmount") java.math.BigDecimal budgetAmount);

    List<BudgetUsedVO> sumUsedAmountByCategory(@Param("userId") Long userId,
                                               @Param("categoryIds") List<Long> categoryIds,
                                               @Param("startTime") LocalDateTime startTime,
                                               @Param("endTime") LocalDateTime endTime);

    @Select("select * from budget_config where id = #{id} and user_id = #{userId} and is_deleted = 0")
    BudgetConfig findByIdAndUserId(@Param("userId") Long userId, @Param("id") Long id);

    @Update("update budget_config set is_deleted = 1 where id = #{id} and user_id = #{userId} and is_deleted = 0")
    int delete(@Param("userId") Long userId, @Param("id") Long id);
}
