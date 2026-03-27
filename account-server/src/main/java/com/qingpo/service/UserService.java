package com.qingpo.service;

import com.qingpo.pojo.user.User;
import com.qingpo.pojo.user.UserLoginV;
import com.qingpo.pojo.user.UserRegisterVO;
import com.qingpo.pojo.user.UserVO;

public interface UserService {

    UserVO getUserInfo(Long userId);

    UserLoginV login(User user);

    UserRegisterVO register(User user);
}
