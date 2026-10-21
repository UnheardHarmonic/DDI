# -*- coding: utf-8 -*-
"""
重庆和平药房连锁有限责任公司医药保健品分公司重药流向平台接入契约测试。

本模块验证和平账号配置完整性、密码加密对称性、五类型端点覆盖、
过滤模型形态和库存快照命名语义，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入重药流向平台适配器。
from ddi_framework.platforms.cqhp import CqhpPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义和平接入契约测试套件。
class CqhpPlatformTests(unittest.TestCase):

    """
    重庆和平重药流向平台接入契约测试。

    :return: 测试套件实例。
    :rtype: CqhpPlatformTests
    """

    # 定义类级账号配置引用。
    ACCOUNT_KEY = "重庆和平药房连锁有限责任公司医药保健品分公司"

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["纯销流向", "配送流向", "购进流向", "库存", "报损流向"]

    # 定义类级数据端点映射引用。
    EXPECTED_PATHS = {
        "纯销流向": "/server/retailHpTarget/page",
        "配送流向": "/server/headOfficeSalesHpTarget/page",
        "购进流向": "/server/headquartersWarehousingHpTarget/page",
        "库存": "/server/factInventoryflowHpTarget/page",
        "报损流向": "/server/factIncomestatementHpTarget/page",
    }

    # 定义平台适配器构建方法。
    def build_platform(self):

        """
        构建注入数据平台用户编号的适配器实例。

        :return: 和平平台适配器实例。
        :rtype: CqhpPlatform
        """

        # 读取和平账号配置并构建适配器。
        platform = CqhpPlatform(self.ACCOUNT_KEY, ACCOUNTS[self.ACCOUNT_KEY], printer=PrintHandler())

        # 注入数据平台用户编号模拟已登录状态。
        platform.data_user_id = "412824"

        # 返回适配器实例。
        return platform

    # 定义账号声明完整性验证。
    def test_account_declaration_is_complete(self):

        """
        验证和平账号声明包含平台归属、凭据覆盖与数据类型清单。

        :return: None。
        :rtype: None
        """

        # 读取和平账号配置。
        account = ACCOUNTS[self.ACCOUNT_KEY]

        # 断言平台归属为重药流向平台。
        self.assertEqual(account["平台"], "cqhp")

        # 断言认证与数据主机指向集团站点。
        self.assertIn("cqp-sxy-sso.cq-p.com.cn", account["认证站点地址"])
        self.assertIn("new-data-flow.cq-p.com.cn:8080", account["数据站点地址"])

        # 断言数据类型清单与约定一致。
        self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES)

    # 定义密码加密对称性验证。
    def test_password_encryption_round_trip(self):

        """
        验证密码加密为 DES-ECB Base64 且解密还原明文一致。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 以样例明文执行加密。
        cipher_text = platform.encrypt_password("Sample@2026")

        # 断言密文为合法 Base64 且还原一致。
        import base64

        # 导入对称解密工具并还原明文。
        from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
        from cryptography.hazmat.primitives.ciphers import Cipher, modes
        from cryptography.hazmat.primitives.padding import PKCS7

        # 解码密文字节流。
        raw = base64.b64decode(cipher_text)

        # 构建解密器并剥离填充。
        decryptor = Cipher(TripleDES(b"test1234"), modes.ECB()).decryptor()
        unpadder = PKCS7(64).unpadder()
        plain = unpadder.update(decryptor.update(raw) + decryptor.finalize()) + unpadder.finalize()

        # 断言解密结果与原始明文一致。
        self.assertEqual(plain.decode("utf-8"), "Sample@2026")

    # 定义五类型端点覆盖验证。
    def test_data_paths_cover_all_types(self):

        """
        验证五类型查询端点与页面抓包地址一致。

        :return: None。
        :rtype: None
        """

        # 断言端点映射与约定一致。
        self.assertEqual(CqhpPlatform.DATA_PATHS, self.EXPECTED_PATHS)

    # 定义过滤模型形态验证。
    def test_data_filter_shapes_match_capture(self):

        """
        验证各类型过滤模型字段与页面请求一致。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 读取纯销过滤模型并断言关键字段。
        retail_filter = platform.build_data_filter("纯销流向", "2026-10-01", "2026-10-21")
        self.assertEqual(retail_filter["outboundStartDate"], "2026-10-01")
        self.assertEqual(retail_filter["outboundEndDate"], "2026-10-21")
        self.assertEqual(retail_filter["userId"], "412824")

        # 读取购进过滤模型并断言日期字段。
        purchase_filter = platform.build_data_filter("购进流向", "2026-10-01", "2026-10-21")
        self.assertEqual(purchase_filter["inStcDateBegin"], "2026-10-01")
        self.assertEqual(purchase_filter["inStcDateEnd"], "2026-10-21")

        # 读取报损过滤模型并断言日期字段。
        loss_filter = platform.build_data_filter("报损流向", "2026-10-01", "2026-10-21")
        self.assertEqual(loss_filter["startTime"], "2026-10-01")
        self.assertEqual(loss_filter["endDate"], "2026-10-21")

        # 读取库存过滤模型并断言仅按用户快照查询。
        stock_filter = platform.build_data_filter("库存", None, None)
        self.assertEqual(stock_filter, {"userId": "412824"})

    # 定义数据请求头形态验证。
    def test_data_headers_carry_raw_token(self):

        """
        验证数据请求头以裸令牌承载身份并携带重定向声明头。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例并注入数据令牌。
        platform = self.build_platform()
        platform.data_token = "header-token-sample"

        # 构建数据请求头。
        headers = platform.build_data_headers()

        # 断言身份头为裸令牌无 Bearer 前缀。
        self.assertEqual(headers["Authorization"], "header-token-sample")

        # 断言重定向声明头存在。
        self.assertEqual(headers["Idm-Login-Redirect-Json"], "1")

    # 定义日期区间要求验证。
    def test_date_range_requirements(self):

        """
        验证流向类要求日期区间且库存快照同样声明区间能力。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言全部类型均要求日期区间。
        for data_type in self.EXPECTED_TYPES:
            self.assertTrue(platform.requires_date_range(data_type), data_type)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
