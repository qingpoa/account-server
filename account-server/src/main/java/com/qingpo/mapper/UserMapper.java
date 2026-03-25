package com.qingpo.mapper;

import com.qingpo.pojo.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserMapper {

    @Select("select id, username, password, nickname, avatar, enable_overspend_alert from user where id = #{id}")
    User getUserInfo(Integer id);
}
