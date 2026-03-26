package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.UserMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.user.User;
import com.qingpo.pojo.user.UserLoginV;
import com.qingpo.pojo.user.UserVO;
import com.qingpo.service.UserService;
import com.qingpo.utils.JwtUtils;
import com.qingpo.utils.PasswordUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;

@Slf4j
@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserMapper userMapper;


    @Override
    public UserVO getUserInfo(Long userId) {
        User user = userMapper.getUserInfoById(userId);
        if (user == null) {
            throw new BusinessException(Result.NOT_FOUND, "用户不存在");
        }
        return new UserVO(
                user.getId(),
                user.getUsername(),
                user.getNickname(),
                user.getAvatar(),
                user.getEnableOverspendAlert()
        );
    }

    @Override
    public UserLoginV login(User user) {
        User dbUser = userMapper.getUserInfoByUserName(user.getUsername());
        log.info("正在请求用户登录:{}", dbUser);
        String now_password = PasswordUtils.encode(user.getPassword());
        if (dbUser != null && PasswordUtils.matches(user.getPassword(), dbUser.getPassword())) {
            UserVO userVO = new UserVO(
                    dbUser.getId(),
                    dbUser.getUsername(),
                    dbUser.getNickname(),
                    dbUser.getAvatar(),
                    dbUser.getEnableOverspendAlert()
            );
            HashMap<String, Object> payload = new HashMap<>();
            payload.put("userId", userVO.getUserId());
            payload.put("username", userVO.getUsername());
            String token = JwtUtils.generateJwt(payload);
            return new UserLoginV(Math.toIntExact(dbUser.getId()), token, userVO);
        }
        return null;
    }


}
