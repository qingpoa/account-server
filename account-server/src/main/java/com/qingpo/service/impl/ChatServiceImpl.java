package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.chat.ChatFileUploadVO;
import com.qingpo.service.ChatService;
import com.qingpo.utils.OssUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.Set;

@Service
public class ChatServiceImpl implements ChatService {

    private static final Set<String> ALLOWED_IMAGE_CONTENT_TYPES = Set.of(
            MediaType.IMAGE_JPEG_VALUE,
            MediaType.IMAGE_PNG_VALUE,
            "image/webp",
            "image/gif"
    );

    private static final Set<String> ALLOWED_IMAGE_EXTENSIONS = Set.of(
            "jpg",
            "jpeg",
            "png",
            "webp",
            "gif"
    );

    @Autowired
    private OssUtils ossUtils;

    @Override
    public ChatFileUploadVO uploadChatImage(MultipartFile file) {
        validateImage(file);

        OssUtils.UploadResult uploadResult = ossUtils.upload(file, "chat");
        return new ChatFileUploadVO(
                uploadResult.objectName(),
                uploadResult.fileUrl(),
                uploadResult.originalFilename()
        );
    }

    private void validateImage(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(Result.BAD_REQUEST, "上传图片不能为空");
        }
        String contentType = file.getContentType();
        String fileName = file.getOriginalFilename();
        String extension = extractExtension(fileName);
        if (!ALLOWED_IMAGE_CONTENT_TYPES.contains(contentType) || !ALLOWED_IMAGE_EXTENSIONS.contains(extension)) {
            throw new BusinessException(Result.BAD_REQUEST, "仅支持 jpg、jpeg、png、webp、gif 格式图片");
        }
    }

    private String extractExtension(String fileName) {
        if (fileName == null || !fileName.contains(".")) {
            return "";
        }
        return fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase();
    }
}
