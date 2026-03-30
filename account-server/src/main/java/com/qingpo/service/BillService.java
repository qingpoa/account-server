package com.qingpo.service;

import com.qingpo.pojo.PageResult;
import com.qingpo.pojo.bill.*;

public interface BillService {

    PageResult<BillListVO> list(Long userId, BillQueryDTO dto);

    BillSaveVO save(Long userId, BillSaveDTO dto);

    void update(Long userId, Long id, BillUpdateDTO dto);

    void delete(Long userId, Long id);

    BillDetailVO detail(Long userId, Long id);
}
