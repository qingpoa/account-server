package com.qingpo.utils;

import com.aliyun.oss.OSS;
import com.qingpo.config.OssProperties;
import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

@Component
public class OssUtils {

    private static final DateTimeFormatter YEAR_MONTH_FORMATTER = DateTimeFormatter.ofPattern("yyyy/MM");

    @Autowired
    private OSS ossClient;

    @Autowired
    private OssProperties ossProperties;

    public String upload(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(Result.BAD_REQUEST, "上传文件不能为空");
        }

        String originalFilename = file.getOriginalFilename();
        String suffix = "";
        if (originalFilename != null && originalFilename.contains(".")) {
            suffix = originalFilename.substring(originalFilename.lastIndexOf("."));
        }

        String yearMonthPath = LocalDate.now().format(YEAR_MONTH_FORMATTER);
        String objectName = yearMonthPath + "/" + UUID.randomUUID().toString().replace("-", "") + suffix;

        try {
            ossClient.putObject(
                    ossProperties.getBucketName(),
                    objectName,
                    file.getInputStream()
            );
        } catch (IOException e) {
            throw new BusinessException(Result.SERVER_ERROR, "文件上传失败");
        }

        return ossProperties.getDomain() + "/" + objectName;
    }
}
