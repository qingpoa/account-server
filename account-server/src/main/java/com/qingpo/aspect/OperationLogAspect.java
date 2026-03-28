package com.qingpo.aspect;

import com.qingpo.context.UserContext;
import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.OperationLogMapper;
import com.qingpo.mapper.UserMapper;
import com.qingpo.pojo.log.OperationLog;
import com.qingpo.pojo.user.User;
import com.qingpo.pojo.user.UserChangePassword;
import com.qingpo.pojo.user.UserVO;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Slf4j
@Aspect
@Component
public class OperationLogAspect {

    @Autowired
    private OperationLogMapper operationLogMapper;

    @Autowired
    private UserMapper userMapper;

    @Around("@annotation(operationLog)")
    public Object around(ProceedingJoinPoint joinPoint, com.qingpo.annotation.OperationLog operationLog) throws Throwable {
        long start = System.currentTimeMillis();
        Long userId = UserContext.getCurrentUserId();
        String username = resolveUsername(userId, joinPoint.getArgs());

        try {
            Object result = joinPoint.proceed();
            saveLog(userId, username, operationLog, 200, "SUCCESS", System.currentTimeMillis() - start);
            return result;
        } catch (BusinessException e) {
            saveLog(userId, username, operationLog, e.getCode(), "FAIL", System.currentTimeMillis() - start);
            throw e;
        } catch (Exception e) {
            saveLog(userId, username, operationLog, 500, "FAIL", System.currentTimeMillis() - start);
            throw e;
        }
    }

    private void saveLog(Long userId, String username, com.qingpo.annotation.OperationLog operationLog,
                         Integer resultCode, String status, long costTime) {
        try {
            OperationLog logData = new OperationLog();
            logData.setUserId(userId);
            logData.setUsername(username);
            logData.setModule(operationLog.module());
            logData.setOperationType(operationLog.type());
            logData.setResultCode(resultCode);
            logData.setStatus(status);
            logData.setCostTime(costTime);
            logData.setCreateTime(LocalDateTime.now());
            operationLogMapper.insert(logData);
        } catch (Exception e) {
            log.error("保存操作日志失败", e);
        }
    }

    private String resolveUsername(Long userId, Object[] args) {
        if (userId != null) {
            User dbUser = userMapper.getUserInfoById(userId);
            if (dbUser != null) {
                return dbUser.getUsername();
            }
        }

        if (args == null) {
            return null;
        }

        for (Object arg : args) {
            if (arg instanceof User user) {
                return user.getUsername();
            }
            if (arg instanceof UserVO userVO) {
                return userVO.getUsername();
            }
            if (arg instanceof UserChangePassword) {
                return null;
            }
        }
        return null;
    }
}
