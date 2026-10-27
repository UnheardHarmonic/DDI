# -*- coding: utf-8 -*-
"""
ABACUS 供应链系统平台适配器测试。

本模块验证商业专属页面字段配置决定正式 Excel 的标题和列顺序，并保留接口原始字段。

:return: 模块提供 ABACUS 平台适配器测试。
:rtype: None
"""

# 导入临时目录模块。
import tempfile

# 导入单元测试模块。
import unittest

# 导入 Excel 工作簿读取函数。
from openpyxl import load_workbook

# 导入账号配置集合。
from ddi_framework.account_config import ACCOUNTS

# 导入 ABACUS 平台适配器。
from ddi_framework.platforms.abacus import AbacusPlatform


# 定义 ABACUS 平台适配器测试类。
class AbacusPlatformTests(unittest.TestCase):

    """
    验证商业页面字段配置和正式 Excel 输出行为。

    :return: None。
    :rtype: None
    """

    # 定义配送页面字段顺序测试方法。
    def test_distribution_excel_uses_company_page_headers_and_order(self):

        """
        验证配送流向正式工作表严格使用商业页面字段标题和顺序。

        :return: None。
        :rtype: None
        """

        # 读取四川圣杰商业配置。
        account = ACCOUNTS["四川圣杰药业有限公司"]

        # 创建商业专属平台适配器。
        platform = AbacusPlatform("四川圣杰药业有限公司", account)

        # 构建接口原始字段定义。
        headers = [{"key": key, "title": key} for key in ("prvempid", "prvempdes", "dptid", "dptdes", "actdat", "gdsid", "gdsdes", "spc", "unit", "mfcfct", "bthno", "vlddat", "qty")]

        # 构建接口原始记录。
        rows = [{"prvempid": "P001", "prvempdes": "配送单位", "dptid": "D001", "dptdes": "门店甲", "actdat": "20260803", "gdsid": "G001", "gdsdes": "商品甲", "spc": "10mg", "unit": "盒", "mfcfct": "厂家甲", "bthno": "B001", "vlddat": "20271231", "qty": 12}]

        # 创建临时导出目录。
        with tempfile.TemporaryDirectory() as temporary_directory:

            # 拼接临时 Excel 文件路径。
            output_path = f"{temporary_directory}\\配送流向.xlsx"

            # 写入配送流向 Excel 文件。
            platform.write_rows_to_excel(rows, headers, "配送流向", output_path)

            # 加载写入后的 Excel 工作簿。
            workbook = load_workbook(output_path)

            # 读取正式页面工作表。
            worksheet = workbook["配送流向"]

            # 读取正式页面表头。
            page_headers = [cell.value for cell in worksheet[1]]

            # 断言页面表头严格匹配商业配置。
            self.assertEqual(page_headers, ["行号", "门店名称", "商品编码", "商品名称", "规格", "生产厂家", "发生日期", "批号", "有效期至", "数量"])

            # 断言页面数据严格按页面字段顺序写入。
            self.assertEqual([cell.value for cell in worksheet[2]], [1, "门店甲", "G001", "商品甲", "10mg", "厂家甲", "20260803", "B001", "20271231", 12])

            # 断言隐藏工作表保留接口原始字段。
            self.assertEqual(workbook["接口原始字段"].sheet_state, "hidden")

            # 断言接口原始字段包含批号真实字段键。
            self.assertIn("bthno", [cell.value for cell in workbook["接口原始字段"][1]])

            # 关闭 Excel 工作簿。
            workbook.close()

    # 定义页面字段配置缺失测试方法。
    def test_missing_page_columns_does_not_fall_back_to_shared_mapping(self):

        """
        验证缺少商业页面字段配置时拒绝使用公共字段映射。

        :return: None。
        :rtype: None
        """

        # 创建缺少页面字段配置的平台适配器。
        platform = AbacusPlatform("测试商业", {"平台": "abacus", "接口根地址": "http://example.test"})

        # 断言读取缺失配置时抛出明确异常。
        with self.assertRaisesRegex(RuntimeError, "未配置页面原始列"):

            # 读取未配置数据类型的页面字段。
            platform.resolve_page_columns("配送流向")
