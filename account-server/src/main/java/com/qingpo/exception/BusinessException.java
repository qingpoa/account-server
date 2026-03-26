package com.qingpo.exception;

import lombok.Getter;

/**
 * 通用业务异常，支持直接携带响应码。
 */
@Getter
public class BusinessException extends RuntimeException {

    private final Integer code;

    public BusinessException(String message) {
        this(500, message);
    }

    public BusinessException(Integer code, String message) {
        super(message);
        this.code = code;
    }

}
