# -*- coding: utf-8 -*-
"""
DDI 受管目录说明自愈服务。

本模块维护项目固定目录的用途说明模板，并在应用启动时补齐被删除的目录或说明文件。

:return: 模块提供目录说明检查与生成函数。
:rtype: None
"""

# 导入路径对象类型。
from pathlib import Path


# 定义受管目录说明模板集合。
DIRECTORY_DOCUMENTS = (
    ("", "===== 项目根目录总览 =====.md", "# DDI 项目根目录总览\n\n本目录只保留源码入口、配置、公共框架、界面资源、测试、文档和打包配置。运行产物统一写入 `runtime`，不得散落在项目根目录。\n"),
    ("config", "===== 账号运行配置 =====.md", "# 账号运行配置\n\n本目录保存商业运行开关、GUI 快捷方案、授权相关配置和复制用 Excel 映射。账号密码只保存在 Git 忽略的本机私有配置文件中。\n"),
    ("config/copy_mappings", "===== 复制用Excel字段映射 =====.md", "# 复制用 Excel 字段映射\n\n本目录保存复制用 Excel 的商业级字段映射。映射只影响派生文件，不得改写正式原始 Excel 的真实字段标题和顺序。\n"),
    ("ddi_framework", "===== 公共任务与协议框架 =====.md", "# 公共任务与协议框架\n\n本目录是 DDI 的唯一业务事实来源，负责任务模型、登录、协议查询、动态字段、Excel、日志、授权和调度。CLI 与 Qt GUI 仅调用这里的公共接口。\n"),
    ("ddi_framework/platforms", "===== 商业平台协议适配器 =====.md", "# 商业平台协议适配器\n\n本目录按平台维护协议登录、查询、分页、响应解析和平台特殊日期语义。正式适配器必须走协议请求，并保留当前商业真实返回的原始字段。\n"),
    ("docs", "===== 正式文档与运行说明 =====.md", "# 正式文档与运行说明\n\n本目录只保存同事使用、发布交付和运行产物的正式说明。个人学习资料、抓包截图和验证材料应放入 `runtime/archive/personal_reference`。\n"),
    ("packaging", "===== PyInstaller发布配置 =====.md", "# PyInstaller 发布配置\n\n本目录保存 CLI、Qt GUI 的 PyInstaller spec、构建脚本和发布说明。构建生成物位于 `dist` 或运行期归档目录，不应提交到源码目录。\n"),
    ("runtime", "===== 本机运行产物 =====.md", "# 本机运行产物\n\n本目录是默认运行产物根目录。正式 Excel、日志、Cookie、自定义输出、工作区和历史归档必须按子目录分类保存。\n"),
    ("runtime/archive", "===== 历史与维护归档 =====.md", "# 历史与维护归档\n\n本目录保存历史运行产物、可再生生成物和维护者个人参考资料。公共任务运行时不会把这里的内容作为当前任务输入。\n"),
    ("runtime/archive/generated", "===== 历史生成物归档 =====.md", "# 历史生成物归档\n\n本目录用于临时保存可再生的构建、验证和浏览器生成物。完成验证后可按需要清理，不属于正式交付内容。\n"),
    ("runtime/archive/legacy", "===== 历史运行产物 =====.md", "# 历史运行产物\n\n本目录保存旧版本或旧任务的 Excel、日志、Cookie、验证结果和交接快照，仅用于追溯。\n"),
    ("runtime/archive/personal_reference", "===== 个人协议研究资料 =====.md", "# 个人协议研究资料\n\n本目录仅供维护者保存个人学习笔记、协议研究材料和截图，不得进入正式文档或发布包。\n"),
    ("runtime/cookies", "===== 登录会话缓存 =====.md", "# 登录会话缓存\n\n本目录保存运行期 Cookie、会话摘要和登录缓存。内容可能包含敏感会话信息，不得提交、共享或打包发布。\n"),
    ("runtime/custom", "===== 项目内自定义运行产物 =====.md", "# 项目内自定义运行产物\n\n项目内通过命令行传入的自定义输出路径会按结果、日志和 Cookie 自动归类到本目录，避免污染项目根目录。\n"),
    ("runtime/downloads", "===== 默认Excel导出结果 =====.md", "# 默认 Excel 导出结果\n\n本目录保存默认查询产生的正式原始 Excel、复制用 Excel 和录入明细。文件名只标识商业、时间范围和数据类型，不写入字段数或记录数。\n"),
    ("runtime/logs", "===== 任务运行日志 =====.md", "# 任务运行日志\n\n本目录保存公共任务运行日志 Excel。记录数、字段变化、失败原因和文件路径在日志中追踪，不应写入业务文件名。\n"),
    ("runtime/work", "===== 本机任务工作区 =====.md", "# 本机任务工作区\n\n本目录集中保存临时任务缓存和平台回归验证等可再生产物，不保存正式业务交付文件。\n"),
    ("runtime/work/temp", "===== 临时任务缓存 =====.md", "# 临时任务缓存\n\n本目录保存任务执行期间可安全清理的临时缓存。\n"),
    ("runtime/work/validation", "===== 平台回归验证产物 =====.md", "# 平台回归验证产物\n\n本目录保存平台协议、字段或日期范围回归验证产生的中间材料。\n"),
    ("tests", "===== 自动化回归测试 =====.md", "# 自动化回归测试\n\n本目录保存领域模型、公共任务运行时、平台适配器和展示隔离的自动化回归测试。\n"),
    ("ui", "===== Qt展示资源 =====.md", "# Qt 展示资源\n\n本目录保存 Qt Quick 桌面展示资源。展示层只负责参数采集和任务状态呈现，不实现协议业务。\n"),

)


# 定义默认项目根目录解析函数。
def resolve_project_root(project_root=None):
    """
    解析目录说明服务使用的项目根目录。

    :param project_root: 调用方指定的项目根目录。
    :type project_root: str | pathlib.Path | None
    :return: 绝对项目根目录。
    :rtype: pathlib.Path
    """

    # 判断调用方是否提供项目根目录。
    if project_root is not None:

        # 返回调用方提供的绝对项目根目录。
        return Path(project_root).resolve()

    # 返回当前公共框架包的上级项目目录。
    return Path(__file__).resolve().parent.parent


# 定义受管目录说明补齐函数。
def ensure_directory_documents(project_root=None):
    """
    创建缺失的受管目录及其用途说明文件，不覆盖已有文件内容。

    :param project_root: 调用方指定的项目根目录。
    :type project_root: str | pathlib.Path | None
    :return: 本次新建的说明文件绝对路径列表。
    :rtype: list[pathlib.Path]
    """

    # 解析本次检查使用的项目根目录。
    root_path = resolve_project_root(project_root)

    # 初始化本次新建说明文件路径列表。
    created_paths = []

    # 遍历全部受管目录说明模板。
    for relative_directory, document_name, document_content in DIRECTORY_DOCUMENTS:

        # 解析当前受管目录的绝对路径。
        directory_path = root_path / relative_directory

        # 创建缺失的受管目录。
        directory_path.mkdir(parents=True, exist_ok=True)

        # 解析当前目录说明文件路径。
        document_path = directory_path / document_name

        # 判断目录说明文件已经存在。
        if document_path.exists():

            # 保留维护者已编辑的说明内容。
            continue

        # 以独占模式创建目录说明文件，避免并发启动覆盖内容。
        try:

            # 打开新的 UTF-8 目录说明文件。
            with document_path.open("x", encoding="utf-8", newline="\n") as file_obj:

                # 写入当前目录用途说明模板。
                file_obj.write(document_content)

        # 处理其他入口并发创建同一说明文件的情况。
        except FileExistsError:

            # 继续检查后续受管目录。
            continue

        # 记录本次成功新建的说明文件。
        created_paths.append(document_path)

    # 返回本次自动补齐的说明文件路径。
    return created_paths
