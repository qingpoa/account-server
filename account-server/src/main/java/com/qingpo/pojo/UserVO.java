package com.qingpo.pojo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户信息视图对象（只返回部分字段）
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class UserVO {
    private Long userId;
    private String username;
    private String nickname;
    private String avatar;
    private Integer enableOverspendAlert;
}
