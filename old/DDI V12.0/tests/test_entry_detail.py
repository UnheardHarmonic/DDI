# -*- coding: utf-8 -*-
"""
商业录入明细聚合模块测试。
"""

# 导入 JSON 编解码模块。
import json

# 导入临时目录模块。
import tempfile

# 导入单元测试模块。
import unittest

# 导入路径处理工具。
from pathlib import Path

# 导入 Excel 工作簿读取函数。
from openpyxl import Workbook

# 导入 Excel 工作簿读取函数。
from openpyxl import load_workbook

# 导入录入明细标准字段。
from ddi_framework.entry_detail import ENTRY_DETAIL_FIELDS

# 导入录入明细采集函数。
from ddi_framework.entry_detail import collect_entry_detail_rows

# 导入录入明细生成函数。
from ddi_framework.entry_detail import generate_entry_detail_excel

# 导入商业映射加载函数。
from ddi_framework.entry_detail import load_entry_detail_mapping


# 定义录入明细测试类。
class EntryDetailTests(unittest.TestCase):

    """
    验证商业录入明细配置、字段转换和工作簿聚合行为。
    """

    # 定义测试环境初始化方法。
    def setUp(self):

        """
        创建临时映射目录、原始流向工作簿和输出目录。

        :return: None。
        :rtype: None
        """

        # 创建独立临时目录。
        self.temp_directory = tempfile.TemporaryDirectory()

        # 保存临时目录路径。
        self.base_path = Path(self.temp_directory.name)

        # 创建映射目录。
        self.mapping_path = self.base_path / "copy_mappings"

        # 创建输出目录。
        self.output_path = self.base_path / "output"

        # 创建映射目录。
        self.mapping_path.mkdir()

        # 创建输出目录。
        self.output_path.mkdir()

    # 定义测试环境清理方法。
    def tearDown(self):

        """
        删除当前测试临时目录。

        :return: None。
        :rtype: None
        """

        # 释放临时目录。
        self.temp_directory.cleanup()

    # 定义映射配置写入辅助方法。
    def write_mapping(self, company_name, fields, rules=None, enabled=True):

        """
        写入测试商业映射 JSON。

        :param company_name: 测试商业名称。
        :type company_name: str
        :param fields: 配送流向字段映射。
        :type fields: dict
        :param rules: 可选行级规则。
        :type rules: list[dict] | None
        :param enabled: 是否启用映射。
        :type enabled: bool
        :return: 映射文件路径。
        :rtype: pathlib.Path
        """

        # 构建测试映射对象。
        mapping = {"schema_version": 1, "company_name": company_name, "enabled": enabled, "data_types": {"配送流向": {"fields": fields, "rules": rules or []}}}

        # 构建测试映射文件路径。
        mapping_file = self.mapping_path / f"{company_name}.json"

        # 写入 UTF-8 映射文件。
        mapping_file.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

        # 返回测试映射文件路径。
        return mapping_file

    # 定义原始工作簿写入辅助方法。
    def write_source(self, filename, headers, rows):

        """
        创建测试原始流向 Excel。

        :param filename: 原始文件名。
        :type filename: str
        :param headers: 原始表头列表。
        :type headers: list[str]
        :param rows: 原始数据行列表。
        :type rows: list[list[object]]
        :return: 原始工作簿路径。
        :rtype: pathlib.Path
        """

        # 创建原始工作簿。
        workbook = Workbook()

        # 读取活动工作表。
        worksheet = workbook.active

        # 写入原始表头。
        worksheet.append(headers)

        # 写入原始数据行。
        for row in rows:

            # 追加当前原始数据行。
            worksheet.append(row)

        # 构建原始工作簿路径。
        source_path = self.base_path / filename

        # 保存原始工作簿。
        workbook.save(source_path)

        # 关闭原始工作簿。
        workbook.close()

        # 返回原始工作簿路径。
        return source_path

    # 定义直接映射和来源表测试方法。
    def test_direct_mapping_preserves_source_file_name(self):

        """
        验证直接映射输出字段并写入原始文件名。

        :return: None。
        :rtype: None
        """

        # 定义测试商业名称。
        company_name = "测试商业直接映射"

        # 创建测试原始流向文件。
        source_path = self.write_source("配送流向甲.xlsx", ["规格", "日期", "客户", "数量", "单价", "批号"], [["10mg", "2026-08-01", "甲客户", 10, 2.5, "A1"]])

        # 写入测试商业映射。
        self.write_mapping(company_name, {"规格": {"operation": "direct", "source": "规格"}, "流向日期": {"operation": "to_date", "source": "日期"}, "买方-原始简称": {"operation": "direct", "source": "客户"}, "销售数量（支）": {"operation": "direct", "source": "数量", "transforms": ["to_number"]}, "销售数量（盒）": {}, "供货单价": {"operation": "to_number", "source": "单价"}, "批号": {"operation": "direct", "source": "批号"}})

        # 读取测试映射配置。
        mapping = load_entry_detail_mapping(company_name, self.mapping_path)

        # 采集测试录入明细行。
        result = collect_entry_detail_rows(company_name, [{"path": str(source_path), "data_type": "配送流向"}], mapping)

        # 验证采集行数量。
        self.assertEqual(result["记录数量"], 1)

        # 验证标准字段值。
        self.assertEqual(result["行"][0]["规格"], "10mg")

        # 验证日期标准化结果。
        self.assertEqual(result["行"][0]["流向日期"], "2026-08-01")

        # 验证来源文件名。
        self.assertEqual(result["行"][0]["来源表"], "配送流向甲.xlsx")

    # 定义退货符号和正负列合并测试方法。
    def test_signed_and_difference_quantity_rules(self):

        """
        验证退货规则和正负分列规则均按配置计算。

        :return: None。
        :rtype: None
        """

        # 定义测试商业名称。
        signed_company = "测试商业退货"

        # 创建退货原始文件。
        signed_source = self.write_source("退货流向.xlsx", ["规格", "客户", "数量", "本单性质"], [["10mg", "甲客户", 10, "退货"]])

        # 写入退货映射配置。
        self.write_mapping(signed_company, {"规格": {"source": "规格"}, "买方-原始简称": {"source": "客户"}, "销售数量（支）": {"operation": "signed", "source": "数量", "direction_source": "本单性质", "negative_values": ["退货"], "positive_values": ["销售"]}})

        # 读取退货映射配置。
        signed_mapping = load_entry_detail_mapping(signed_company, self.mapping_path)

        # 采集退货行。
        signed_result = collect_entry_detail_rows(signed_company, [str(signed_source)], signed_mapping)

        # 验证退货数量为负数。
        self.assertEqual(signed_result["行"][0]["销售数量（支）"], -10)

        # 定义正负分列商业名称。
        difference_company = "测试商业正负分列"

        # 创建正负分列原始文件。
        difference_source = self.write_source("正负流向.xlsx", ["规格", "客户", "销售数", "退货数"], [["20mg", "乙客户", 15, 4]])

        # 写入正负分列映射配置。
        self.write_mapping(difference_company, {"规格": {"source": "规格"}, "买方-原始简称": {"source": "客户"}, "销售数量（支）": {"operation": "difference", "positive_sources": ["销售数"], "negative_sources": ["退货数"]}})

        # 读取正负分列映射配置。
        difference_mapping = load_entry_detail_mapping(difference_company, self.mapping_path)

        # 采集正负分列行。
        difference_result = collect_entry_detail_rows(difference_company, [str(difference_source)], difference_mapping)

        # 验证正数减负数结果。
        self.assertEqual(difference_result["行"][0]["销售数量（支）"], 11)

    # 定义聚合工作簿结构测试方法。
    def test_generation_creates_one_workbook_with_audit_sheets(self):

        """
        验证多个原始文件聚合到一个录入明细工作簿。

        :return: None。
        :rtype: None
        """

        # 定义测试商业名称。
        company_name = "测试商业聚合"

        # 创建两个原始流向文件。
        source_a = self.write_source("配送甲.xlsx", ["规格", "数量"], [["A", 1]])

        # 创建第二个原始流向文件。
        source_b = self.write_source("配送乙.xlsx", ["规格", "数量"], [["B", 2]])

        # 写入聚合映射配置。
        self.write_mapping(company_name, {"规格": {"source": "规格"}, "销售数量（支）": {"source": "数量", "transforms": ["to_number"]}})

        # 生成聚合录入明细。
        result = generate_entry_detail_excel(company_name, [{"path": str(source_a), "data_type": "配送流向"}, {"path": str(source_b), "data_type": "配送流向"}], str(self.output_path), self.mapping_path)

        # 验证输出文件存在。
        self.assertTrue(result["输出文件"])

        # 验证输出文件命名。
        self.assertTrue(result["输出文件"].endswith("测试商业聚合_录入明细.xlsx"))

        # 读取生成工作簿。
        workbook = load_workbook(result["输出文件"], data_only=True)

        # 验证工作表名称。
        self.assertEqual(workbook.sheetnames, ["录入明细", "字段映射", "处理说明"])

        # 读取录入明细工作表。
        worksheet = workbook["录入明细"]

        # 验证主表字段顺序。
        self.assertEqual([cell.value for cell in worksheet[1]], ENTRY_DETAIL_FIELDS)

        # 验证聚合记录数量。
        self.assertEqual(worksheet.max_row, 3)

        # 验证第二个源文件来源标记。
        self.assertEqual(worksheet.cell(row=3, column=8).value, "配送乙.xlsx")

        # 关闭生成工作簿。
        workbook.close()

    # 定义未启用映射安全行为测试方法。
    def test_disabled_mapping_keeps_raw_files_without_entry_workbook(self):

        """
        验证未启用商业映射不会生成错误录入数据。

        :return: None。
        :rtype: None
        """

        # 定义测试商业名称。
        company_name = "测试商业未启用"

        # 创建原始流向文件。
        source_path = self.write_source("配送原始.xlsx", ["未知字段"], [["原始值"]])

        # 写入关闭状态映射配置。
        self.write_mapping(company_name, {}, enabled=False)

        # 尝试生成录入明细。
        result = generate_entry_detail_excel(company_name, [str(source_path)], str(self.output_path), self.mapping_path)

        # 验证未生成录入明细文件。
        self.assertEqual(result["输出文件"], "")

        # 验证原始文件仍然存在。
        self.assertTrue(source_path.exists())


# 直接运行当前测试模块时执行单元测试。
if __name__ == "__main__":

    # 启动单元测试运行器。
    unittest.main()
