# -*- coding: utf-8 -*-
"""
DDI 本机 Web GUI 展示层。

本模块只负责本机浏览器界面、任务状态和结构化事件转发，业务执行统一调用公共任务运行时。
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ddi_framework.account_config import get_effective_accounts, load_runtime_account_config, resolve_runtime_enabled
from ddi_framework.directory_docs import ensure_directory_documents
from ddi_framework.task_core import DateRangeSpec, TaskCancellation, TaskEvent, TaskEventSink, TaskRequest, list_data_type_categories, normalize_data_type_category
from ddi_framework.task_runtime import DdiTaskRuntime


# 解析项目源代码根目录。
PROJECT_ROOT = Path(__file__).resolve().parent

# 解析统一展示资源目录。
STATIC_ROOT = PROJECT_ROOT / "ui"

# 解析本机 Web 任务工作目录。
WEB_RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "work" / "web"

class WebTaskSubmission(BaseModel):
    """
    描述本机 Web GUI 提交的任务参数。

    :param companies: 商业名称列表。
    :type companies: list[str]
    :param data_types: 多选数据类型。
    :type data_types: list[str]
    :param date_mode: 日期模式。
    :type date_mode: str
    :param start_date: 自定义开始日期。
    :type start_date: str
    :param end_date: 自定义结束日期。
    :type end_date: str
    :param max_workers: 最大并发商业数。
    :type max_workers: int
    :param copy_excel: 是否生成复制用 Excel。
    :type copy_excel: bool
    """

    companies: list[str] = Field(min_length=1, max_length=100)
    data_types: list[str] = Field(min_length=1, max_length=20)
    date_mode: str = "previous_month_full"
    start_date: str = ""
    end_date: str = ""
    max_workers: int = Field(default=1, ge=1, le=12)
    copy_excel: bool = True


class WebEventSink(TaskEventSink):
    """
    保存本机浏览器任务需要消费的结构化事件。

    :param service: 本机网页任务服务。
    :type service: WebTaskService
    :param task_id: 任务标识。
    :type task_id: str
    """

    def __init__(self, service, task_id):
        self.service = service
        self.task_id = task_id

    def publish(self, event):
        """
        将公共事件转换为浏览器事件。

        :param event: 公共任务事件。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        self.service.append_event(self.task_id, event)


class WebTaskService:
    """
    管理本机浏览器任务、事件和产物路径。

    :param project_root: DDI 项目根目录。
    :type project_root: pathlib.Path
    """

    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.lock = RLock()
        self.records = {}
        self.events = {}
        self.cancellations = {}

        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ddi-local-web")

    def list_companies(self):
        """
        返回运行期启用商业信息。

        :return: 商业信息列表。
        :rtype: list[dict]
        """

        runtime_config = load_runtime_account_config(str(self.project_root))
        accounts = get_effective_accounts(str(self.project_root), runtime_config)
        return [{"name": name, "platform": str(account.get("平台", "")), "data_types": list(dict.fromkeys(normalize_data_type_category(value) for value in account.get("数据类型列表", []) or [] if str(value).strip()))} for name, account in accounts.items() if resolve_runtime_enabled(name, account, runtime_config)]

    def validate_submission(self, submission):
        """
        校验商业、数据类型和日期范围。

        :param submission: 网页任务参数。
        :type submission: WebTaskSubmission
        :return: None。
        :rtype: None
        """

        available_companies = {item["name"] for item in self.list_companies()}
        invalid_companies = sorted(set(submission.companies) - available_companies)
        if invalid_companies:
            raise HTTPException(status_code=422, detail="包含不可执行商业：" + "、".join(invalid_companies))
        available_types = set(list_data_type_categories(get_effective_accounts(str(self.project_root))))
        invalid_types = sorted(set(submission.data_types) - available_types)
        if invalid_types:
            raise HTTPException(status_code=422, detail="包含未登记数据类型：" + "、".join(invalid_types))
        try:
            date_range = DateRangeSpec.from_mode(submission.date_mode, submission.start_date, submission.end_date)
            start_value = datetime.strptime(date_range.start_date, "%Y-%m-%d")
            end_value = datetime.strptime(date_range.end_date, "%Y-%m-%d")
        except ValueError as error:
            raise HTTPException(status_code=422, detail=f"日期参数无效：{error}") from error
        if start_value > end_value:
            raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")

    def submit(self, submission):
        """
        校验并提交本机网页任务。

        :param submission: 网页任务参数。
        :type submission: WebTaskSubmission
        :return: 任务状态字典。
        :rtype: dict
        """

        self.validate_submission(submission)
        task_id = uuid4().hex
        task_root = WEB_RUNTIME_ROOT / task_id
        record = {"task_id": task_id, "status": "排队中", "message": "任务已进入本机执行队列", "result": None, "artifacts": [], "submitted_at": datetime.now().isoformat(timespec="seconds")}

        # 创建可覆盖排队和运行阶段的公共取消控制器。
        cancellation = TaskCancellation()

        # 在锁内登记本机任务状态和取消控制器。
        with self.lock:

            # 保存浏览器可读取的初始任务记录。
            self.records[task_id] = record

            # 初始化当前任务的事件集合。
            self.events[task_id] = []

            # 保存任务全生命周期使用的取消控制器。
            self.cancellations[task_id] = cancellation
        # 提交当前本机网页任务到受控执行器。
        self.executor.submit(self.execute_task, task_id, submission, task_root)

        return dict(record)

    def execute_task(self, task_id, submission, task_root):
        """
        使用公共运行时执行本机网页任务。

        :param task_id: 任务标识。
        :type task_id: str
        :param submission: 任务参数。
        :type submission: WebTaskSubmission
        :param task_root: 任务目录。
        :type task_root: pathlib.Path
        :return: None。
        :rtype: None
        """

        # 读取任务是否已经在排队阶段取消。
        with self.lock:

            # 获取当前任务的最新状态记录。
            record = self.records.get(task_id, {})

        # 跳过已在排队阶段取消的任务。
        if record.get("status") == "已停止":

            # 结束已取消任务的后台执行入口。
            return

        # 构造当前任务独立的 Cookie 目录。
        cookie_dir = task_root / "cookies"
        output_dir = task_root / "outputs"
        log_dir = task_root / "logs"
        for path in (cookie_dir, output_dir, log_dir):
            path.mkdir(parents=True, exist_ok=True)
        date_range = DateRangeSpec.from_mode(submission.date_mode, submission.start_date, submission.end_date)
        request = TaskRequest(action="query_excel", data_type=",".join(submission.data_types), data_types=tuple(submission.data_types), start_date=date_range.start_date, end_date=date_range.end_date, date_range=date_range, cookie_dir=str(cookie_dir), output_dir=str(output_dir), log_dir=str(log_dir), max_workers=submission.max_workers, copy_excel=submission.copy_excel, console_output_enabled=False)
        # 读取提交阶段已创建的任务取消控制器。
        cancellation = self.cancellations[task_id]

        # 判断任务是否已在排队阶段收到安全停止请求。
        stop_requested = cancellation.is_stop_requested()

        # 在锁内同步浏览器可见的任务运行状态。
        with self.lock:

            # 保留排队阶段已收到的停止请求状态。
            if stop_requested:

                # 告知浏览器公共协调器即将确认停止结果。
                self.records[task_id]["status"] = "停止请求中"

                # 保留安全停止状态说明。
                self.records[task_id]["message"] = "已请求安全停止，正在确认未启动商业"

            # 标记未收到停止请求的任务进入运行状态。
            else:

                # 更新浏览器可见的运行状态。
                self.records[task_id]["status"] = "运行中"

                # 更新浏览器可见的运行说明。
                self.records[task_id]["message"] = "正在执行公共 DDI 任务"
        try:
            execution = DdiTaskRuntime(str(self.project_root), WebEventSink(self, task_id)).execute(request, submission.companies, cancellation)
            artifacts = [str(path.relative_to(task_root)) for path in task_root.rglob("*") if path.is_file() and path.parent.name in {"outputs", "logs"}]
            result = {"总数": execution.task_result.total_count, "成功": execution.task_result.success_count, "失败": execution.task_result.failure_count, "停止": execution.task_result.stopped_count, "错误": execution.task_result.errors}
            # 解析包含安全停止信息的最终任务状态。
            status, message = self.resolve_completion_status(execution.task_result)

            # 保存最终状态和可下载产物。
            self.update_record(task_id, status, message, result, artifacts)
        except Exception as error:
            self.update_record(task_id, "失败", f"任务执行失败：{str(error)[:300]}", None, [])

    # 定义任务完成状态解析方法。
    def resolve_completion_status(self, task_result):

        """
        根据公共任务汇总生成本机 Web 的终态文本。

        :param task_result: 公共任务协调器返回的汇总结果。
        :type task_result: TaskResult
        :return: 本机 Web 终态和终态说明。
        :rtype: tuple[str, str]
        """

        # 读取尚未启动即被安全停止的商业数量。
        stopped_count = int(getattr(task_result, "stopped_count", 0) or 0)

        # 判断本次任务是否包含安全停止的商业。
        if stopped_count:

            # 返回可供浏览器识别的已停止终态。
            return "已停止", f"任务已安全停止，未启动商业 {stopped_count} 家"

        # 返回正常完成终态。
        return "已完成", "任务执行完成"

    def append_event(self, task_id, event):
        """
        保存结构化任务事件。

        :param task_id: 任务标识。
        :type task_id: str
        :param event: 公共任务事件。
        :type event: TaskEvent
        :return: None。
        :rtype: None
        """

        payload = {"event_type": event.event_type, "message": event.message, "status": event.status, "company_name": event.company_name, "data_type": event.data_type, "payload": event.payload, "created_at": event.created_at.isoformat(timespec="seconds")}
        with self.lock:
            self.events.setdefault(task_id, []).append(payload)

    # 定义事件增量读取方法。
    def get_events_since(self, task_id, event_index):

        """
        读取指定事件序号后的本机任务事件。

        :param task_id: 任务标识。
        :type task_id: str
        :param event_index: 已消费事件数量。
        :type event_index: int
        :return: 新事件集合和新的消费序号。
        :rtype: tuple[list[dict], int]
        """

        # 在锁内复制新增事件，避免流式响应读取到半写入数据。
        with self.lock:
            events = list(self.events.get(task_id, []))

        # 返回指定位置之后的新增事件。
        return events[event_index:], len(events)

    def update_record(self, task_id, status, message, result, artifacts):
        """
        更新任务状态和产物列表。

        :param task_id: 任务标识。
        :type task_id: str
        :param status: 状态文本。
        :type status: str
        :param message: 状态说明。
        :type message: str
        :param result: 脱敏结果。
        :type result: dict | None
        :param artifacts: 产物相对路径列表。
        :type artifacts: list[str]
        :return: None。
        :rtype: None
        """

        with self.lock:
            if task_id in self.records:
                self.records[task_id].update({"status": status, "message": message, "result": result, "artifacts": artifacts})

    def get_record(self, task_id):
        """
        读取本机任务状态。

        :param task_id: 任务标识。
        :type task_id: str
        :return: 任务状态。
        :rtype: dict
        """

        with self.lock:
            record = self.records.get(task_id)
        if record is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return dict(record)

    def stop(self, task_id):
        """
        请求停止尚未开始的商业任务。

        :param task_id: 任务标识。
        :type task_id: str
        :return: 当前任务状态。
        :rtype: dict
        """

        # 读取当前任务状态和取消控制器。
        with self.lock:

            # 获取当前任务记录。
            record = self.records.get(task_id)

            # 获取运行中任务的公共取消控制器。
            cancellation = self.cancellations.get(task_id)

        # 处理不存在的任务记录。
        if record is None:

            # 返回统一的任务不存在错误。
            raise HTTPException(status_code=404, detail="任务不存在")

        # 定义不可再次停止的终态集合。
        terminal_statuses = {"已完成", "已失败", "已停止"}

        # 保留已经结束任务的最终状态。
        if record.get("status") in terminal_statuses:

            # 返回当前终态任务记录。
            return dict(record)

        # 处理已经进入公共任务运行时的任务。
        if cancellation is not None:

            # 请求公共协调器停止后续未开始商业。
            cancellation.request_stop()

            # 更新浏览器可见的停止请求状态。
            self.update_record(task_id, "停止请求中", "已请求安全停止，运行中的商业将完成当前协议步骤", None, [])

        return self.get_record(task_id)


task_service = WebTaskService(PROJECT_ROOT)
app = FastAPI(title="DDI 本机 Web GUI", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=str(STATIC_ROOT)), name="assets")


# 在 Web 服务生命周期启动时补齐受管目录说明。
@app.on_event("startup")
def initialize_web_runtime():

    """
    初始化本机 Web 运行期目录说明。

    :return: None。
    :rtype: None
    """

    # 创建缺失的目录和用途说明文件。
    ensure_directory_documents(PROJECT_ROOT)


@app.get("/", include_in_schema=False)
def get_index():
    """
    返回本机 Web GUI 首页。

    :return: 首页文件响应。
    :rtype: FileResponse
    """

    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def get_favicon():
    """
    返回空图标响应，避免本机浏览器产生无意义的 404 请求。

    :return: 空图标响应。
    :rtype: Response
    """

    # 返回无内容图标响应。
    return Response(status_code=204)


@app.get("/api/bootstrap")
def get_bootstrap():
    """
    返回本机 Web GUI 初始化数据。

    :return: 初始化数据响应。
    :rtype: JSONResponse
    """

    return JSONResponse({"companies": task_service.list_companies(), "data_types": list_data_type_categories(get_effective_accounts(str(PROJECT_ROOT))), "date_modes": ["previous_month_full", "previous_month_to_today", "custom"]})


@app.get("/api/options")
def get_options():
    """
    返回与初始化接口一致的公共筛选选项。

    :return: 公共选项响应。
    :rtype: JSONResponse
    """

    # 复用初始化数据，确保各入口只使用一份配置事实来源。
    return get_bootstrap()


@app.post("/api/tasks")
def create_task(submission: WebTaskSubmission):
    """
    提交本机 Web GUI 任务。

    :param submission: 任务参数。
    :type submission: WebTaskSubmission
    :return: 任务状态响应。
    :rtype: JSONResponse
    """

    return JSONResponse(task_service.submit(submission), status_code=202)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    """
    返回本机任务状态。

    :param task_id: 任务标识。
    :type task_id: str
    :return: 任务状态响应。
    :rtype: JSONResponse
    """

    return JSONResponse(task_service.get_record(task_id))


@app.get("/api/tasks/{task_id}/events")
def get_task_events(task_id: str):
    """
    以 SSE 形式推送本机任务事件。

    :param task_id: 任务标识。
    :type task_id: str
    :return: SSE 流响应。
    :rtype: StreamingResponse
    """

    task_service.get_record(task_id)

    def stream_events():
        """
        持续推送任务新增事件直到任务进入终态。

        :return: SSE 数据块迭代器。
        :rtype: collections.abc.Iterator[str]
        """

        # 初始化浏览器尚未消费的事件位置。
        event_index = 0

        # 持续读取公共任务层新产生的事件。
        while True:

            # 读取本轮新增事件。
            events, event_index = task_service.get_events_since(task_id, event_index)

            # 推送当前批次全部新增事件。
            for event in events:

                # 输出符合 SSE 协议的数据帧。
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 读取任务当前状态。
            record = task_service.get_record(task_id)

            # 判断任务是否已结束。
            if record.get("status") in {"已完成", "失败", "已停止"}:

                # 推送最终状态，供浏览器关闭连接前刷新汇总。
                yield f"event: completed\ndata: {json.dumps(record, ensure_ascii=False)}\n\n"

                # 结束事件流。
                return

            # 输出保活帧，避免本机代理提前关闭空闲连接。
            yield ": keep-alive\n\n"

            # 等待公共执行层继续产生事件。
            time.sleep(0.5)

    return StreamingResponse(stream_events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/tasks/{task_id}/stop")
def stop_task(task_id: str):
    """
    请求停止本机任务。

    :param task_id: 任务标识。
    :type task_id: str
    :return: 当前任务状态。
    :rtype: JSONResponse
    """

    return JSONResponse(task_service.stop(task_id))


@app.get("/api/tasks/{task_id}/artifacts")
def list_task_artifacts(task_id: str):
    """
    返回本机任务可下载的全部产物路径。

    :param task_id: 任务标识。
    :type task_id: str
    :return: 产物列表响应。
    :rtype: JSONResponse
    """

    # 读取已完成或正在执行的任务状态。
    record = task_service.get_record(task_id)

    # 返回只包含任务自身产物的相对路径列表。
    return JSONResponse({"task_id": task_id, "artifacts": list(record.get("artifacts", []))})


@app.get("/api/tasks/{task_id}/artifacts/{artifact_path:path}")
def download_artifact(task_id: str, artifact_path: str):
    """
    下载本机任务结果文件。

    :param task_id: 任务标识。
    :type task_id: str
    :param artifact_path: 任务产物相对路径。
    :type artifact_path: str
    :return: 文件响应。
    :rtype: FileResponse
    """

    record = task_service.get_record(task_id)
    task_root = WEB_RUNTIME_ROOT / task_id
    path = (task_root / artifact_path).resolve()
    allowed = {(task_root / name).resolve() for name in record.get("artifacts", [])}
    if path not in allowed:
        raise HTTPException(status_code=404, detail="任务产物不存在")
    return FileResponse(path, filename=path.name)
