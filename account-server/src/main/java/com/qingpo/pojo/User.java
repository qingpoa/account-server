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
//    用户 id
    private Long id;
//    用户名
    private String username;
//    密码
    private String password;
//     昵称
    private String nickname;
//    头像
    private String avatar = null;
//    是否开启超支提醒
    private Integer enableOverspendAlert;
//    创建时间
    private LocalDateTime createTime;
//    更新时间
    private LocalDateTime updateTime;
//    是否删除(1为是，默认为0)
    private Integer isDeleted;

    @Override
    public String toString() {
        return "User{" +
                "id=" + id +
                ", username='" + username + '\'' +
                ", nickname='" + nickname + '\'' +
                ", avatar='" + avatar + '\'' +
                ", enableOverspendAlert=" + enableOverspendAlert +
                ", createTime=" + createTime +
                ", updateTime=" + updateTime +
                ", isDeleted=" + isDeleted +
                '}';
    }
}
