package com.qingpo.mapper;

import com.qingpo.pojo.user.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserMapper {

    @Select("select id, username, password, nickname, avatar, enable_overspend_alert, create_time, update_time, is_deleted from user where username = #{username}")
    User getUserInfoByUserName(String username);

    @Select("select id, username, password, nickname, avatar, enable_overspend_alert, create_time, update_time, is_deleted from user where id = #{id} and is_deleted = 0")
    User getUserInfoById(Long id);

    int insertUser(User user);
}
