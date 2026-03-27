package com.qingpo.pojo.user;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class UserChangePassword {
    private Integer userId;
    private String oldPassword;
    private String newPassword;
}
