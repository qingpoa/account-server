package com.qingpo.service.impl;

import com.qingpo.annotation.OperationLog;
import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.UserMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.user.*;
import com.qingpo.service.UserService;
import com.qingpo.utils.OssUtils;
import com.qingpo.utils.PasswordUtils;
import com.qingpo.utils.TokenUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.Set;
import java.util.concurrent.TimeUnit;

import static com.qingpo.config.RedisConfig.*;

@Slf4j
@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private OssUtils ossUtils;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

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
            String token = TokenUtils.generateToken(32);
            String loginUserKey = LOGIN_USER_KEY + token;
            String userTokenKey = USER_TO_TOKEN_KEY + dbUser.getId().toString();
            cleanupInvalidTokens(userTokenKey);
            stringRedisTemplate.opsForValue().set(loginUserKey, dbUser.getId().toString());
            stringRedisTemplate.expire(loginUserKey, LOGIN_USER_TTL, TimeUnit.HOURS);
            stringRedisTemplate.opsForSet().add(userTokenKey, token);
            stringRedisTemplate.expire(userTokenKey, USER_TO_TOKEN_TTL, TimeUnit.HOURS);
            return new UserLoginV(Math.toIntExact(dbUser.getId()), token, userVO);
        }
        return null;
    }

    @Override
    @OperationLog(module = "USER", type = "INSERT")
    public UserRegisterVO register(User user) {
        User dbUser = userMapper.getUserInfoByUserName(user.getUsername());
        if (dbUser != null) {
            throw new BusinessException(Result.BAD_REQUEST, "用户名已存在");
        }
        if (user.getNickname() == null || user.getNickname().isBlank()) {
            user.setNickname(user.getUsername());
        }

        user.setPassword(PasswordUtils.encode(user.getPassword()));
        try {
            userMapper.insertUser(user);
        } catch (DuplicateKeyException e) {
            throw new BusinessException(Result.BAD_REQUEST, "用户名已存在");
        }
        if (user.getId() == null) {
            throw new BusinessException(Result.SERVER_ERROR, "注册失败");
        }
        String token = TokenUtils.generateToken(32);
        String userTokenKey = USER_TO_TOKEN_KEY + user.getId().toString();
        cleanupInvalidTokens(userTokenKey);
        stringRedisTemplate.opsForValue().set(LOGIN_USER_KEY + token, user.getId().toString());
        stringRedisTemplate.expire(LOGIN_USER_KEY + token, LOGIN_USER_TTL, TimeUnit.HOURS);
        stringRedisTemplate.opsForSet().add(userTokenKey, token);
        stringRedisTemplate.expire(userTokenKey, USER_TO_TOKEN_TTL, TimeUnit.HOURS);
        return new UserRegisterVO(user.getId(), token);

    }

    @Override
    @OperationLog(module = "USER", type = "UPDATE")
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
        int rows = userMapper.updatePassword(ucp.getUserId(), newEncodedPassword);
        if (rows == 0) {
            throw new BusinessException(Result.SERVER_ERROR, "修改密码失败");
        }
        Set<String> tokens = stringRedisTemplate.opsForSet().members(USER_TO_TOKEN_KEY + ucp.getUserId());
        if (tokens != null) {
            for (String token : tokens) {
                stringRedisTemplate.delete(LOGIN_USER_KEY + token);
            }
        }
        stringRedisTemplate.delete(USER_TO_TOKEN_KEY + ucp.getUserId());
    }

    @Override
    @OperationLog(module = "USER", type = "UPDATE")
    public void updateUserInfo(UserVO user) {
        User dbUser = userMapper.getUserInfoById(user.getUserId());
        if (dbUser == null) {
            throw new BusinessException(Result.NOT_FOUND, "用户不存在");
        }
        int rows = userMapper.updateUserInfo(user);
        if (rows == 0) {
            throw new BusinessException(Result.SERVER_ERROR, "更新用户信息失败");
        }
    }

    @Override
    @OperationLog(module = "USER", type = "UPDATE")
    public String uploadAvatar(Long userId, MultipartFile file) {
        User dbUser = userMapper.getUserInfoById(userId);
        if (dbUser == null) {
            throw new BusinessException(Result.NOT_FOUND, "用户不存在");
        }

        String avatarUrl = ossUtils.upload(file);
        UserVO userVO = new UserVO();
        userVO.setUserId(userId);
        userVO.setAvatar(avatarUrl);

        int rows = userMapper.updateUserInfo(userVO);
        if (rows == 0) {
            throw new BusinessException(Result.SERVER_ERROR, "头像更新失败");
        }
        return avatarUrl;
    }

    private void cleanupInvalidTokens(String userTokenKey) {
        Set<String> tokens = stringRedisTemplate.opsForSet().members(userTokenKey);
        if (tokens == null || tokens.isEmpty()) {
            return;
        }
        for (String oldToken : tokens) {
            Boolean exists = stringRedisTemplate.hasKey(LOGIN_USER_KEY + oldToken);
            if (Boolean.FALSE.equals(exists)) {
                stringRedisTemplate.opsForSet().remove(userTokenKey, oldToken);
            }
        }
    }


}
