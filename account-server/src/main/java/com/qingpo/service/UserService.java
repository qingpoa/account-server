package com.qingpo.service;

import com.qingpo.pojo.User;
import com.qingpo.pojo.UserLoginV;
import com.qingpo.pojo.UserVO;

public interface UserService {

    UserVO getUserInfo(Long userId);

    UserLoginV login(User user);
}
