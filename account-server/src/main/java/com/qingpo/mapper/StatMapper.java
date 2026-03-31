package com.qingpo.mapper;

import com.qingpo.pojo.stat.StatOverviewVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;

@Mapper
public interface StatMapper {


    StatOverviewVO overview(@Param("userId")Long userId,
                            @Param("startTime") LocalDateTime startTime,
                            @Param("endTime") LocalDateTime endTime);
}
