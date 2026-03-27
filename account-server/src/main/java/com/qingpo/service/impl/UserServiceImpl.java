package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.UserMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.user.*;
import com.qingpo.service.UserService;
import com.qingpo.utils.JwtUtils;
import com.qingpo.utils.PasswordUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

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
        //log.info("正在登录用户: username={}，password={}", user.getUsername(),user.getPassword());
        if (user == null
                || user.getUsername() == null || user.getUsername().isBlank()
                || user.getPassword() == null || user.getPassword().isBlank()) {
            return null;
        }
        User dbUser = userMapper.getUserInfoByUserName(user.getUsername());
        log.info("正在校验登录用户: username={}", user.getUsername());
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

    @Override
    public UserRegisterVO register(User user) {
        User dbUser = userMapper.getUserInfoByUserName(user.getUsername());
        if (dbUser != null) {
            throw new BusinessException(Result.BAD_REQUEST, "用户名已存在");
        }
        if (user.getNickname() == null || user.getNickname().isBlank()) {
            user.setNickname(user.getUsername());
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("username", user.getUsername());
        user.setPassword(PasswordUtils.encode(user.getPassword()));
        try {
            userMapper.insertUser(user);
        } catch (DuplicateKeyException e) {
            throw new BusinessException(Result.BAD_REQUEST, "用户名已存在");
        }
        if (user.getId() == null) {
            throw new BusinessException(Result.SERVER_ERROR, "注册失败");
        }
        payload.put("userId", user.getId());
        String token = JwtUtils.generateJwt(payload);
        return new UserRegisterVO(user.getId(), token);

    }

    @Override
    public void updatePassword(UserChangePassword ucp) {
        if (ucp == null
                || ucp.getOldPassword() == null || ucp.getOldPassword().isBlank()
                || ucp.getNewPassword() == null || ucp.getNewPassword().isBlank()) {
            throw new BusinessException(Result.BAD_REQUEST, "旧密码和新密码不能为空");
        }
        if (ucp.getOldPassword().equals(ucp.getNewPassword())) {
            throw new BusinessException(Result.BAD_REQUEST, "新密码不能与旧密码相同");
        }
        User user = userMapper.getUserInfoById(Long.valueOf(ucp.getUserId()));
        if (user == null) {
            throw new BusinessException(Result.NOT_FOUND, "用户不存在");
        }
        if (!PasswordUtils.matches(ucp.getOldPassword(), user.getPassword())) {
            throw new BusinessException(Result.BAD_REQUEST, "旧密码错误");
        }
        String newEncodedPassword = PasswordUtils.encode(ucp.getNewPassword());
        userMapper.updatePassword(ucp.getUserId(), newEncodedPassword);
    }

    @Override
    public void updateUserInfo(UserVO user) {
        User dbUser = userMapper.getUserInfoById(user.getUserId());
        if (dbUser == null) {
            throw new BusinessException(Result.NOT_FOUND, "用户不存在");
        }
        userMapper.updateUserInfo(user);
    }


}
