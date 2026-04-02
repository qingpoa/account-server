package com.qingpo.service.impl;

import com.qingpo.exception.BusinessException;
import com.qingpo.mapper.BillMapper;
import com.qingpo.pojo.Result;
import com.qingpo.pojo.bill.BillListVO;
import com.qingpo.pojo.bill.BillQueryDTO;
import com.qingpo.service.ExportService;
import jakarta.servlet.http.HttpServletResponse;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class ExportServiceImpl implements ExportService {

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
        String fileName = URLEncoder.encode("bill-export.xlsx", StandardCharsets.UTF_8);
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setCharacterEncoding("UTF-8");
        response.setHeader("Content-Disposition", "attachment;filename=" + fileName);

        Workbook workbook = new XSSFWorkbook();
        Sheet sheet = workbook.createSheet("账单数据");
        Row headerRow = sheet.createRow(0);
        headerRow.createCell(0).setCellValue("账单ID");
        headerRow.createCell(1).setCellValue("金额");
        headerRow.createCell(2).setCellValue("类型");
        headerRow.createCell(3).setCellValue("分类名称");
        headerRow.createCell(4).setCellValue("备注");
        headerRow.createCell(5).setCellValue("记录时间");
        headerRow.createCell(6).setCellValue("是否AI生成");

        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

        for (int i = 0; i < list.size(); i++) {
            BillListVO bill = list.get(i);
            Row row = sheet.createRow(i + 1);

            row.createCell(0).setCellValue(bill.getId());
            row.createCell(1).setCellValue(bill.getAmount().doubleValue());
            row.createCell(2).setCellValue(bill.getType() == 1 ? "收入" : "支出");
            row.createCell(3).setCellValue(bill.getCategoryName() == null ? "" : bill.getCategoryName());
            row.createCell(4).setCellValue(bill.getRemark() == null ? "" : bill.getRemark());
            row.createCell(5).setCellValue(
                    bill.getRecordTime() == null ? "" : bill.getRecordTime().format(formatter)
            );
            row.createCell(6).setCellValue(
                    bill.getIsAiGenerated() != null && bill.getIsAiGenerated() == 1 ? "是" : "否"
            );
        }
        workbook.write(response.getOutputStream());
        response.getOutputStream().flush();
        workbook.close();



    }
}
