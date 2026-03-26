package com.qingpo.pojo.user;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户注册成功返回对象
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class UserRegisterVO {
    private Long userId;
    private String token;
}
