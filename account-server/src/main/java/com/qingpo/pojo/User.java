package com.qingpo.pojo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

//用户实体类
@Data
@AllArgsConstructor
@NoArgsConstructor
public class User {
    private Long id;//用户 id
    private String username;//用户名
    private String password;//密码
    private String nickname;//昵称
    private String avatar = null;//头像
    private Integer enableOverspendAlert;//是否开启超支提醒
    private LocalDateTime createTime;//创建时间
    private LocalDateTime updateTime;//更新时间
    private Integer isDeleted;//是否删除(1为是，默认为0)
}


