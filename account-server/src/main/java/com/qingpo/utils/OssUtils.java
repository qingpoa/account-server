package com.qingpo.utils;

import com.aliyun.oss.ClientException;
import com.aliyun.oss.OSS;
import com.aliyun.oss.OSSException;
import com.qingpo.config.OssProperties;
import com.qingpo.exception.BusinessException;
import com.qingpo.pojo.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

@Slf4j
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

    public void delete(String url) throws OSSException {
        if (url == null) {
            return;
        }
        if (!url.contains(ossProperties.getDomain())) {
            log.warn("跳过OSS删除：URL不属于当前环境域名, url={}", url);
            return;
        }
        String objectName = url.replace(ossProperties.getDomain() + "/", "");
        try {
            ossClient.deleteObject(ossProperties.getBucketName(), objectName);
        } catch (OSSException | ClientException e) {
            log.error("删除OSS文件失败: {}", objectName, e);
        }
    }
}
