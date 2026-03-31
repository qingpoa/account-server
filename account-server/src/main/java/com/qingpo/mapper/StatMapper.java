package com.qingpo.mapper;

import com.qingpo.pojo.stat.StatCategoryVO;
import com.qingpo.pojo.stat.StatOverviewVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface StatMapper {


    StatOverviewVO overview(@Param("userId")Long userId,
                            @Param("startTime") LocalDateTime startTime,
                            @Param("endTime") LocalDateTime endTime);

    List<StatCategoryVO> category(@Param("userId") Long userId,
                                  @Param("type") Integer type,
                                  @Param("startTime") LocalDateTime startTime,
                                  @Param("endTime") LocalDateTime endTime);
}
