package com.qingpo.controller;

import com.qingpo.context.UserContext;
import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import com.qingpo.service.ChatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/chat")
public class ChatController extends BaseController {

    @Autowired
    private ChatService chatService;

    @PostMapping("/files")
    public ResponseEntity<Result> uploadChatImage(@RequestParam("file") MultipartFile file) {
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        }
        return response(Result.SUCCESS, Result.success(chatService.uploadChatImage(file)));
    }
}
