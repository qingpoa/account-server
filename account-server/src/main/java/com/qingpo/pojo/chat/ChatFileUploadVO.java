package com.qingpo.pojo.chat;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class ChatFileUploadVO {
    private String fileId;
    private String fileUrl;
    private String fileName;
}
