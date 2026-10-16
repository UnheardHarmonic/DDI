# -*- coding: utf-8 -*-
"""
DDI 统一任务领域模型与动态字段契约测试。

本模块验证日期预设、数据类型选择、文件命名和跨分页动态字段写入行为。
"""

# 导入日期工具。
from datetime import date

# 导入临时目录工具。
import tempfile

# 导入单元测试工具。
import unittest

# 导入日期时间模块。
from datetime import datetime

# 导入 Excel 工作簿读取工具。
from openpyxl import load_workbook

# 导入下载命名工具。
from ddi_framework.download_watcher import DownloadWatcher

# 导入动态字段收集器。
from ddi_framework.raw_fields import DynamicFieldCollector

# 导入动态字段 Excel 写入函数。
from ddi_framework.raw_fields import write_dynamic_raw_excel

# 导入正式原始 Excel 写入函数。
from ddi_framework.raw_fields import write_formal_raw_excel

# 导入日期范围对象。
from ddi_framework.task_core import DateRangeSpec

# 导入界面数据类型大类汇总函数。
from ddi_framework.task_core import list_data_type_categories

# 导入商业数据类型选择函数。
from ddi_framework.task_core import resolve_company_data_type_selection

# 导入统一任务请求对象。
from ddi_framework.task_core import TaskRequest


# 定义统一任务领域模型测试类。
class TaskDomainTests(unittest.TestCase):

    """
    验证三入口共享的任务领域规则。

    :return: None。
    :rtype: None
    """

    # 定义日期预设测试方法。
    def test_date_modes_resolve_expected_ranges(self):

        """
        验证上月整月和上月一日至今天预设范围。

        :return: None。
        :rtype: None
        """

        # 按固定今天计算上月整月范围。
        full_range = DateRangeSpec.from_mode("previous_month_full", today=date(2026, 9, 3))

        # 按固定今天计算上月一日至今天范围。
        current_range = DateRangeSpec.from_mode("previous_month_to_today", today=date(2026, 9, 3))

        # 断言整月范围正确。
        self.assertEqual((full_range.start_date, full_range.end_date, full_range.is_customized), ("2026-08-01", "2026-08-31", False))

        # 断言跨月核对范围正确。
        self.assertEqual((current_range.start_date, current_range.end_date, current_range.is_customized), ("2026-08-01", "2026-09-03", False))

        # 断言逆序日期范围被拒绝。
        with self.assertRaises(ValueError):

            # 构造不合法的自定义日期范围。
            DateRangeSpec.from_mode("custom", "2026-09-03", "2026-08-01")

    # 定义文件命名测试方法。
    def test_file_name_distinguishes_range_and_snapshot(self):

        """
        验证文件名使用完整范围且仅显式快照库存使用快照标签。

        :return: None。
        :rtype: None
        """

        # 创建无下载目录依赖的命名工具。
        watcher = DownloadWatcher("")

        # 构建上月整月流向文件名。
        full_name = watcher.build_target_name("测试商业", "配送流向", start_date="2026-08-01", end_date="2026-08-31", date_mode="previous_month_full")

        # 构建日期过滤库存文件名。
        inventory_range_name = watcher.build_target_name("测试商业", "门店库存", start_date="2026-08-01", end_date="2026-09-03", date_mode="previous_month_to_today")

        # 构建当前快照库存文件名。
        snapshot_name = watcher.build_target_name("测试商业", "库存", snapshot_date="2026-09-03")

        # 断言整月命名格式正确。
        self.assertEqual(full_name, "「DDI」测试商业｜整月｜2026.08.01~2026.08.31｜配送流向.xlsx")

        # 断言库存类即使携带日期过滤也使用导出当天快照命名。
        today_label = datetime.now().strftime("%Y.%m.%d")

        # 断言快照标签为当天日期。
        self.assertEqual(inventory_range_name, f"「DDI」测试商业｜快照｜{today_label}｜门店库存.xlsx")

        # 断言显式快照库存使用快照命名。
        self.assertEqual(snapshot_name, "「DDI」测试商业｜快照｜2026.09.03｜库存.xlsx")

    # 定义商业跳过选择测试方法。
    def test_unsupported_type_is_skipped_without_blocking_supported_type(self):

        """
        验证商业未声明的数据类型仅被跳过并附带原因。

        :return: None。
        :rtype: None
        """

        # 构造两家商业的能力声明。
        accounts = {"甲商业": {"数据类型列表": ["库存", "配送流向"]}, "乙商业": {"数据类型列表": ["配送流向"]}}

        # 汇总全局选择在每家商业中的实际结果。
        selections = resolve_company_data_type_selection(accounts, ["甲商业", "乙商业"], ("库存", "配送流向"))

        # 断言甲商业执行全部请求类型。
        self.assertEqual(selections["甲商业"].effective_types, ("库存", "配送流向"))

        # 断言乙商业保留可执行类型。
        self.assertEqual(selections["乙商业"].effective_types, ("配送流向",))

        # 断言乙商业记录库存跳过原因。
        self.assertEqual(selections["乙商业"].skipped_types["库存"], "商业账号配置未声明该数据类型")

    # 定义数据类型大类归并测试方法。
    def test_data_type_categories_collapse_inventory_and_pure_sale_aliases(self):

        """
        验证库存层级和纯销别名只在界面呈现一个业务大类。

        :return: None。
        :rtype: None
        """

        # 构造包含库存层级与纯销别名的商业配置。
        accounts = {"甲商业": {"数据类型列表": ["门店库存", "大仓库存", "仓库库存", "纯销"]}, "乙商业": {"数据类型列表": ["总部库存", "纯销流向"]}}

        # 汇总界面展示数据类型大类。
        categories = list_data_type_categories(accounts)

        # 断言库存别名只保留一个库存大类。
        self.assertEqual(categories.count("库存"), 1)

        # 断言纯销别名只保留纯销流向大类。
        self.assertEqual(categories.count("纯销流向"), 1)

        # 断言界面不再出现库存层级或纯销短名称。
        self.assertNotIn("门店库存", categories)
        self.assertNotIn("大仓库存", categories)
        self.assertNotIn("仓库库存", categories)
        self.assertNotIn("总部库存", categories)
        self.assertNotIn("纯销", categories)

    # 定义命令行数据类型兼容测试方法。
    def test_task_request_parses_comma_separated_data_types(self):

        """
        验证旧版单参数会统一转换为去重后的多选类型。

        :return: None。
        :rtype: None
        """

        # 构造使用旧版逗号分隔参数的任务请求。
        request = TaskRequest("query_excel", "库存,配送流向,库存", "2026-08-01", "2026-08-31", "cookies", "outputs", "logs", 1)

        # 断言请求内部保存去重后的多选类型。
        self.assertEqual(request.data_types, ("库存", "配送流向"))

    # 定义动态字段契约测试方法。
    def test_dynamic_fields_are_merged_and_metadata_sheet_is_hidden(self):

        """
        验证跨分页新增字段保留、缺失字段补空和元数据页隐藏。

        :return: None。
        :rtype: None
        """

        # 构造含第二页新增字段的字段收集器。
        collector = DynamicFieldCollector({"customer": "客户名称"})

        # 合并两页不完全相同的原始响应。
        table = collector.collect([{"page": 1, "headers": [{"key": "customer", "note": "客户备注"}, {"key": "qty", "title": "数量"}], "rows": [{"customer": "甲", "qty": 1}]}, {"page": 2, "headers": [{"key": "customer"}, {"key": "secondary_company", "note": "二级商业"}], "rows": [{"customer": "乙", "secondary_company": "丙"}]}])

        # 断言新增字段追加在既有字段之后。
        self.assertEqual([column["key"] for column in table.columns], ["customer", "qty", "secondary_company"])

        # 断言配置标题优先于接口备注。
        self.assertEqual(table.columns[0]["title"], "客户名称")

        # 断言第二页缺失数量字段补为空值。
        self.assertEqual(table.rows[1]["qty"], "")

        # 创建临时目录承载 Excel 文件。
        with tempfile.TemporaryDirectory() as directory:

            # 构造目标工作簿路径。
            file_path = f"{directory}/动态字段.xlsx"

            # 写入原始数据和隐藏元数据页。
            write_dynamic_raw_excel(file_path, table)

            # 读取写入后的工作簿。
            workbook = load_workbook(file_path)

            # 断言原始表保留动态字段标题。
            self.assertEqual([cell.value for cell in workbook["原始数据"][1]], ["客户名称", "数量", "二级商业"])

            # 断言字段元数据页不会干扰业务人员查看。
            self.assertEqual(workbook["字段元数据"].sheet_state, "hidden")

    # 定义正式原始字段契约测试方法。
    def test_formal_raw_excel_preserves_duplicate_titles_and_source_order(self):

        """
        验证正式原始 Excel 保留接口标题文本、重复标题和字段顺序。

        :return: None。
        :rtype: None
        """

        # 构造含重复标题的接口字段元数据。
        headers = [{"key": "detail_code", "title": "明细"}, {"key": "detail_name", "title": "明细"}, {"key": "quantity", "title": "数量"}]

        # 构造与接口字段顺序一致的原始记录。
        rows = [{"detail_code": "A01", "detail_name": "测试明细", "quantity": 5}]

        # 创建临时目录承载正式原始 Excel 文件。
        with tempfile.TemporaryDirectory() as directory:

            # 构造正式原始 Excel 文件路径。
            file_path = f"{directory}/正式原始.xlsx"

            # 写入保持接口字段契约的正式原始 Excel。
            write_formal_raw_excel(file_path, headers, rows, sheet_name="配送流向")

            # 打开生成的工作簿以读取数据和工作表状态。
            workbook = load_workbook(file_path)

            # 读取正式原始数据工作表。
            worksheet = workbook["配送流向"]

            # 读取正式原始标题行。
            excel_headers = [cell.value for cell in next(worksheet.iter_rows(min_row=1, max_row=1))]

            # 读取字段元数据工作表的隐藏状态。
            metadata_sheet_state = workbook["字段元数据"].sheet_state

            # 读取正式原始首条数据行。
            excel_row = [cell.value for cell in next(worksheet.iter_rows(min_row=2, max_row=2))]

            # 关闭已读取的工作簿。
            workbook.close()

        # 断言正式原始标题不改名且允许重复。
        self.assertEqual(excel_headers, ["明细", "明细", "数量"])

        # 断言正式原始数据严格匹配字段顺序。
        self.assertEqual(excel_row, ["A01", "测试明细", 5])

        # 断言正式原始文件也提供隐藏字段元数据页。
        self.assertEqual(metadata_sheet_state, "hidden")


# 定义直接运行测试模块入口。
if __name__ == "__main__":

    # 执行本模块单元测试。
    unittest.main()
