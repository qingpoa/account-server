package com.qingpo.service;

import com.qingpo.pojo.user.*;

public interface UserService {

    UserVO getUserInfo(Long userId);

    UserLoginV login(User user);

    UserRegisterVO register(User user);

    void updatePassword(UserChangePassword ucp);

    void updateUserInfo(UserVO user);
}
