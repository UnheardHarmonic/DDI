# -*- coding: utf-8 -*-
"""
DDI 本地授权签名校验模块。

本模块负责查找授权文件、验证授权签名、检查授权开关、有效期、应用版本、机器码和 Windows 用户。
"""

# 导入 Base64 编解码模块。
import base64

# 导入当前登录用户模块。
import getpass

# 导入哈希摘要模块。
import hashlib

# 导入 JSON 序列化模块。
import json

# 导入操作系统接口模块。
import os

# 导入路径处理模块。
from pathlib import Path

# 导入主机名称读取模块。
import socket

# 导入系统运行状态模块。
import sys

# 导入日期模块。
from datetime import date

# 导入日期时间模块。
from datetime import datetime

# 导入签名异常类型。
from cryptography.exceptions import InvalidSignature

# 导入公钥加载函数。
from cryptography.hazmat.primitives.serialization import load_pem_public_key


# 定义默认授权文件名称。
LICENSE_FILE_NAME = "license.json"

# 定义授权配置目录名称。
LICENSE_CONFIG_DIR_NAME = "config"

# 定义显式授权路径环境变量名称。
LICENSE_PATH_ENV_NAME = "DDI_LICENSE_PATH"

# 定义共享授权路径环境变量名称。
SHARED_LICENSE_PATH_ENV_NAME = "DDI_SHARED_LICENSE_PATH"

# 定义本机源码开发授权文件名称。
LOCAL_DEVELOPMENT_LICENSE_FILE_NAME = "local_development.json"

# 定义本机源码开发授权模式名称。
LOCAL_DEVELOPMENT_LICENSE_MODE = "source-development"

# 定义本机开发授权身份不匹配错误文本集合。
LOCAL_DEVELOPMENT_IDENTITY_MISMATCH_ERRORS = frozenset({"本机开发授权不属于当前电脑", "本机开发授权电脑名称不匹配", "本机开发授权 Windows 用户不匹配"})

# 定义当前应用授权版本。
DEFAULT_LICENSE_VERSION = "DDI_V4.0"

# 定义内置 Ed25519 公钥。
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAbfLX3zu9wDGTRQr1KG8gYHZcGyx5lKKHCtlud8EUIb0=
-----END PUBLIC KEY-----
"""


# 定义授权校验异常类型。
class LicenseError(RuntimeError):

    """
    DDI 授权校验异常。

    :return: 授权校验异常实例。
    :rtype: LicenseError
    """


# 定义运行授权校验函数。
def ensure_runtime_license(project_root, app_version=DEFAULT_LICENSE_VERSION, required_owner_names=None):

    """
    校验当前运行环境授权。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :param app_version: 当前应用授权版本。
    :type app_version: str
    :param required_owner_names: 本次任务涉及的负责人列表。
    :type required_owner_names: list[str] | None
    :return: 授权校验结果。
    :rtype: dict
    """

    # 读取仅限当前源码副本的本机开发授权。
    local_development_result = resolve_local_development_license(project_root, app_version)

    # 判断本机开发授权是否有效。
    if local_development_result:

        # 返回本机开发授权结果。
        return local_development_result

    # 解析候选授权文件路径列表。
    license_paths = resolve_license_paths(project_root)

    # 遍历候选授权文件路径。
    for license_path in license_paths:

        # 判断授权文件是否存在。
        if os.path.exists(license_path):

            # 读取授权文件数据。
            license_data = load_license_data(license_path)

            # 校验授权文件数据。
            result = validate_license_data(license_data, app_version, required_owner_names)

            # 记录实际命中的授权文件路径。
            result["授权文件"] = license_path

            # 返回授权校验结果。
            return result

    # 抛出授权文件缺失异常。
    raise LicenseError(f"未找到授权文件，请将 {LICENSE_FILE_NAME} 放到程序目录或配置 {LICENSE_PATH_ENV_NAME}")


# 定义本机开发授权解析函数。
def resolve_local_development_license(project_root, app_version):

    """
    读取仅限源码开发环境与当前机器的本地开发授权。

    :param project_root: DDI 项目根目录。
    :type project_root: str | Path
    :param app_version: 当前应用授权版本。
    :type app_version: str
    :return: 本机开发授权结果或空值。
    :rtype: dict | None
    """

    # 判断当前是否为可使用开发授权的源码环境。
    if not is_source_development_context(project_root):

        # 返回不启用本机开发授权结果。
        return None

    # 构建本机开发授权文件路径。
    development_license_path = Path(project_root).resolve() / LICENSE_CONFIG_DIR_NAME / LOCAL_DEVELOPMENT_LICENSE_FILE_NAME

    # 判断本机开发授权文件是否不存在。
    if not development_license_path.exists():

        # 返回未配置本机开发授权结果。
        return None

    # 读取本机开发授权文件数据。
    development_license_data = load_license_data(str(development_license_path))

    # 尝试校验本机开发授权文件数据。
    try:

        # 执行本机开发授权完整校验。
        validate_local_development_license_data(development_license_data, app_version)

    # 处理本机开发授权校验异常。
    except LicenseError as error:

        # 判断开发授权是否来自其他电脑。
        if str(error) in LOCAL_DEVELOPMENT_IDENTITY_MISMATCH_ERRORS:

            # 返回空值以继续验证带签名的正式授权。
            return None

        # 继续抛出同机开发授权的配置异常。
        raise

    # 构建本机开发授权结果。
    result = {"授权编号": development_license_data.get("license_id", "LOCAL-DEVELOPMENT"), "授权状态": "本机开发模式", "过期日期": "仅当前源码副本", "负责人权限": "全部（本机开发）", "授权文件": str(development_license_path)}

    # 返回本机开发授权结果。
    return result


# 定义源码开发环境识别函数。
def is_source_development_context(project_root):

    """
    判断授权请求是否来自当前源码副本而非冻结发布程序。

    :param project_root: DDI 项目根目录。
    :type project_root: str | Path
    :return: 是否为当前源码开发环境。
    :rtype: bool
    """

    # 判断当前进程是否为 PyInstaller 等冻结发布程序。
    if bool(getattr(sys, "frozen", False)):

        # 拒绝冻结发布程序使用本机开发授权。
        return False

    # 读取授权模块所在源码根目录。
    source_project_root = Path(__file__).resolve().parent.parent

    # 捕获传入路径无法解析的情况。
    try:

        # 解析调用方项目根目录。
        requested_project_root = Path(project_root).resolve()

    # 处理路径解析失败。
    except (OSError, RuntimeError, TypeError, ValueError):

        # 返回非源码开发环境结果。
        return False

    # 返回是否为当前源码副本。
    return requested_project_root == source_project_root


# 定义本机开发授权校验函数。
def validate_local_development_license_data(license_data, app_version):

    """
    校验本机开发授权的模式、版本与机器身份。

    :param license_data: 本机开发授权数据。
    :type license_data: dict
    :param app_version: 当前应用授权版本。
    :type app_version: str
    :return: None。
    :rtype: None
    """

    # 读取本机开发授权模式。
    license_mode = str(license_data.get("mode", "")).strip()

    # 判断授权模式是否不是源码开发模式。
    if license_mode != LOCAL_DEVELOPMENT_LICENSE_MODE:

        # 抛出开发授权模式无效异常。
        raise LicenseError("本机开发授权模式无效")

    # 判断本机开发授权是否已启用。
    if not bool(license_data.get("enabled", False)):

        # 抛出本机开发授权已停用异常。
        raise LicenseError("本机开发授权已停用")

    # 读取允许的授权版本列表。
    allowed_versions = normalize_string_list(license_data.get("allowed_versions", []))

    # 判断当前版本是否不在允许列表。
    if app_version not in allowed_versions:

        # 抛出本机开发授权版本无效异常。
        raise LicenseError(f"本机开发授权不允许当前版本: {app_version}")

    # 读取当前运行环境身份信息。
    runtime_identity = build_runtime_identity()

    # 读取开发授权机器码。
    allowed_machine_code = str(license_data.get("machine_code", "")).strip().upper()

    # 判断当前机器码是否不匹配。
    if allowed_machine_code != runtime_identity["machine_code"]:

        # 抛出本机开发授权机器码不匹配异常。
        raise LicenseError("本机开发授权不属于当前电脑")

    # 读取开发授权电脑名称。
    allowed_machine_name = str(license_data.get("machine_name", "")).strip().lower()

    # 判断当前电脑名称是否不匹配。
    if allowed_machine_name != runtime_identity["machine_name"].lower():

        # 抛出本机开发授权电脑名称不匹配异常。
        raise LicenseError("本机开发授权电脑名称不匹配")

    # 读取开发授权 Windows 用户。
    allowed_user_name = str(license_data.get("user_name", "")).strip().lower()

    # 判断当前 Windows 用户是否不匹配。
    if allowed_user_name != runtime_identity["user_name"].lower():

        # 抛出本机开发授权 Windows 用户不匹配异常。
        raise LicenseError("本机开发授权 Windows 用户不匹配")


# 定义授权文件路径解析函数。
def resolve_license_paths(project_root):

    """
    解析授权文件候选路径。

    :param project_root: DDI 项目根目录。
    :type project_root: str
    :return: 授权文件候选路径列表。
    :rtype: list[str]
    """

    # 初始化候选路径列表。
    license_paths = []

    # 追加显式授权文件路径。
    append_env_path(license_paths, LICENSE_PATH_ENV_NAME)

    # 追加共享授权文件路径。
    append_env_path(license_paths, SHARED_LICENSE_PATH_ENV_NAME)

    # 追加项目配置目录授权文件路径。
    license_paths.append(os.path.join(project_root, LICENSE_CONFIG_DIR_NAME, LICENSE_FILE_NAME))

    # 追加项目根目录授权文件路径。
    license_paths.append(os.path.join(project_root, LICENSE_FILE_NAME))

    # 返回按顺序去重后的路径列表。
    return deduplicate_paths(license_paths)


# 定义环境变量路径追加函数。
def append_env_path(license_paths, env_name):

    """
    将环境变量中的授权路径追加到候选路径列表。

    :param license_paths: 授权文件候选路径列表。
    :type license_paths: list[str]
    :param env_name: 环境变量名称。
    :type env_name: str
    :return: None。
    :rtype: None
    """

    # 读取环境变量路径。
    env_path = os.environ.get(env_name, "").strip()

    # 判断环境变量路径是否为空。
    if not env_path:

        # 结束当前环境变量处理。
        return

    # 判断环境变量路径是否为目录。
    if os.path.isdir(env_path):

        # 追加目录下的默认授权文件路径。
        license_paths.append(os.path.join(env_path, LICENSE_FILE_NAME))

        # 结束目录路径处理。
        return

    # 追加环境变量指定的授权文件路径。
    license_paths.append(env_path)


# 定义路径去重函数。
def deduplicate_paths(paths):

    """
    对路径列表按顺序去重。

    :param paths: 原始路径列表。
    :type paths: list[str]
    :return: 去重后的路径列表。
    :rtype: list[str]
    """

    # 初始化已存在路径集合。
    exists = set()

    # 初始化去重结果列表。
    result = []

    # 遍历原始路径列表。
    for path_value in paths:

        # 转换路径为绝对路径。
        normalized_path = os.path.abspath(path_value)

        # 判断路径是否已经存在。
        if normalized_path in exists:

            # 跳过重复路径。
            continue

        # 记录当前路径。
        exists.add(normalized_path)

        # 追加当前路径。
        result.append(normalized_path)

    # 返回去重结果列表。
    return result


# 定义授权文件读取函数。
def load_license_data(license_path):

    """
    读取授权文件 JSON 数据。

    :param license_path: 授权文件路径。
    :type license_path: str
    :return: 授权文件数据。
    :rtype: dict
    """

    # 打开授权文件。
    with open(license_path, "r", encoding="utf-8") as file_obj:

        # 读取授权文件 JSON 数据。
        license_data = json.load(file_obj)

    # 判断授权数据是否为字典。
    if not isinstance(license_data, dict):

        # 抛出授权文件格式异常。
        raise LicenseError("授权文件格式错误")

    # 返回授权文件数据。
    return license_data


# 定义授权数据校验函数。
def validate_license_data(license_data, app_version, required_owner_names=None):

    """
    校验授权文件数据。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :param app_version: 当前应用授权版本。
    :type app_version: str
    :param required_owner_names: 本次任务涉及的负责人列表。
    :type required_owner_names: list[str] | None
    :return: 授权校验结果。
    :rtype: dict
    """

    # 校验授权文件签名。
    verify_license_signature(license_data)

    # 校验授权启用状态。
    validate_enabled_status(license_data)

    # 校验授权有效期。
    validate_expire_date(license_data)

    # 校验授权应用版本。
    validate_app_version(license_data, app_version)

    # 校验当前机器码。
    validate_machine_code(license_data)

    # 校验当前电脑名称。
    validate_machine_name(license_data)

    # 校验当前 Windows 用户。
    validate_user_name(license_data)

    # 校验本次任务涉及的负责人。
    validate_responsible_persons(license_data, required_owner_names)

    # 读取负责人授权范围。
    allowed_owner_names = resolve_license_responsible_persons(license_data)

    # 构建负责人授权范围文本。
    owner_scope_text = "全部" if bool(license_data.get("allow_all_responsible_persons", False)) else "、".join(allowed_owner_names)

    # 构建授权校验结果。
    result = {"授权编号": license_data.get("license_id", ""), "授权状态": "有效", "过期日期": license_data.get("expire_date", ""), "负责人权限": owner_scope_text}

    # 返回授权校验结果。
    return result


# 定义授权签名校验函数。
def verify_license_signature(license_data):

    """
    校验授权文件数字签名。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: None。
    :rtype: None
    """

    # 读取授权签名文本。
    signature_text = str(license_data.get("signature", "")).strip()

    # 判断授权签名是否为空。
    if not signature_text:

        # 抛出授权签名缺失异常。
        raise LicenseError("授权文件缺少签名")

    # 生成签名载荷字节。
    payload_bytes = build_license_payload_bytes(license_data)

    # 解码授权签名字节。
    signature_bytes = decode_signature(signature_text)

    # 加载内置公钥。
    public_key = load_pem_public_key(PUBLIC_KEY_PEM)

    # 捕获签名校验异常。
    try:

        # 使用内置公钥校验授权签名。
        public_key.verify(signature_bytes, payload_bytes)

    # 处理签名无效异常。
    except InvalidSignature as error:

        # 抛出授权签名无效异常。
        raise LicenseError("授权文件签名无效") from error


# 定义授权签名解码函数。
def decode_signature(signature_text):

    """
    解码授权文件签名文本。

    :param signature_text: Base64 授权签名文本。
    :type signature_text: str
    :return: 授权签名字节。
    :rtype: bytes
    """

    # 捕获 Base64 解码异常。
    try:

        # 返回 Base64 解码后的签名字节。
        return base64.b64decode(signature_text.encode("ascii"), validate=True)

    # 处理 Base64 解码异常。
    except Exception as error:

        # 抛出授权签名格式异常。
        raise LicenseError("授权文件签名格式错误") from error


# 定义签名载荷构建函数。
def build_license_payload_bytes(license_data):

    """
    构建授权签名载荷字节。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: 授权签名载荷字节。
    :rtype: bytes
    """

    # 复制授权文件数据。
    payload_data = dict(license_data)

    # 移除签名字段。
    payload_data.pop("signature", None)

    # 序列化标准 JSON 载荷。
    payload_text = json.dumps(payload_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    # 返回 UTF-8 载荷字节。
    return payload_text.encode("utf-8")


# 定义授权启用状态校验函数。
def validate_enabled_status(license_data):

    """
    校验授权启用状态。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: None。
    :rtype: None
    """

    # 判断授权是否启用。
    if not bool(license_data.get("enabled", False)):

        # 抛出授权停用异常。
        raise LicenseError("当前授权已停用")


# 定义授权有效期校验函数。
def validate_expire_date(license_data):

    """
    校验授权有效期。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: None。
    :rtype: None
    """

    # 读取授权过期日期文本。
    expire_date_text = str(license_data.get("expire_date", "")).strip()

    # 判断授权过期日期是否为空。
    if not expire_date_text:

        # 抛出授权过期日期缺失异常。
        raise LicenseError("授权文件缺少过期日期")

    # 解析授权过期日期。
    expire_date_value = datetime.strptime(expire_date_text, "%Y-%m-%d").date()

    # 判断授权是否已经过期。
    if expire_date_value < date.today():

        # 抛出授权过期异常。
        raise LicenseError("当前授权已过期")


# 定义授权应用版本校验函数。
def validate_app_version(license_data, app_version):

    """
    校验授权应用版本。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :param app_version: 当前应用授权版本。
    :type app_version: str
    :return: None。
    :rtype: None
    """

    # 读取授权版本列表。
    allowed_versions = normalize_string_list(license_data.get("allowed_versions", []))

    # 判断授权版本列表是否为空。
    if not allowed_versions:

        # 结束版本校验。
        return

    # 判断当前版本是否在授权版本列表内。
    if app_version not in allowed_versions:

        # 抛出应用版本未授权异常。
        raise LicenseError(f"当前版本未授权运行: {app_version}")


# 定义机器码校验函数。
def validate_machine_code(license_data):

    """
    校验当前机器码是否在授权范围内。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: None。
    :rtype: None
    """

    # 读取授权机器码列表。
    allowed_machine_codes = normalize_string_list(license_data.get("allowed_machine_codes", []))

    # 判断授权机器码列表是否为空。
    if not allowed_machine_codes:

        # 结束机器码校验。
        return

    # 读取当前机器身份信息。
    runtime_identity = build_runtime_identity()

    # 读取当前机器码。
    current_machine_code = runtime_identity["machine_code"]

    # 判断当前机器码是否在授权列表内。
    if current_machine_code not in allowed_machine_codes:

        # 抛出机器码未授权异常。
        raise LicenseError("当前电脑未被授权运行")


# 定义电脑名称校验函数。
def validate_machine_name(license_data):

    """
    校验当前电脑名称是否在授权范围内。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: None。
    :rtype: None
    """

    # 读取授权电脑名称列表。
    allowed_machines = normalize_string_list(license_data.get("allowed_machines", []))

    # 判断授权电脑名称列表是否为空。
    if not allowed_machines:

        # 结束电脑名称校验。
        return

    # 读取当前电脑名称。
    current_machine = socket.gethostname().strip().lower()

    # 构建授权电脑名称集合。
    allowed_machine_set = {machine.strip().lower() for machine in allowed_machines}

    # 判断当前电脑名称是否在授权集合内。
    if current_machine not in allowed_machine_set:

        # 抛出电脑名称未授权异常。
        raise LicenseError("当前电脑名称未被授权运行")


# 定义 Windows 用户校验函数。
def validate_user_name(license_data):

    """
    校验当前 Windows 用户是否在授权范围内。

    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: None。
    :rtype: None
    """

    # 读取授权用户列表。
    allowed_users = normalize_string_list(license_data.get("allowed_users", []))

    # 判断授权用户列表是否为空。
    if not allowed_users:

        # 结束用户校验。
        return

    # 读取当前 Windows 用户名称。
    current_user = getpass.getuser().strip().lower()

    # 构建授权用户集合。
    allowed_user_set = {user.strip().lower() for user in allowed_users}

    # 判断当前用户是否在授权集合内。
    if current_user not in allowed_user_set:

        # 抛出 Windows 用户未授权异常。
        raise LicenseError("当前 Windows 用户未被授权运行")


# 定义负责人授权范围解析函数。
def resolve_license_responsible_persons(license_data):

    """
    解析授权文件中的负责人授权范围。
    :param license_data: 授权文件数据。
    :type license_data: dict
    :return: 负责人授权范围列表。
    :rtype: list[str]
    """

    # 读取负责人授权字段。
    allowed_owners = normalize_string_list(license_data.get("allowed_responsible_persons", []))

    # 初始化去重后的负责人列表。
    result = []

    # 遍历负责人授权范围。
    for owner_name in allowed_owners:

        # 标准化负责人名称。
        normalized_owner_name = owner_name.strip()

        # 判断负责人名称是否为空。
        if not normalized_owner_name:

            # 进入下一项负责人名称。
            continue

        # 判断负责人名称是否已经存在。
        if normalized_owner_name in result:

            # 进入下一项负责人名称。
            continue

        # 追加负责人名称。
        result.append(normalized_owner_name)

    # 返回负责人授权范围列表。
    return result


# 定义负责人授权校验函数。
def validate_responsible_persons(license_data, required_owner_names=None):

    """
    校验授权文件允许的业务负责人范围。
    :param license_data: 授权文件数据。
    :type license_data: dict
    :param required_owner_names: 本次任务涉及的负责人列表。
    :type required_owner_names: list[str] | None
    :return: None。
    :rtype: None
    """

    # 标准化本次任务涉及的负责人列表。
    required_owners = normalize_string_list(required_owner_names)

    # 读取负责人授权字段。
    allowed_owners = normalize_string_list(license_data.get("allowed_responsible_persons", []))

    # 判断授权文件是否允许全部负责人。
    if bool(license_data.get("allow_all_responsible_persons", False)):

        # 结束负责人授权校验。
        return

    # 判断授权文件是否缺少负责人范围。
    if not allowed_owners:

        # 抛出负责人授权配置缺失异常。
        raise LicenseError("授权文件缺少负责人权限配置")

    # 判断本次任务是否没有负责人约束输入。
    if not required_owners:

        # 结束负责人授权校验。
        return

    # 构建授权负责人集合。
    allowed_owner_set = {owner.strip().lower() for owner in allowed_owners if owner.strip()}

    # 筛选未被授权覆盖的负责人。
    missing_owners = [owner for owner in required_owners if owner.strip().lower() not in allowed_owner_set]

    # 判断是否存在未授权负责人。
    if missing_owners:

        # 抛出负责人授权范围异常。
        raise LicenseError(f"授权文件不允许当前负责人：{', '.join(missing_owners)}")


# 定义字符串列表标准化函数。
def normalize_string_list(value):

    """
    将授权配置值标准化为字符串列表。

    :param value: 授权配置原始值。
    :type value: object
    :return: 标准化后的字符串列表。
    :rtype: list[str]
    """

    # 判断原始值是否为空。
    if value is None:

        # 返回空列表。
        return []

    # 判断原始值是否为字符串。
    if isinstance(value, str):

        # 返回单元素字符串列表。
        return [value]

    # 判断原始值是否为列表或元组。
    if isinstance(value, (list, tuple)):

        # 返回过滤空值后的字符串列表。
        return [str(item).strip() for item in value if str(item).strip()]

    # 返回原始值的字符串形式列表。
    return [str(value).strip()]


# 定义运行环境身份构建函数。
def build_runtime_identity():

    """
    构建当前运行环境身份信息。

    :return: 当前运行环境身份信息。
    :rtype: dict
    """

    # 读取当前电脑名称。
    machine_name = socket.gethostname().strip()

    # 读取当前 Windows 用户名称。
    user_name = getpass.getuser().strip()

    # 读取 Windows 机器 GUID。
    machine_guid = read_windows_machine_guid()

    # 构建机器码源文本。
    machine_code_source = "|".join([machine_guid.lower(), machine_name.lower(), user_name.lower()])

    # 计算机器码哈希摘要。
    machine_code = hashlib.sha256(machine_code_source.encode("utf-8")).hexdigest().upper()

    # 返回运行环境身份信息。
    return {"machine_name": machine_name, "user_name": user_name, "machine_guid": machine_guid, "machine_code": machine_code}


# 定义 Windows 机器 GUID 读取函数。
def read_windows_machine_guid():

    """
    读取 Windows MachineGuid。

    :return: Windows MachineGuid 或空字符串。
    :rtype: str
    """

    # 捕获非 Windows 环境或注册表读取异常。
    try:

        # 导入 Windows 注册表模块。
        import winreg

        # 打开 Windows 加密配置注册表项。
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key_obj:

            # 读取 MachineGuid 注册表值。
            machine_guid = winreg.QueryValueEx(key_obj, "MachineGuid")[0]

        # 返回 MachineGuid 文本。
        return str(machine_guid).strip()

    # 处理注册表读取异常。
    except Exception:

        # 返回空机器 GUID。
        return ""
