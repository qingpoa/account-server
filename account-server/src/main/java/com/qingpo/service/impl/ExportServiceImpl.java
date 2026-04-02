package com.qingpo.service.impl;

import com.alibaba.excel.EasyExcel;
import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.BillMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.bill.BillExportVO;
import com.qingpo.pojo.bill.BillListVO;
import com.qingpo.pojo.bill.BillQueryDTO;
import com.qingpo.service.ExportService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ExportServiceImpl implements ExportService {

    private static final DateTimeFormatter EXPORT_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");
    private static final DateTimeFormatter FILE_DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    @Autowired
    private BillMapper billMapper;

    @Override
    public void exportBill(Long userId, BillQueryDTO dto, HttpServletResponse response) throws IOException {
        if (userId == null)
            throw new BusinessException(Result.UNAUTHORIZED, "未登录或登录已过期");
        if (dto == null)
            throw new BusinessException(Result.BAD_REQUEST, "请求参数不能为空");
        if (dto.getType() != null && dto.getType() != 1 && dto.getType() != 2)
            throw new BusinessException(Result.BAD_REQUEST, "账单类型参数错误");
        if (dto.getStartTime() != null && dto.getEndTime() != null
                && dto.getStartTime().isAfter(dto.getEndTime())) {
            throw new BusinessException(Result.BAD_REQUEST, "开始时间不能晚于结束时间");
        }

        List<BillListVO> list = billMapper.list(userId,dto);
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        List<BillExportVO> exportList = list.stream()
                .map(bill -> new BillExportVO(
                        bill.getId(),
                        bill.getAmount(),
                        bill.getType() == 1 ? "收入" : "支出",
                        bill.getCategoryName() == null ? "" : bill.getCategoryName(),
                        bill.getRemark() == null ? "" : bill.getRemark(),
                        bill.getRecordTime() == null ? "" : bill.getRecordTime().format(formatter),
                        bill.getIsAiGenerated() != null && bill.getIsAiGenerated() == 1 ? "是" : "否"
                ))
                .collect(Collectors.toList());

        String rawFileName = buildExportFileName(dto);
        String fileName = URLEncoder.encode(rawFileName, StandardCharsets.UTF_8).replaceAll("\\+", "%20");
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setCharacterEncoding("UTF-8");
        response.setHeader("Content-Disposition", "attachment; filename*=UTF-8''" + fileName);
        EasyExcel.write(response.getOutputStream(), BillExportVO.class)
                .sheet("账单数据")
                .doWrite(exportList);
        response.getOutputStream().flush();
    }

    private String buildExportFileName(BillQueryDTO dto) {
        List<String> parts = new ArrayList<>();
        parts.add("bill-export");

        if (dto.getType() != null) {
            parts.add(dto.getType() == 1 ? "income" : "expense");
        }
        if (dto.getCategoryId() != null) {
            parts.add("category-" + dto.getCategoryId());
        }
        if (dto.getStartTime() != null) {
            parts.add("from-" + dto.getStartTime().format(FILE_DATE_FORMATTER));
        }
        if (dto.getEndTime() != null) {
            parts.add("to-" + dto.getEndTime().format(FILE_DATE_FORMATTER));
        }

        parts.add(LocalDateTime.now().format(EXPORT_TIME_FORMATTER));
        return String.join("_", parts) + ".xlsx";
    }
}
