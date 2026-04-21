package com.qingpo.service;

import com.qingpo.pojo.chat.ChatFileUploadVO;
import org.springframework.web.multipart.MultipartFile;

public interface ChatService {

    ChatFileUploadVO uploadChatImage(MultipartFile file);
}
