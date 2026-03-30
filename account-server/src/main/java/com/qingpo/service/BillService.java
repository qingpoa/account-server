package com.qingpo.service;

import com.qingpo.pojo.PageResult;
import com.qingpo.pojo.bill.BillListVO;
import com.qingpo.pojo.bill.BillQueryDTO;
import com.qingpo.pojo.bill.BillSaveDTO;
import com.qingpo.pojo.bill.BillSaveVO;

public interface BillService {

    PageResult<BillListVO> list(Long userId, BillQueryDTO dto);

    BillSaveVO save(Long userId, BillSaveDTO dto);

    void update(Long userId, Long id, BillSaveDTO dto);
}
