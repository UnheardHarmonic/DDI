# -*- coding: utf-8 -*-
"""
下载目录监听与重命名工具。
"""

# 导入操作系统接口模块。
import os

# 导入时间模块。
import time

# 导入日期时间模块。
from datetime import datetime


class DownloadWatcher:
    """
    下载目录监听器。

    :param root_dir: 下载根目录。
    :type root_dir: str
    :return: 下载目录监听器实例。
    :rtype: DownloadWatcher
    """

    def __init__(self, root_dir):
        """
        初始化下载目录监听器。

        :param root_dir: 下载根目录。
        :type root_dir: str
        :return: None。
        :rtype: None
        """

        # 保存下载根目录。
        self.root_dir = root_dir

    def make_today_dir(self):
        """
        创建当天下载目录。

        :return: 当天下载目录路径。
        :rtype: str
        """

        # 生成当天目录名称。
        today_name = datetime.now().strftime("%Y%m%d")

        # 拼接当天目录路径。
        save_path = os.path.join(self.root_dir, today_name)

        # 创建当天目录。
        os.makedirs(save_path, exist_ok=True)

        # 返回当天目录路径。
        return save_path

    def snapshot(self, folder_path):
        """
        获取目录文件快照。

        :param folder_path: 目录路径。
        :type folder_path: str
        :return: 文件名集合。
        :rtype: set[str]
        """

        # 创建目录。
        os.makedirs(folder_path, exist_ok=True)

        # 返回当前文件集合。
        return set(os.listdir(folder_path))

    def wait_and_rename(self, folder_path, company_name, data_type, query_date=None, match_keyword=None, before_snapshot=None, timeout=120):
        """
        等待新增下载文件并重命名。

        :param folder_path: 下载目录路径。
        :type folder_path: str
        :param company_name: 商业公司名称。
        :type company_name: str
        :param data_type: 数据类型名称。
        :type data_type: str
        :param query_date: 查询日期。
        :type query_date: str | None
        :param match_keyword: 文件名匹配关键字。
        :type match_keyword: str | None
        :param before_snapshot: 下载前文件快照。
        :type before_snapshot: set[str] | None
        :param timeout: 超时秒数。
        :type timeout: int
        :return: 重命名后的文件路径。
        :rtype: str | None
        """

        # 创建目录。
        os.makedirs(folder_path, exist_ok=True)

        # 获取下载前快照。
        before_files = before_snapshot if before_snapshot is not None else self.snapshot(folder_path)

        # 记录开始时间。
        start_time = time.time()

        # 定义有效文件后缀。
        valid_extensions = (".xlsx", ".xls", ".csv", ".zip", ".rar", ".txt")

        # 循环等待新增文件。
        while time.time() - start_time < timeout:
            # 获取当前文件集合。
            current_files = set(os.listdir(folder_path))

            # 计算新增文件集合。
            new_files = current_files - before_files

            # 遍历新增文件。
            for filename in new_files:
                # 跳过临时下载文件。
                if self._is_temporary_file(filename):
                    continue

                # 跳过无效后缀文件。
                if not filename.lower().endswith(valid_extensions):
                    continue

                # 跳过未命中关键字的文件。
                if match_keyword and match_keyword not in filename:
                    continue

                # 执行文件重命名。
                return self.rename_file(folder_path, filename, company_name, data_type, query_date)

            # 等待下一轮扫描。
            time.sleep(1)

        # 超时返回空值。
        return None

    def rename_file(self, folder_path, filename, company_name, data_type, query_date=None):
        """
        重命名下载文件。

        :param folder_path: 下载目录路径。
        :type folder_path: str
        :param filename: 原始文件名。
        :type filename: str
        :param company_name: 商业公司名称。
        :type company_name: str
        :param data_type: 数据类型名称。
        :type data_type: str
        :param query_date: 查询日期。
        :type query_date: str | None
        :return: 重命名后的文件路径。
        :rtype: str
        """

        # 读取文件扩展名。
        extension = os.path.splitext(filename)[1]

        # 构建目标文件名。
        target_name = self.build_target_name(company_name, data_type, query_date, extension)

        # 拼接源文件路径。
        source_path = os.path.join(folder_path, filename)

        # 拼接目标文件路径。
        target_path = os.path.join(folder_path, target_name)

        # 等待文件占用释放。
        time.sleep(1)

        # 删除已存在的同名目标文件。
        if os.path.exists(target_path):
            os.remove(target_path)

        # 执行重命名。
        os.rename(source_path, target_path)

        # 返回目标文件路径。
        return target_path

    def build_target_name(self, company_name, data_type, query_date=None, extension=".xlsx"):
        """
        构建标准下载文件名。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param data_type: 数据类型名称。
        :type data_type: str
        :param query_date: 查询日期。
        :type query_date: str | None
        :param extension: 文件扩展名。
        :type extension: str
        :return: 标准下载文件名。
        :rtype: str
        """

        # 生成日期文案。
        date_label = self._format_date_label(data_type, query_date)

        # 生成导出文件商业名称。
        export_company_name = self._build_export_company_name(company_name)

        # 返回标准下载文件名。
        return f"{export_company_name}{date_label}{data_type}{extension}"

    def _build_export_company_name(self, company_name):
        """
        构建导出文件使用的商业名称前缀。

        :param company_name: 商业公司名称。
        :type company_name: str
        :return: 带 DDI 标识的商业名称。
        :rtype: str
        """

        # 返回带 DDI 标识的商业名称。
        return f"「DDI」{company_name}"

    def _format_date_label(self, data_type, query_date):
        """
        格式化文件名日期文案。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param query_date: 查询日期。
        :type query_date: str | None
        :return: 日期文案。
        :rtype: str
        """

        # 库存类使用当天日期。
        if "库存" in data_type:

            # 读取导出当天日期。
            date_text = datetime.now().strftime("%Y-%m-%d")

            # 尝试格式化库存日期文案。
            try:

                # 解析库存业务日期。
                date_obj = datetime.strptime(date_text, "%Y-%m-%d")

                # 返回库存日期文案。
                return f"{date_obj.year % 100}.{date_obj.month}.{date_obj.day}"

            # 处理库存日期解析失败。
            except Exception:

                # 返回原始日期文案。
                return date_text

        # 无查询日期时返回空文案。
        if not query_date:
            return ""

        # 尝试格式化月份文案。
        try:
            date_obj = datetime.strptime(query_date, "%Y-%m-%d")

            return f"{date_obj.year % 100}.{date_obj.month}月"

        except Exception:
            return query_date

    def _is_temporary_file(self, filename):
        """
        判断文件是否为临时下载文件。

        :param filename: 文件名。
        :type filename: str
        :return: 是否为临时文件。
        :rtype: bool
        """

        # 返回临时文件判断结果。
        return filename.endswith(".tmp") or filename.endswith(".crdownload") or filename.startswith("~$")
