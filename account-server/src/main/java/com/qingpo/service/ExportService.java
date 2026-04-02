package com.qingpo.service;

import com.qingpo.pojo.bill.BillQueryDTO;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;

public interface ExportService {
    void exportBill(Long userId, BillQueryDTO dto, HttpServletResponse response) throws IOException;
}
