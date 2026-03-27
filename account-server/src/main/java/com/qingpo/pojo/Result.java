package com.qingpo.pojo;

import lombok.Data;

/**
 * 后端统一返回结果
 */
@Data
public class Result{

    public static final Integer SUCCESS = 200; //成功
    public static final Integer BAD_REQUEST = 400; //请求错误
    public static final Integer UNAUTHORIZED = 401; //未授权
    public static final Integer API_KEY_INVALID = 402; //API密钥无效
    public static final Integer FORBIDDEN = 403; //禁止
    public static final Integer NOT_FOUND = 404; //未找到
    public static final Integer SERVER_ERROR = 500; //服务器错误
    public static final Integer AI_SERVICE_ERROR = 503; //AI服务错误

    private Integer code;
    private String msg;
    private Object data;

    public static Result success() {
        Result result = new Result();
        result.code = SUCCESS;
        result.msg = "success";
        return result;
    }

    public static Result success(Object object) {
        Result result = new Result();
        result.data = object;
        result.code = SUCCESS;
        result.msg = "success";
        return result;
    }

    public static Result error(String msg) {
        return error(SERVER_ERROR, msg);
    }

    public static Result error(Integer code, String msg) {
        Result result = new Result();
        result.code = code;
        result.msg = msg;
        return result;
    }

}
