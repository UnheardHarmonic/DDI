# -*- coding: utf-8 -*-
"""
DDI 受控网页任务入口。

本模块仅提供展示层 API 和网页静态资源，不保存账号密码、授权信息或商业平台会话。
业务任务始终复用 ddi_framework 中的无界面公共运行时，并由 Cloudflare Access 负责外部访问鉴权。
"""

# 导入操作系统环境模块。
import os

# 导入常量时间密钥比较工具。
import secrets

# 导入线程安全锁工具。
from threading import RLock

# 导入通用唯一标识生成工具。
from uuid import uuid4

# 导入日期时间解析工具。
from datetime import datetime

# 导入任务数据类工具。
from dataclasses import dataclass

# 导入线程池执行器。
from concurrent.futures import ThreadPoolExecutor

# 导入路径对象工具。
from pathlib import Path

# 导入 FastAPI 应用类型。
from fastapi import FastAPI

# 导入 HTTP 请求类型。
from fastapi import Request

# 导入 HTTP 状态异常类型。
from fastapi import HTTPException

# 导入静态文件挂载类型。
from fastapi.staticfiles import StaticFiles

# 导入 JSON 响应类型。
from fastapi.responses import JSONResponse

# 导入文件响应类型。
from fastapi.responses import FileResponse

# 导入 ZIP 压缩文件处理模块。
import zipfile

# 导入 Pydantic 数据模型工具。
from pydantic import BaseModel

# 导入 Pydantic 字段校验工具。
from pydantic import Field

# 导入商业有效配置读取函数。
from ddi_framework.account_config import get_effective_accounts

# 导入商业启停状态解析函数。
from ddi_framework.account_config import resolve_runtime_enabled

# 导入运行期配置读取函数。
from ddi_framework.account_config import load_runtime_account_config

# 导入数据类型汇总函数。
from ddi_framework.task_core import list_supported_data_types

# 导入无界面任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入无界面 DDI 任务运行时。
from ddi_framework.task_runtime import DdiTaskRuntime


# 定义项目根目录常量。
PROJECT_ROOT = Path(__file__).resolve().parent

# 定义网页静态资源目录常量。
STATIC_ROOT = PROJECT_ROOT / "web"

# 定义网页任务运行产物根目录常量。
WEB_RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "web"

# 定义 Cloudflare Access 身份头名称。
ACCESS_EMAIL_HEADER = "cf-access-authenticated-user-email"

# 定义临时访问口令请求头名称。
TEMPORARY_ACCESS_KEY_HEADER = "x-ddi-access-key"

# 定义临时访问者标识请求头名称。
TEMPORARY_VISITOR_ID_HEADER = "x-ddi-visitor-id"

# 定义临时访问口令环境变量名称。
TEMPORARY_ACCESS_KEY_ENVIRONMENT_NAME = "DDI_TEMPORARY_ACCESS_KEY"


# 定义网页任务提交参数模型。
class WebTaskSubmission(BaseModel):

    """
    描述网页提交的一次 DDI 任务。

    :param companies: 需要执行的商业名称列表。
    :type companies: list[str]
    :param data_type: 需要执行的数据类型。
    :type data_type: str
    :param start_date: 查询开始日期。
    :type start_date: str
    :param end_date: 查询结束日期。
    :type end_date: str
    :param max_workers: 最大并发商业数。
    :type max_workers: int
    :param copy_excel: 是否生成复制用 Excel。
    :type copy_excel: bool
    """

    # 保存至少包含一家商业的任务清单。
    companies: list[str] = Field(min_length=1, max_length=100)

    # 保存前端选择的数据类型。
    data_type: str = Field(min_length=1, max_length=32)

    # 保存 ISO 日期格式的查询开始日期。
    start_date: str = Field(min_length=10, max_length=10)

    # 保存 ISO 日期格式的查询结束日期。
    end_date: str = Field(min_length=10, max_length=10)

    # 保存允许执行的最大商业并发数量。
    max_workers: int = Field(default=1, ge=1, le=12)

    # 保存复制用 Excel 的生成开关。
    copy_excel: bool = True


# 定义网页任务状态对象。
@dataclass
class WebTaskRecord:

    """
    保存单个网页任务的无敏感状态信息。

    :param task_id: 网页任务唯一标识。
    :type task_id: str
    :param requester_email: Cloudflare Access 已验证访问者邮箱。
    :type requester_email: str
    :param submitted_at: 任务提交时间。
    :type submitted_at: datetime
    :param status: 当前任务状态。
    :type status: str
    :param message: 当前任务状态说明。
    :type message: str
    :param result: 脱敏任务汇总结果。
    :type result: dict
    :param artifact_names: 当前访问者可下载的任务文件名称列表。
    :type artifact_names: list[str]
    """

    # 保存浏览器可查询的任务唯一标识。
    task_id: str

    # 保存通过 Access 验证后的访问者邮箱。
    requester_email: str

    # 保存任务创建时间。
    submitted_at: datetime

    # 保存任务执行状态。
    status: str = "排队中"

    # 保存供网页显示的任务说明。
    message: str = "任务已进入执行队列"

    # 保存不包含绝对路径、Cookie 或账号信息的汇总结果。
    result: dict | None = None

    # 保存仅包含文件名称的可下载任务文件列表。
    artifact_names: list[str] | None = None


# 定义网页任务服务。
class WebTaskService:

    """
    串行调度网页 DDI 任务并保存脱敏状态。

    :param project_root: DDI 项目根目录。
    :type project_root: pathlib.Path
    """

    # 定义网页任务服务初始化方法。
    def __init__(self, project_root):

        """
        初始化网页任务状态容器与单任务执行队列。

        :param project_root: DDI 项目根目录。
        :type project_root: pathlib.Path
        :return: None。
        :rtype: None
        """

        # 保存标准化项目根目录。
        self.project_root = Path(project_root).resolve()

        # 初始化网页任务状态映射。
        self.records = {}

        # 初始化任务状态读写锁。
        self.lock = RLock()

        # 创建单工作线程以避免跨任务复用商业平台会话。
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ddi-web")

    # 定义可执行商业列表读取方法。
    def list_companies(self):

        """
        返回当前启用商业的脱敏展示信息。

        :return: 可供网页选择的商业信息列表。
        :rtype: list[dict]
        """

        # 读取本地运行期启停配置。
        runtime_config = load_runtime_account_config(str(self.project_root))

        # 构建应用运行期覆盖后的账号配置。
        accounts = get_effective_accounts(str(self.project_root), runtime_config)

        # 初始化网页可展示商业列表。
        companies = []

        # 遍历全部有效账号配置。
        for company_name, account in accounts.items():

            # 跳过运行期关闭的商业配置。
            if not resolve_runtime_enabled(company_name, account, runtime_config):

                # 继续读取下一家商业配置。
                continue

            # 追加不包含账号密码的商业展示信息。
            companies.append({"name": company_name, "platform": str(account.get("平台", ""))})

        # 返回按商业名称排序的展示列表。
        return sorted(companies, key=lambda item: item["name"])

    # 定义支持数据类型读取方法。
    def list_data_types(self):

        """
        返回当前有效账号声明的数据类型集合。

        :return: 网页可选择的数据类型列表。
        :rtype: list[str]
        """

        # 构建应用运行期覆盖后的账号配置。
        accounts = get_effective_accounts(str(self.project_root))

        # 返回公共任务层定义的数据类型列表。
        return list_supported_data_types(accounts)

    # 定义网页任务提交方法。
    def submit(self, submission, requester_email):

        """
        创建网页任务记录并提交到串行执行队列。

        :param submission: 已校验的网页任务参数。
        :type submission: WebTaskSubmission
        :param requester_email: Cloudflare Access 已验证访问者邮箱。
        :type requester_email: str
        :return: 新建任务记录。
        :rtype: WebTaskRecord
        """

        # 校验网页提交参数。
        self.validate_submission(submission)

        # 生成随机网页任务标识。
        task_id = uuid4().hex

        # 创建网页任务状态记录。
        record = WebTaskRecord(task_id=task_id, requester_email=requester_email, submitted_at=datetime.now())

        # 获取任务状态写入锁。
        with self.lock:

            # 保存新建任务状态记录。
            self.records[task_id] = record

        # 将实际协议任务提交到单任务执行队列。
        self.executor.submit(self.execute_task, task_id, submission)

        # 返回新建任务状态记录。
        return record

    # 定义网页任务状态读取方法。
    def get_record(self, task_id, requester_email):

        """
        读取指定访问者可见的网页任务状态。

        :param task_id: 网页任务唯一标识。
        :type task_id: str
        :param requester_email: Cloudflare Access 已验证访问者邮箱。
        :type requester_email: str
        :return: 网页任务状态记录。
        :rtype: WebTaskRecord
        """

        # 获取任务状态读取锁。
        with self.lock:

            # 读取指定标识对应的任务记录。
            record = self.records.get(task_id)

        # 判断任务记录是否存在。
        if record is None:

            # 抛出任务不存在异常。
            raise HTTPException(status_code=404, detail="任务不存在或已清理")

        # 判断访问者是否为原任务提交者。
        if record.requester_email != requester_email:

            # 拒绝读取其他访问者的任务状态。
            raise HTTPException(status_code=403, detail="无权查看该任务")

        # 返回归属校验通过的任务记录。
        return record

    # 定义网页提交参数校验方法。
    def validate_submission(self, submission):

        """
        校验日期范围、商业范围和数据类型范围。

        :param submission: 已解析的网页任务参数。
        :type submission: WebTaskSubmission
        :return: None。
        :rtype: None
        """

        # 将开始日期解析为日期对象。
        start_date = self.parse_date(submission.start_date, "开始日期")

        # 将结束日期解析为日期对象。
        end_date = self.parse_date(submission.end_date, "结束日期")

        # 校验开始日期不晚于结束日期。
        if start_date > end_date:

            # 抛出无效日期范围异常。
            raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")

        # 构建当前可执行商业名称集合。
        available_companies = {item["name"] for item in self.list_companies()}

        # 查找未授权或已关闭的商业名称。
        invalid_companies = sorted(set(submission.companies) - available_companies)

        # 判断是否包含无效商业名称。
        if invalid_companies:

            # 抛出商业不可执行异常。
            raise HTTPException(status_code=422, detail="包含不可执行商业：" + "、".join(invalid_companies))

        # 判断数据类型是否为当前支持选项。
        if submission.data_type not in self.list_data_types():

            # 抛出数据类型无效异常。
            raise HTTPException(status_code=422, detail="数据类型不在当前可选范围内")

    # 定义日期解析方法。
    def parse_date(self, date_text, field_name):

        """
        校验并解析 ISO 日期文本。

        :param date_text: ISO 日期文本。
        :type date_text: str
        :param field_name: 用于错误提示的字段名称。
        :type field_name: str
        :return: 已解析日期对象。
        :rtype: datetime.date
        """

        # 捕获日期文本解析失败异常。
        try:

            # 按标准日期格式解析文本。
            return datetime.strptime(date_text, "%Y-%m-%d").date()

        # 处理不符合标准格式的日期文本。
        except ValueError as error:

            # 抛出便于网页展示的参数异常。
            raise HTTPException(status_code=422, detail=f"{field_name}必须使用 YYYY-MM-DD 格式") from error

    # 定义后台任务执行方法。
    def execute_task(self, task_id, submission):

        """
        使用公共 DDI 运行时执行网页任务并保存脱敏结果。

        :param task_id: 网页任务唯一标识。
        :type task_id: str
        :param submission: 已校验的网页任务参数。
        :type submission: WebTaskSubmission
        :return: None。
        :rtype: None
        """

        # 更新当前任务为运行中状态。
        self.update_record(task_id, status="运行中", message="正在连接商业平台并生成文件")

        # 构建当前任务专属运行目录。
        task_root = WEB_RUNTIME_ROOT / task_id

        # 构建当前任务 Cookie 目录。
        cookie_dir = task_root / "cookies"

        # 构建当前任务业务文件目录。
        output_dir = task_root / "outputs"

        # 构建当前任务日志目录。
        log_dir = task_root / "logs"

        # 创建公共任务请求对象。
        request = TaskRequest(action="query_excel", data_type=submission.data_type, start_date=submission.start_date, end_date=submission.end_date, cookie_dir=str(cookie_dir), output_dir=str(output_dir), log_dir=str(log_dir), max_workers=submission.max_workers, copy_excel=submission.copy_excel, console_path_mode="relative", console_output_enabled=False)

        # 捕获公共运行时执行异常。
        try:

            # 创建指向本项目的无界面运行时。
            runtime = DdiTaskRuntime(str(self.project_root))

            # 执行用户选择的商业协议任务。
            execution = runtime.execute(request, submission.companies)

            # 构建不包含敏感路径的任务汇总。
            result = self.build_result_summary(execution.task_result)

            # 构建当前访问者可下载的任务文件清单。
            artifact_names = self.build_download_artifacts(task_root, output_dir, log_dir)

            # 更新当前任务为执行结束状态。
            self.update_record(task_id, status="已完成", message="任务已执行完成，可下载结果文件", result=result, artifact_names=artifact_names)

        # 处理公共运行时未捕获的异常。
        except Exception as error:

            # 记录不包含堆栈和敏感内容的异常说明。
            self.update_record(task_id, status="失败", message=f"任务执行失败：{str(error)[:300]}", result=None)

    # 定义任务状态更新方法。
    def update_record(self, task_id, status, message, result=None, artifact_names=None):

        """
        原子更新网页任务的展示状态。

        :param task_id: 网页任务唯一标识。
        :type task_id: str
        :param status: 新任务状态。
        :type status: str
        :param message: 新任务说明。
        :type message: str
    :param result: 可选的脱敏任务结果。
    :type result: dict | None
    :param artifact_names: 可选的可下载文件名称列表。
    :type artifact_names: list[str] | None
        :return: None。
        :rtype: None
        """

        # 获取任务状态写入锁。
        with self.lock:

            # 读取待更新的任务记录。
            record = self.records.get(task_id)

            # 判断任务记录是否仍然存在。
            if record is None:

                # 结束已清理任务的状态更新。
                return

            # 保存当前任务状态。
            record.status = status

            # 保存当前任务说明。
            record.message = message

            # 保存当前任务脱敏结果。
            record.result = result

            # 保存当前任务可下载文件名称列表。
            record.artifact_names = artifact_names

    # 定义任务结果脱敏方法。
    def build_result_summary(self, task_result):

        """
        将公共任务结果转换为可供网页查看的摘要。

        :param task_result: 公共任务协调结果。
        :type task_result: ddi_framework.task_core.TaskResult
        :return: 不包含文件绝对路径、Cookie 或账号字段的结果摘要。
        :rtype: dict
        """

        # 返回只包含执行计数和失败说明的结果对象。
        return {"计划商业数": task_result.total_count, "成功商业数": task_result.success_count, "失败商业数": task_result.failure_count, "未启动商业数": task_result.stopped_count, "失败原因": {str(name): str(message)[:300] for name, message in task_result.errors.items()}}

    # 定义下载归档构建方法。
    def build_download_artifacts(self, task_root, output_dir, log_dir):

        """
        将任务业务文件和日志压缩为访问者专属下载文件。

        :param task_root: 当前任务运行目录。
        :type task_root: pathlib.Path
        :param output_dir: 当前任务业务文件目录。
        :type output_dir: pathlib.Path
        :param log_dir: 当前任务日志文件目录。
        :type log_dir: pathlib.Path
        :return: 当前任务可下载的归档文件名称列表。
        :rtype: list[str]
        """

        # 创建当前任务下载目录。
        download_dir = task_root / "downloads"

        # 确保当前任务下载目录存在。
        download_dir.mkdir(parents=True, exist_ok=True)

        # 定义当前任务下载归档文件路径。
        archive_path = download_dir / "DDI任务结果.zip"

        # 打开 ZIP 文件并使用压缩模式写入。
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:

            # 遍历业务文件目录内的全部文件。
            for source_path in output_dir.rglob("*"):

                # 跳过业务目录中的非文件路径。
                if not source_path.is_file():

                    # 继续检查下一个业务目录路径。
                    continue

                # 将业务文件写入归档的 outputs 子目录。
                archive.write(source_path, source_path.relative_to(task_root))

            # 遍历日志目录内的全部文件。
            for source_path in log_dir.rglob("*"):

                # 跳过日志目录中的非文件路径。
                if not source_path.is_file():

                    # 继续检查下一个日志目录路径。
                    continue

                # 将日志文件写入归档的 logs 子目录。
                archive.write(source_path, source_path.relative_to(task_root))

        # 返回归档文件名称列表。
        return [archive_path.name]

    # 定义任务下载文件解析方法。
    def resolve_download_path(self, task_id, artifact_name, requester_email):

        """
        校验任务归属并解析可下载归档文件路径。

        :param task_id: 网页任务唯一标识。
        :type task_id: str
        :param artifact_name: 网页请求的文件名称。
        :type artifact_name: str
        :param requester_email: Cloudflare Access 已验证访问者邮箱。
        :type requester_email: str
        :return: 已校验的下载文件路径。
        :rtype: pathlib.Path
        """

        # 读取归属当前访问者的任务状态记录。
        record = self.get_record(task_id, requester_email)

        # 校验当前任务是否已完成。
        if record.status != "已完成":

            # 拒绝下载尚未完成的任务文件。
            raise HTTPException(status_code=409, detail="任务尚未完成，暂不能下载文件")

        # 校验请求的文件名称是否为当前任务已登记文件。
        if artifact_name not in (record.artifact_names or []):

            # 拒绝读取未登记的任务文件。
            raise HTTPException(status_code=404, detail="下载文件不存在")

        # 解析当前任务下载文件路径。
        artifact_path = WEB_RUNTIME_ROOT / task_id / "downloads" / artifact_name

        # 校验下载文件是否仍在运行目录中存在。
        if not artifact_path.is_file():

            # 提示访问者任务文件已清理。
            raise HTTPException(status_code=404, detail="下载文件已清理，请重新提交任务")

        # 返回已经完成归属校验的下载文件路径。
        return artifact_path


# 创建网页任务服务单例。
task_service = WebTaskService(PROJECT_ROOT)

# 创建 FastAPI 网页服务实例。
app = FastAPI(title="DDI 网页入口", docs_url=None, redoc_url=None)

# 挂载网页静态资源目录。
app.mount("/assets", StaticFiles(directory=str(STATIC_ROOT)), name="assets")


# 定义网页访问身份读取函数。
def require_access_identity(request):

    """
    从 Cloudflare Access 或临时访问口令读取并校验访问者身份。

    :param request: 当前 HTTP 请求。
    :type request: fastapi.Request
    :return: 已授权访问者唯一身份。
    :rtype: str
    """

    # 读取 Cloudflare Tunnel 传递的已验证邮箱。
    email = str(request.headers.get(ACCESS_EMAIL_HEADER, "")).strip().lower()

    # 读取部署电脑配置的允许邮箱集合。
    allowed_emails = {value.strip().lower() for value in os.environ.get("DDI_ALLOWED_EMAILS", "").split(",") if value.strip()}

    # 读取部署电脑配置的临时访问口令。
    expected_access_key = str(os.environ.get(TEMPORARY_ACCESS_KEY_ENVIRONMENT_NAME, "")).strip()

    # 读取浏览器提交的临时访问口令。
    provided_access_key = str(request.headers.get(TEMPORARY_ACCESS_KEY_HEADER, "")).strip()

    # 读取浏览器生成的临时访问者标识。
    visitor_id = str(request.headers.get(TEMPORARY_VISITOR_ID_HEADER, "")).strip()

    # 在已配置临时访问口令时校验浏览器提交的口令。
    if expected_access_key:

        # 使用常量时间比较拒绝错误访问口令。
        if not secrets.compare_digest(provided_access_key, expected_access_key):

            # 抛出临时访问口令错误异常。
            raise HTTPException(status_code=401, detail="临时访问口令无效")

        # 拒绝缺少独立浏览器标识的临时访问请求。
        if len(visitor_id) < 16 or len(visitor_id) > 128:

            # 抛出临时访问者标识无效异常。
            raise HTTPException(status_code=400, detail="临时访问者标识无效")

        # 返回隔离浏览器任务归属的临时访问者身份。
        return f"temporary:{visitor_id}"

    # 拒绝未配置 Access 允许邮箱集合的服务。
    if not allowed_emails:

        # 抛出服务端 Access 策略缺失异常。
        raise HTTPException(status_code=503, detail="服务未配置 DDI_ALLOWED_EMAILS 或 DDI_TEMPORARY_ACCESS_KEY")

    # 拒绝缺少 Cloudflare Access 已验证邮箱的请求。
    if not email:

        # 抛出需要 Cloudflare Access 登录异常。
        raise HTTPException(status_code=401, detail="需要通过 Cloudflare Access 登录")

    # 拒绝不在允许列表中的 Access 邮箱。
    if email not in allowed_emails:

        # 抛出访问者未授权异常。
        raise HTTPException(status_code=403, detail="当前邮箱没有 DDI 网页入口权限")

    # 返回已验证且已授权的 Access 邮箱。
    return email

# 定义网页认证模式读取函数。
def get_authentication_mode():

    """
    返回当前服务可用的网页认证模式。

    :return: 网页认证模式标识。
    :rtype: str
    """

    # 读取部署电脑配置的临时访问口令。
    temporary_access_key = str(os.environ.get(TEMPORARY_ACCESS_KEY_ENVIRONMENT_NAME, "")).strip()

    # 在临时访问口令存在时返回临时认证模式。
    if temporary_access_key:

        # 返回临时访问口令认证模式标识。
        return "temporary_access_key"

    # 返回 Cloudflare Access 认证模式标识。
    return "cloudflare_access"


# 定义网页认证模式读取接口。
@app.get("/api/authentication-mode")
def get_authentication_mode_endpoint():

    """
    返回前端选择认证请求头所需的认证模式。

    :return: 认证模式响应。
    :rtype: fastapi.responses.JSONResponse
    """

    # 返回当前服务认证模式标识。
    return JSONResponse({"mode": get_authentication_mode()})


# 定义首页响应函数。
@app.get("/", include_in_schema=False)
def get_index():

    """
    返回 DDI 网页入口静态首页。

    :return: 首页文件响应。
    :rtype: fastapi.responses.FileResponse
    """

    # 返回网页首页静态文件。
    return FileResponse(STATIC_ROOT / "index.html")


# 定义网页选项读取接口。
@app.get("/api/options")
def get_options(request: Request):

    """
    返回当前访问者可选择的商业和数据类型。

    :param request: 当前 HTTP 请求。
    :type request: fastapi.Request
    :return: 脱敏选择项响应。
    :rtype: fastapi.responses.JSONResponse
    """

    # 校验当前请求的网页访问身份。
    require_access_identity(request)

    # 返回不含账号密码的网页选择项。
    return JSONResponse({"companies": task_service.list_companies(), "data_types": task_service.list_data_types()})


# 定义网页任务提交接口。
@app.post("/api/tasks")
def create_task(submission: WebTaskSubmission, request: Request):

    """
    创建并异步执行一项 DDI 网页任务。

    :param submission: 网页任务提交参数。
    :type submission: WebTaskSubmission
    :param request: 当前 HTTP 请求。
    :type request: fastapi.Request
    :return: 新建任务的状态响应。
    :rtype: fastapi.responses.JSONResponse
    """

    # 读取已验证访问者身份。
    requester_email = require_access_identity(request)

    # 创建当前访问者的网页任务。
    record = task_service.submit(submission, requester_email)

    # 返回浏览器轮询所需的任务标识。
    return JSONResponse({"task_id": record.task_id, "status": record.status, "message": record.message}, status_code=202)


# 定义网页任务状态读取接口。
@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, request: Request):

    """
    返回当前访问者提交任务的脱敏执行状态。

    :param task_id: 网页任务唯一标识。
    :type task_id: str
    :param request: 当前 HTTP 请求。
    :type request: fastapi.Request
    :return: 任务状态响应。
    :rtype: fastapi.responses.JSONResponse
    """

    # 读取已验证访问者身份。
    requester_email = require_access_identity(request)

    # 读取归属当前访问者的任务状态。
    record = task_service.get_record(task_id, requester_email)

    # 返回不包含账号密码和文件绝对路径的状态内容。
    return JSONResponse({"task_id": record.task_id, "status": record.status, "message": record.message, "submitted_at": record.submitted_at.isoformat(timespec="seconds"), "result": record.result, "artifacts": record.artifact_names or []})


# 定义网页任务文件下载接口。
@app.get("/api/tasks/{task_id}/downloads/{artifact_name}")
def download_task_artifact(task_id: str, artifact_name: str, request: Request):

    """
    下载当前访问者已完成任务的结果归档文件。

    :param task_id: 网页任务唯一标识。
    :type task_id: str
    :param artifact_name: 任务归档文件名称。
    :type artifact_name: str
    :param request: 当前 HTTP 请求。
    :type request: fastapi.Request
    :return: 受控文件下载响应。
    :rtype: fastapi.responses.FileResponse
    """

    # 读取已验证访问者身份。
    requester_email = require_access_identity(request)

    # 解析经过归属验证的下载文件路径。
    artifact_path = task_service.resolve_download_path(task_id, artifact_name, requester_email)

    # 返回浏览器下载的任务结果归档文件。
    return FileResponse(artifact_path, filename=artifact_path.name, media_type="application/zip")


# 定义命令行服务启动函数。
def main():

    """
    以仅本机监听模式启动 DDI 网页服务。

    :return: None。
    :rtype: None
    """

    # 导入 ASGI 服务启动模块。
    import uvicorn

    # 启动仅允许 Cloudflare Tunnel 转发的本机服务。
    uvicorn.run("ddi_web:app", host="127.0.0.1", port=8787, reload=False)


# 判断当前模块是否以脚本方式运行。
if __name__ == "__main__":

    # 启动 DDI 网页服务。
    main()
