package com.qingpo.pojo.log;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class OperationLog {

    private Long id;
    private Long userId;
    private String username;
    private String module;
    private String operationType;
    private Integer resultCode;
    private String status;
    private Long costTime;
    private LocalDateTime createTime;
}
