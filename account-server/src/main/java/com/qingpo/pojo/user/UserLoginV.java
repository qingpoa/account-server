package com.qingpo.pojo.user;


import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class UserLoginV {
    private Integer userId;
    private String token;
    private UserVO userInfo;
}
