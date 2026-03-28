package com.qingpo.mapper;

import com.qingpo.pojo.user.User;
import com.qingpo.pojo.user.UserVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface UserMapper {

    @Select("select id, username, password, nickname, avatar, enable_overspend_alert, create_time, update_time, is_deleted from user where username = #{username}")
    User getUserInfoByUserName(String username);

    @Select("select id, username, password, nickname, avatar, enable_overspend_alert, create_time, update_time, is_deleted from user where id = #{id} and is_deleted = 0")
    User getUserInfoById(Long id);

    int insertUser(User user);

    @Update("update user set password = #{newEncodedPassword} where id = #{userId}")
    int updatePassword(Integer userId, String newEncodedPassword);

    int updateUserInfo(UserVO user);
}
