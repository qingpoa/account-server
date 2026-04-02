package com.qingpo.mapper;

import com.qingpo.pojo.bill.*;
import com.qingpo.pojo.budget.BudgetConfig;
import com.qingpo.pojo.category.SystemCategory;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface BillMapper {

    Integer countCategoryById(@Param("categoryId") Long categoryId);

    SystemCategory getCategoryById(@Param("categoryId") Long categoryId);

    List<BudgetConfig> listActiveBudgetsByUserIdAndCategoryId(@Param("userId") Long userId,
                                                              @Param("categoryId") Long categoryId);

    java.math.BigDecimal sumExpenseByCategoryAndTimeRange(@Param("userId") Long userId,
                                                          @Param("categoryId") Long categoryId,
                                                          @Param("startTime") java.time.LocalDateTime startTime,
                                                          @Param("endTime") java.time.LocalDateTime endTime);

    int insertBill(Bill bill);

    List<BillListVO> list(@Param("userId") Long userId,
                          @Param("dto") BillQueryDTO dto);

    @Select("select id, user_id, category_id, amount, type," +
            " remark, record_time, is_ai_generated, create_time," +
            " update_time, is_deleted from bill where id = #{id} and user_id = #{userId} and is_deleted = 0")
    Bill getById(@Param("id") Long id, @Param("userId") Long userId);

    int update(@Param("id") Long id, @Param("userId") Long userId, @Param("dto") BillUpdateDTO dto);

    int delete(@Param("id") Long id, @Param("userId") Long userId);
}
