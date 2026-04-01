package com.qingpo.exception;

import com.qingpo.pojo.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Result> handleBusinessException(BusinessException e) {
        log.warn("业务异常: code={}, msg={}", e.getCode(), e.getMessage());
        return response(e.getCode(), Result.error(e.getCode(), e.getMessage()));
    }

    @ExceptionHandler({
            IllegalArgumentException.class,
            MissingServletRequestParameterException.class,
            MethodArgumentTypeMismatchException.class,
            HttpMessageNotReadableException.class
    })
    public ResponseEntity<Result> handleBadRequestException(Exception e) {
        log.warn("请求参数错误: {}", e.getMessage());
        return response(Result.BAD_REQUEST, Result.error(Result.BAD_REQUEST, "请求参数错误"));
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<Result> handleMethodNotSupportedException(HttpRequestMethodNotSupportedException e) {
        log.warn("请求方式错误: {}", e.getMessage());
        return response(Result.BAD_REQUEST, Result.error(Result.BAD_REQUEST, "请求方式错误"));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<Result> handleNotFoundException(NoResourceFoundException e) {
        log.warn("资源不存在: {}", e.getMessage());
        return response(Result.NOT_FOUND, Result.error(Result.NOT_FOUND, "请求资源不存在"));
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<Result> handleMaxUploadSizeExceededException(MaxUploadSizeExceededException e) {
        log.warn("上传文件大小超出限制: {}", e.getMessage());
        long maxSize = e.getMaxUploadSize();
        String maxSizeMb = String.format("%.2f", maxSize / 1024.0 / 1024.0);
        return response(Result.BAD_REQUEST, Result.error(Result.BAD_REQUEST, "上传文件大小超出"+maxSizeMb+"MB"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Result> handleException(Exception e) {
        log.error("系统异常", e);
        return response(Result.SERVER_ERROR, Result.error(Result.SERVER_ERROR, "服务器内部错误"));
    }

    private ResponseEntity<Result> response(Integer status, Result result) {
        return ResponseEntity.status(status).body(result);
    }
}
