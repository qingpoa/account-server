package com.qingpo.service;

import com.qingpo.pojo.user.*;
import org.springframework.web.multipart.MultipartFile;

public interface UserService {

    UserVO getUserInfo(Long userId);

    UserLoginV login(User user);

    UserRegisterVO register(User user);

    void updatePassword(UserChangePassword ucp);

    void updateUserInfo(UserVO user);

    String uploadAvatar(Long userId, MultipartFile file);
}
