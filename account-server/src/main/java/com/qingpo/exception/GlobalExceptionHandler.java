package com.qingpo.exception;


import com.qingpo.pojo.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public Result handleBusinessException(BusinessException e) {
        log.warn("业务异常: code={}, msg={}", e.getCode(), e.getMessage());
        return Result.error(e.getCode(), e.getMessage());
    }

    @ExceptionHandler({
            IllegalArgumentException.class,
            MissingServletRequestParameterException.class,
            MethodArgumentTypeMismatchException.class,
            HttpMessageNotReadableException.class
    })
    public Result handleBadRequestException(Exception e) {
        log.warn("请求参数错误: {}", e.getMessage());
        return Result.error(Result.BAD_REQUEST, "请求参数错误");
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public Result handleMethodNotSupportedException(HttpRequestMethodNotSupportedException e) {
        log.warn("请求方式错误: {}", e.getMessage());
        return Result.error(Result.BAD_REQUEST, "请求方式错误");
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public Result handleNotFoundException(NoResourceFoundException e) {
        log.warn("资源不存在: {}", e.getMessage());
        return Result.error(Result.NOT_FOUND, "请求资源不存在");
    }

    @ExceptionHandler(Exception.class)
    public Result handleException(Exception e) {
        log.error("系统异常", e);
        return Result.error(Result.SERVER_ERROR, "服务器内部错误");
    }
}
