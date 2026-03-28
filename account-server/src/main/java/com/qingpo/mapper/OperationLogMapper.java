package com.qingpo.mapper;

import com.qingpo.pojo.log.OperationLog;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface OperationLogMapper {

    @Insert("""
            insert into operation_log
            (user_id, username, module, operation_type, result_code, status, cost_time, create_time)
            values
            (#{userId}, #{username}, #{module}, #{operationType}, #{resultCode}, #{status}, #{costTime}, #{createTime})
            """)
    int insert(OperationLog operationLog);
}
