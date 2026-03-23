package com.qingpo.service.impl;

import com.qingpo.mapper.UserMapper;
import com.qingpo.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserMapper userMapper;
}
