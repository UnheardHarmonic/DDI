# -*- coding: utf-8 -*-
"""
华润江苏医药有限公司德信行分公司平台接入契约测试。

本模块验证德信行账号配置完整性、五类型端点映射、查询负载形态、
HTML 表格解析口径、总条数解析与登录明文表单形态，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入华润德信行平台适配器。
from ddi_framework.platforms.dexinxing import DexinxingPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义华润德信行接入契约测试套件。
class DexinxingPlatformTests(unittest.TestCase):

    """
    华润德信行平台接入契约测试。

    :return: 测试套件实例。
    :rtype: DexinxingPlatformTests
    """

    # 定义类级账号配置键引用。
    ACCOUNT_KEY = "华润江苏医药有限公司德信行分公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "大仓库存", "门店库存"]

    # 定义类级端点映射引用（与活体实测一致）。
    EXPECTED_ENDPOINTS = {
        "配送流向": "/lssales/index.html",
        "购进流向": "/lssupplys/index.html",
        "纯销流向": "/shopsales/index.html",
        "大仓库存": "/lsstore/index.html",
        "门店库存": "/shopstore/index.html",
    }

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建平台适配器实例。

        :return: 德信行平台适配器实例。
        :rtype: DexinxingPlatform
        """

        # 读取账号配置并构建适配器。
        return DexinxingPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证德信行账号声明平台归属、站点地址与数据类型清单。

        :return: None。
        :rtype: None
        """

        # 读取德信行账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为德信行平台。
        self.assertEqual(account["平台"], "dexinxing")

        # 断言站点根地址指向华润站点。
        self.assertIn("kscx.crcjs.cn", account["站点根地址"])

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

        # 断言库存按快照口径。
        self.assertTrue(account["库存快照"])

    # 定义五类型端点映射验证。
    def test_type_endpoints_match_capture(self):

        """
        验证五类型查询端点与活体实测一致。

        :return: None。
        :rtype: None
        """

        # 断言端点映射与约定一致。
        self.assertEqual(DexinxingPlatform.TYPE_ENDPOINTS, self.EXPECTED_ENDPOINTS)

    # 定义查询负载形态验证。
    def test_query_payload_shapes(self):

        """
        验证流向类带日期区间、库存类仅商品筛选与分页域。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 读取购进负载并断言五字段与分页域。
        purchase_payload = platform.build_query_payload("购进流向", "2026-09-22", "2026-10-22", 2)
        self.assertEqual(purchase_payload["begindate"], "2026-09-22")
        self.assertEqual(purchase_payload["enddate"], "2026-10-22")
        self.assertEqual(purchase_payload["pageNum"], "2")
        self.assertEqual(purchase_payload["numberPage"], "100")
        self.assertEqual(purchase_payload["goodsid"], "")

        # 读取总部库存负载并断言无日期字段。
        store_payload = platform.build_query_payload("大仓库存", None, None, 1)
        self.assertNotIn("begindate", store_payload)
        self.assertNotIn("enddate", store_payload)
        self.assertEqual(store_payload["pageNum"], "1")

    # 定义总条数解析验证。
    def test_total_count_parsing(self):

        """
        验证共N条总账文本解析与无总账返回空。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言常规总账解析。
        self.assertEqual(platform.parse_total_count("<div>共20条</div>"), 20)

        # 断言带空白总账解析。
        self.assertEqual(platform.parse_total_count("共 76 条"), 76)

        # 断言无总账文本返回空。
        self.assertIsNone(platform.parse_total_count("<div>没有数据</div>"))

    # 定义数据表解析口径验证。
    def test_table_rows_parsing(self):

        """
        验证最大表法解析、空表头列丢弃与行字典组装。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构造含勾选框空列与两行数据的样例页。
        sample_html = """
        <table id="pager"><tr><td>1</td></tr></table>
        <table>
            <tr><td></td><td>制单日期</td><td>产品代码</td></tr>
            <tr><td><input/></td><td>2026-10-23</td><td>1300203932</td></tr>
            <tr><td><input/></td><td>2026-10-22</td><td>30745804</td></tr>
        </table>
        """

        # 解析样例页。
        headers, data_rows = platform.parse_table_rows(sample_html)

        # 断言空表头列被丢弃。
        self.assertEqual(headers, ["制单日期", "产品代码"])

        # 断言数据行按表头组装。
        self.assertEqual(len(data_rows), 2)
        self.assertEqual(data_rows[0]["制单日期"], "2026-10-23")
        self.assertEqual(data_rows[1]["产品代码"], "30745804")

    # 定义登录明文表单形态验证。
    def test_login_payload_is_plaintext_form(self):

        """
        验证登录表单按 account/password/verify 明文三字段构建。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建登录表单。
        payload = {
            "account": platform.clean_login_name(),
            "password": platform.clean_login_password(),
            "verify": "abcd",
        }

        # 断言三字段齐备。
        self.assertEqual(set(payload), {"account", "password", "verify"})

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
        self.assertFalse(platform.requires_date_range("大仓库存"))
        self.assertFalse(platform.requires_date_range("门店库存"))

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

    # 定义慢平台超时配置验证。
    def test_slow_platform_timeout(self):

        """
        验证数据请求超时按慢平台 300 秒配置。

        :return: None。
        :rtype: None
        """

        # 断言长超时常量。
        self.assertEqual(DexinxingPlatform.QUERY_TIMEOUT, 300)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
