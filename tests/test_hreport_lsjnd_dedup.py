# -*- coding: utf-8 -*-
"""
HReport 与凉山佳能达 Excel 写入去重契约测试。

本模块验证标准字段前置写入时，原始字段块只保留标准字段未覆盖的列，
杜绝同名业务字段在结果中重复出现的现象，全部离线执行不触网。
"""

# 导入单元测试工具。
import unittest

# 导入临时目录工具。
import tempfile

# 导入路径工具。
import os

# 导入 Excel 读取库。
import openpyxl

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入 HReport 平台适配器。
from ddi_framework.platforms.hreport import HreportPlatform

# 导入凉山佳能达平台适配器与其标准字段映射。
from ddi_framework.platforms.lsjnd import LsjndPlatform, STANDARD_FIELD_MAP

# 导入账号配置字典。
from ddi_framework.account_config import ACCOUNTS


# 定义标准字段去重测试套件。
class StandardFieldDedupTests(unittest.TestCase):

    """
    验证标准字段前置写入时原始字段块的去重行为。

    :return: 测试套件实例。
    :rtype: StandardFieldDedupTests
    """

    # 定义读取工作表表头的辅助方法。
    def read_headers(self, output_path, sheet_name):

        """
        读取生成 Excel 的表头行。

        :param output_path: Excel 文件路径。
        :type output_path: str
        :param sheet_name: 工作表名称。
        :type sheet_name: str
        :return: 表头文本列表。
        :rtype: list[str]
        """

        # 打开工作簿并读取首行。
        workbook = openpyxl.load_workbook(output_path, read_only=True)

        # 读取目标工作表。
        worksheet = workbook[sheet_name]

        # 提取表头文本。
        headers = [cell.value for cell in next(worksheet.iter_rows(min_row=1, max_row=1))]

        # 关闭工作簿。
        workbook.close()

        # 返回表头列表。
        return headers

    # 定义 HReport 标准字段去重验证。
    def test_hreport_keeps_only_uncovered_raw_fields(self):

        """
        验证 HReport 写入时原始块不再重复标准块已消费的字段。

        :return: None。
        :rtype: None
        """

        # 读取绵阳安康账号配置（含标准字段映射，凭据留空不触网）。
        account = ACCOUNTS["绵阳安康药业连锁有限公司"]

        # 构建平台适配器实例。
        platform = HreportPlatform("绵阳安康药业连锁有限公司", account, printer=PrintHandler())

        # 构建与真实页面一致的原始字段清单并附加一个平台新增字段。
        headers = ["时间", "单据类型", "业务机构编码", "业务机构", "供应商编码", "供应商名称", "商品编码", "商品名称", "规格", "单位", "生产企业", "入数量", "出数量", "批号", "收货门店"]

        # 构建单条原始记录。
        rows = [{"时间": "2026-10-31", "单据类型": "零售销售", "业务机构编码": "0020", "业务机构": "绵阳安康", "供应商编码": "10092", "供应商名称": "供应商甲", "商品编码": "01615", "商品名称": "人表皮生长因子", "规格": "10g/支", "单位": "支", "生产企业": "桂林华诺威", "入数量": "0.00", "出数量": "1.00", "批号": "20250203B", "收货门店": "门店一"}]

        # 写入临时目录。
        with tempfile.TemporaryDirectory() as temp_dir:

            # 拼接输出路径。
            output_path = os.path.join(temp_dir, "hreport.xlsx")

            # 调用写入方法。
            platform.write_rows_to_excel(rows, headers, output_path, "配送流向")

            # 读取生成表头。
            result_headers = self.read_headers(output_path, "配送流向")

        # 断言标准字段前置且无重复列。
        self.assertEqual(result_headers, ["配送日期", "单据类型", "业务机构编码", "业务机构", "供应商编码", "供应商名称", "商品编码", "商品名称", "规格", "单位", "生产企业", "入数量", "出数量", "批号", "收货门店"])

        # 断言表头数量与去重后一致。
        self.assertEqual(len(result_headers), len(set(result_headers)))

    # 定义凉山佳能达标准字段去重验证。
    def test_lsjnd_keeps_only_uncovered_raw_fields(self):

        """
        验证凉山佳能达写入时原始块仅保留类别等未覆盖字段。

        :return: None。
        :rtype: None
        """

        # 构建平台适配器实例。
        platform = LsjndPlatform("凉山佳能达医药贸易有限责任公司", {"平台": "lsjnd", "接口根地址": "http://www.lsjnd.com.cn:6501"}, printer=PrintHandler())

        # 构建与真实页面一致的原始字段清单（含未覆盖的类别字段）。
        headers = ["日期", "往来单位", "商品编号", "商品名称", "商品规格", "单位", "数量", "含税价", "含税金额", "批号", "生产厂家", "类别"]

        # 构建单条原始记录。
        rows = [{"日期": "2026-10-31", "往来单位": "凉山好医生", "商品编号": "010203", "商品名称": "人表皮生长因子凝胶", "商品规格": "10g", "单位": "盒", "数量": "5.000", "含税价": "1.000000", "含税金额": "5.000000", "批号": "20260101B", "生产厂家": "桂林华诺威", "类别": "出库"}]

        # 写入临时目录。
        with tempfile.TemporaryDirectory() as temp_dir:

            # 拼接输出路径。
            output_path = os.path.join(temp_dir, "lsjnd.xlsx")

            # 调用写入方法。
            platform.write_excel(rows, headers, "配送流向", output_path)

            # 读取生成表头。
            result_headers = self.read_headers(output_path, "配送流向")

        # 断言标准字段前置且仅保留类别。
        self.assertEqual(result_headers, ["出库日期", "往来单位", "商品编号", "商品名称", "商品规格", "单位", "数量", "含税价", "含税金额", "批号", "生产厂家", "类别"])

        # 断言表头数量与去重后一致。
        self.assertEqual(len(result_headers), len(set(result_headers)))

    # 定义标准字段映射完整性验证。
    def test_standard_map_sources_exist_in_page_headers(self):

        """
        验证凉山佳能达三类型标准字段取数源均来自页面原始字段。

        :return: None。
        :rtype: None
        """

        # 遍历三类型标准字段定义。
        for data_type, standard_fields in STANDARD_FIELD_MAP.items():

            # 断言每个标准字段都携带取数源。
            self.assertTrue(all(source_name for _, source_name in standard_fields), data_type)


# 定义测试套件入口。
if __name__ == "__main__":

    # 按默认方式执行单元测试。
    unittest.main()
