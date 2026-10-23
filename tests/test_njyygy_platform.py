# -*- coding: utf-8 -*-
"""
南京医药国药 DDI 数据直连系统平台接入契约测试。

本模块验证国药账号配置完整性、五类型端点映射、查询负载形态、
登录响应双层数据结构口径与库存快照语义，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入南京医药国药平台适配器。
from ddi_framework.platforms.njyygy import NjyygyPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义南京医药国药接入契约测试套件。
class NjyygyPlatformTests(unittest.TestCase):

    """
    南京医药国药 DDI 数据直连系统平台接入契约测试。

    :return: 测试套件实例。
    :rtype: NjyygyPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "南京医药国药有限公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "门店库存", "仓库库存"]

    # 定义类级端点映射引用（与浏览器抓包一致）。
    EXPECTED_ENDPOINTS = {
        "配送流向": "/api/v1/supplier-data/delivery-out",
        "购进流向": "/api/v1/supplier-data/purchase-in",
        "纯销流向": "/api/v1/supplier-data/retail-out",
        "门店库存": "/api/v1/supplier-data/store-stock",
        "仓库库存": "/api/v1/supplier-data/warehouse-stock",
    }

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: 南京医药国药平台适配器实例。
        :rtype: NjyygyPlatform
        """

        # 读取账号配置并构建适配器。
        return NjyygyPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证国药账号声明平台归属、双站点地址与类型清单。

        :return: None。
        :rtype: None
        """

        # 读取国药账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为 njyygy。
        self.assertEqual(account["平台"], "njyygy")

        # 断言接口与前端站点地址分离部署。
        self.assertEqual(account["站点根地址"], "https://ddi-api.njyygy.com")
        self.assertEqual(account["前端地址"], "https://ddi.njyygy.com")

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义五类型端点映射验证。
    def test_data_paths_match_capture(self):

        """
        验证五类型端点与浏览器抓包一致。

        :return: None。
        :rtype: None
        """

        # 断言端点映射与约定一致。
        self.assertEqual(NjyygyPlatform.DATA_PATHS, self.EXPECTED_ENDPOINTS)

    # 定义登录表单形态验证。
    def test_login_payload_is_plaintext_json(self):

        """
        验证登录表单为手机号、明文密码与空验证码三字段。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建登录请求体。
        payload = platform.build_login_payload()

        # 断言三字段齐备且值正确。
        self.assertEqual(payload["phone"], "15044239286")
        self.assertEqual(payload["password"], "Qqwer1234..**")
        self.assertEqual(payload["captcha"], "")

    # 定义查询负载形态验证。
    def test_query_payload_shapes(self):

        """
        验证流向类带日期区间、库存类仅分页域。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 读取购进负载并断言日期区间与分页域。
        purchase_payload = platform.build_query_payload("购进流向", "2026-10-16", "2026-10-23", 1)
        self.assertEqual(purchase_payload, {"pageNum": 1, "pageSize": 100, "startTime": "2026-10-16", "endTime": "2026-10-23"})

        # 读取门店库存负载并断言无日期字段。
        store_payload = platform.build_query_payload("门店库存", None, None, 1)
        self.assertEqual(store_payload, {"pageNum": 1, "pageSize": 100})

    # 定义总条数与数据块口径验证。
    def test_response_block_semantics(self):

        """
        验证单页解析提取 data.list 数据行与 data.total 总条数。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构造平台响应样例。
        sample = {"code": "0000", "message": "操作成功", "data": {"list": [{"goodsCode": "012001208", "billNo": "2610201155VI1D"}, {"goodsCode": "012001208", "billNo": "700552026102"}], "total": 15, "pageNum": 1, "pageSize": 100, "pages": 1}, "success": True}

        # 解析单页响应。
        rows, total, headers = platform.parse_one_page_sample(sample)

        # 断言数据行与总条数。
        self.assertEqual(len(rows), 2)
        self.assertEqual(total, 15)
        self.assertEqual(headers, ["goodsCode", "billNo"])

    # 定义日期区间要求验证。
    def test_date_range_requirements(self):

        """
        验证流向类要求日期区间且两类库存按快照口径。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言流向类要求日期区间。
        for data_type in ("配送流向", "购进流向", "纯销流向"):
            self.assertTrue(platform.requires_date_range(data_type), data_type)

        # 断言两类库存不要求日期区间。
        self.assertFalse(platform.requires_date_range("门店库存"))
        self.assertFalse(platform.requires_date_range("仓库库存"))

    # 定义未接入类型拒绝验证。
    def test_unsupported_type_is_rejected(self):

        """
        验证未接入数据类型抛出未接入异常。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言未知类型抛出异常。
        with self.assertRaises(NotImplementedError):
            platform.validate_data_type("报损流向")

    # 定义分页容量配置验证。
    def test_page_size_within_server_limit(self):

        """
        验证分页大小取服务器实测上限 100（500 被平台拒绝）。

        :return: None。
        :rtype: None
        """

        # 断言分页大小常量。
        self.assertEqual(NjyygyPlatform.PAGE_SIZE, 100)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
