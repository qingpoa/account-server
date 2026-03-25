package com.qingpo.service.impl;

import com.qingpo.mapper.UserMapper;
import com.qingpo.pojo.User;
import com.qingpo.pojo.UserVO;
import com.qingpo.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserMapper userMapper;


    @Override
    public UserVO getUserInfo(Integer id) {
        User user = userMapper.getUserInfo(id);
        if (user == null) {
            return null;
        }
        return new UserVO(
                user.getId(),
                user.getUsername(),
                user.getNickname(),
                user.getAvatar(),
                user.getEnableOverspendAlert()
        );
    }
}
