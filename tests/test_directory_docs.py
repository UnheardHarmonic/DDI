# -*- coding: utf-8 -*-
"""
受管目录说明自愈服务测试。

本模块验证目录说明在首次启动时创建、后续启动时保留人工维护内容，并覆盖所有受管目录。

:return: 模块提供自动化测试用例。
:rtype: None
"""

# 导入临时目录工具。
import tempfile

# 导入单元测试框架。
import unittest

# 导入路径对象类型。
from pathlib import Path

# 导入目录说明模板与补齐函数。
from ddi_framework.directory_docs import DIRECTORY_DOCUMENTS, ensure_directory_documents


# 定义目录说明服务测试类。
class DirectoryDocumentationTests(unittest.TestCase):
    """
    验证受管目录用途说明的自动创建与内容保护行为。

    :return: None
    :rtype: None
    """

    # 定义首次启动自动创建测试方法。
    def test_ensure_directory_documents_creates_every_managed_document(self):
        """
        验证空项目根目录会补齐全部受管目录说明文件。

        :return: None
        :rtype: None
        """

        # 创建隔离的临时项目目录。
        with tempfile.TemporaryDirectory() as temporary_directory:

            # 解析临时项目根目录。
            project_root = Path(temporary_directory)

            # 执行首次目录说明补齐。
            created_paths = ensure_directory_documents(project_root)

            # 断言首次创建数量与模板数量一致。
            self.assertEqual(len(created_paths), len(DIRECTORY_DOCUMENTS))

            # 遍历全部受管目录说明模板。
            for relative_directory, document_name, document_content in DIRECTORY_DOCUMENTS:

                # 解析预期目录说明文件路径。
                document_path = project_root / relative_directory / document_name

                # 断言目录说明文件已创建。
                self.assertTrue(document_path.is_file())

                # 断言目录说明文件内容使用对应模板。
                self.assertEqual(document_path.read_text(encoding="utf-8"), document_content)

    # 定义人工内容保护测试方法。
    def test_ensure_directory_documents_preserves_existing_content(self):
        """
        验证后续启动不覆盖维护者已修改的目录说明。

        :return: None
        :rtype: None
        """

        # 创建隔离的临时项目目录。
        with tempfile.TemporaryDirectory() as temporary_directory:

            # 解析临时项目根目录。
            project_root = Path(temporary_directory)

            # 执行首次目录说明补齐。
            ensure_directory_documents(project_root)

            # 读取第一个受管目录说明模板。
            relative_directory, document_name, _ = DIRECTORY_DOCUMENTS[0]

            # 解析将被人工修改的目录说明文件路径。
            document_path = project_root / relative_directory / document_name

            # 写入维护者自定义说明内容。
            document_path.write_text("维护者自定义说明\n", encoding="utf-8", newline="\n")

            # 再次执行目录说明补齐。
            created_paths = ensure_directory_documents(project_root)

            # 断言第二次检查不重复创建文件。
            self.assertEqual(created_paths, [])

            # 断言维护者自定义说明保持不变。
            self.assertEqual(document_path.read_text(encoding="utf-8"), "维护者自定义说明\n")
