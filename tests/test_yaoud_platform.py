# -*- coding: utf-8 -*-
"""
江苏大德隆药德平台（yaoud）接入契约测试。

本模块验证三家联营商业账号配置完整性、登录密码加密口径与浏览器抓包
密文逐字节一致、五类型报表编号映射、查询条件形态、商业作用域负载
和库存快照回溯语义，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入对称解密工具。
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS

# 导入药德平台适配器。
from ddi_framework.platforms.yaoud import YaoudPlatform

# 导入日志打印器。
from ddi_framework import PrintHandler


# 定义药德接入契约测试套件。
class YaoudPlatformTests(unittest.TestCase):

    """
    江苏大德隆药德平台接入契约测试。

    :return: 测试套件实例。
    :rtype: YaoudPlatformTests
    """

    # 定义类级商业名称与流向编号映射引用。
    EXPECTED_BUSINESSES = {
        "江苏舒福达医药有限公司": "1922",
        "江苏舒健大药房连锁有限公司": "1923",
        "江苏大德隆医药连锁有限公司": "1491",
        "苏州市采芝灵药房连锁有限公司": "1650",
    }

    # 定义类级商业名称与登录账号映射引用。
    EXPECTED_ACCOUNTS = {
        "江苏舒福达医药有限公司": "15751345245",
        "江苏舒健大药房连锁有限公司": "15751345245",
        "江苏大德隆医药连锁有限公司": "15751345245",
        "苏州市采芝灵药房连锁有限公司": "18936257595",
    }

    # 定义类级数据类型清单引用。
    EXPECTED_TYPES = ["配送流向", "购进流向", "纯销流向", "库存", "报损流向"]

    # 定义类级报表编号映射引用（与浏览器抓包一致）。
    EXPECTED_REPORT_IDS = {
        "库存": "247",
        "纯销流向": "251",
        "购进流向": "252",
        "配送流向": "253",
        "报损流向": "254",
    }

    # 定义平台适配器构建方法。
    def build_platform(self, company_name="江苏大德隆医药连锁有限公司"):

        """
        构建指定商业的适配器实例。

        :param company_name: 商业公司名称。
        :type company_name: str
        :return: 药德平台适配器实例。
        :rtype: YaoudPlatform
        """

        # 读取商业账号配置并构建适配器。
        return YaoudPlatform(company_name, ACCOUNTS[company_name], printer=PrintHandler())

    # 定义三家商业账号声明完整性验证。
    def test_three_business_accounts_are_declared(self):

        """
        验证各家商业账号声明平台归属、凭据覆盖与各自流向编号。

        :return: None。
        :rtype: None
        """

        # 遍历预期商业清单。
        for company_name, flow_id in self.EXPECTED_BUSINESSES.items():

            # 读取商业账号配置。
            account = ACCOUNTS[company_name]

            # 断言平台归属为药德平台。
            self.assertEqual(account["平台"], "yaoud", company_name)

            # 断言登录账号与约定一致。
            self.assertEqual(account["账号"], self.EXPECTED_ACCOUNTS[company_name], company_name)

            # 断言登录密码与约定一致。
            self.assertEqual(account["密码"], "Huanuowei123", company_name)

            # 断言商业作用域流向编号。
            self.assertEqual(account["供应商流向编号"], flow_id, company_name)

            # 断言数据类型清单与约定一致。
            self.assertEqual(account["数据类型列表"], self.EXPECTED_TYPES, company_name)

    # 定义登录密码加密口径验证。
    def test_password_encryption_matches_captured_ciphertext(self):

        """
        验证密码加密为 AES-CFB Base64 且与浏览器抓包密文逐字节一致。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 以抓包当次提交的十三位明文执行加密。
        captured_cipher_text = platform.encrypt_password("Huanuowei123]")

        # 断言密文与浏览器抓包表单密文一致。
        self.assertEqual(captured_cipher_text, "c5DUrD1txXyUrJMKkA==")

        # 以真实十二位明文执行加密并按前端同款口径解密还原。
        key_bytes = b"PITWDjRNQCQ4xUev"

        # 构建 AES-CFB-128 解密器。
        decryptor = Cipher(algorithms.AES(key_bytes), modes.CFB(key_bytes)).decryptor()

        # 解码并还原真实明文。
        plain = decryptor.update(base64.b64decode(platform.encrypt_password("Huanuowei123"))) + decryptor.finalize()

        # 断言解密结果与原始明文一致。
        self.assertEqual(plain.decode("latin-1"), "Huanuowei123")

    # 定义五类型报表编号映射验证。
    def test_report_ids_match_capture(self):

        """
        验证五类型报表编号与浏览器抓包地址一致。

        :return: None。
        :rtype: None
        """

        # 断言报表编号映射与约定一致。
        self.assertEqual(YaoudPlatform.REPORT_IDS, self.EXPECTED_REPORT_IDS)

    # 定义流向类查询条件形态验证。
    def test_flow_conditions_match_capture(self):

        """
        验证购进、配送、纯销的日期区间条件与页面请求一致。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 读取购进条件并断言字段与规则。
        purchase_conditions = platform.build_conditions("购进流向", "2026-01-01", "2026-10-22")
        self.assertEqual(purchase_conditions, [{"field": "入库日期|范围查询", "rule": "between", "val": ["2026-01-01", "2026-10-22"]}])

        # 读取配送条件并断言字段与规则。
        delivery_conditions = platform.build_conditions("配送流向", "2026-01-01", "2026-10-22")
        self.assertEqual(delivery_conditions, [{"field": "配送日期|范围查询", "rule": "between", "val": ["2026-01-01", "2026-10-22"]}])

        # 读取纯销条件并断言字段与规则。
        sale_conditions = platform.build_conditions("纯销流向", "2026-05-01", "2026-10-01")
        self.assertEqual(sale_conditions, [{"field": "销售日期|范围查询", "rule": "between", "val": ["2026-05-01", "2026-10-01"]}])

    # 定义库存快照条件形态验证。
    def test_inventory_conditions_match_capture(self):

        """
        验证库存单日等于条件组与页面请求一致。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 读取库存条件并断言双条件形态。
        inventory_conditions = platform.build_inventory_conditions("2026-10-22")
        self.assertEqual(inventory_conditions, [
            {"field": "inventoryTime", "rule": "eq", "val": "2026-10-22"},
            {"field": "范围查询|inventoryTime", "rule": "eq", "val": "2026-10-22"},
        ])

    # 定义报损全量口径验证。
    def test_loss_conditions_are_empty(self):

        """
        验证报损报表按全量口径不携带日期条件。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 读取报损条件并断言为空列表。
        self.assertEqual(platform.build_conditions("报损流向", "2026-01-01", "2026-10-22"), [])

    # 定义商业作用域负载验证。
    def test_query_payload_scopes_supplier_flow(self):

        """
        验证查询负载携带报表编号、商业作用域与分页口径。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform("江苏舒健大药房连锁有限公司")

        # 构建查询负载。
        payload = platform.build_query_payload("购进流向", platform.build_conditions("购进流向", "2026-01-01", "2026-10-22"), 1)

        # 断负载关键键值。
        self.assertEqual(payload["reportId"], "252")
        self.assertEqual(payload["current"], 1)
        self.assertEqual(payload["size"], YaoudPlatform.PAGE_SIZE)
        self.assertEqual(payload["reportSource"], 1)
        self.assertEqual(payload["extendParams"], {"supFlowId": "1923"})

        # 断言负载可完整序列化。
        self.assertTrue(json.dumps(payload, ensure_ascii=False))

    # 定义滑块校验密文形态验证。
    def test_slide_check_request_shapes(self):

        """
        验证滑块点位文本与二次校验密文的结构约定。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 构建固定 secretKey 的取图上下文。
        captcha_payload = {"token": "token-sample", "secretKey": "acE33T4QM2FR8fFY", "originalImage": b"", "jigsawImage": b""}

        # 构建校验请求与登录密文。
        check_query, captcha_verification = platform.build_slide_check_request(captcha_payload, 126.0)

        # 断言查询串包含校验类型与令牌。
        self.assertIn("captchaType=blockPuzzle", check_query)
        self.assertIn("token=token-sample", check_query)

        # 以固定密钥解出二次校验明文。
        from ddi_framework.captcha_solver import AesEcbEncryptor

        # 构建验证明文期望值。
        expected_plain = "token-sample---" + platform.build_point_json(126.0)

        # 断言密文可被同款加密器复原为期望明文。
        reencrypted = AesEcbEncryptor.encrypt_to_base64(expected_plain, "acE33T4QM2FR8fFY")
        self.assertEqual(captcha_verification, reencrypted)

    # 定义请求头形态验证。
    def test_headers_carry_client_and_tenant_marks(self):

        """
        验证公共头带商户端标记、认证头带 Bearer 令牌与租户编号。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例并注入令牌。
        platform = self.build_platform()
        platform.access_token = "token-sample"
        platform.tenant_id = "1"

        # 断言公共头商户端标记。
        self.assertEqual(platform.build_common_headers()["CLIENT-TOM"], "Y")

        # 读取认证请求头。
        auth_headers = platform.build_auth_headers()

        # 断言身份头为 Bearer 口径。
        self.assertEqual(auth_headers["Authorization"], "Bearer token-sample")

        # 断言租户头取值。
        self.assertEqual(auth_headers["TENANT-ID"], "1")

    # 定义日期区间要求验证。
    def test_date_range_requirements(self):

        """
        验证流向类要求日期区间且库存、报损按快照与全量口径。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = self.build_platform()

        # 断言流向类要求日期区间。
        for data_type in ("配送流向", "购进流向", "纯销流向"):
            self.assertTrue(platform.requires_date_range(data_type), data_type)

        # 断言库存与报损不要求日期区间。
        self.assertFalse(platform.requires_date_range("库存"))
        self.assertFalse(platform.requires_date_range("报损流向"))

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
            platform.validate_data_type("批发销售流向")


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
