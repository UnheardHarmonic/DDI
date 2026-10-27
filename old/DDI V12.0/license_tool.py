# -*- coding: utf-8 -*-
"""
DDI 授权文件生成工具。

本工具使用用户持有的 Ed25519 私钥生成带签名的 license.json 授权文件。
"""

# 导入参数解析模块。
import argparse

# 导入 Base64 编码模块。
import base64

# 导入 JSON 序列化模块。
import json

# 导入操作系统接口模块。
import os

# 导入系统路径模块。
import sys

# 导入日期模块。
from datetime import date

# 导入路径处理类型。
from pathlib import Path

# 导入私钥加载函数。
from cryptography.hazmat.primitives.serialization import load_pem_private_key


# 定义项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 将项目根目录加入模块搜索路径。
sys.path.insert(0, str(PROJECT_ROOT))

# 导入授权载荷构建函数。
from ddi_framework import build_license_payload_bytes

# 导入默认授权版本。
from ddi_framework import DEFAULT_LICENSE_VERSION

# 导入授权文件默认名称。
from ddi_framework import LICENSE_FILE_NAME

# 导入运行环境身份构建函数。
from ddi_framework import build_runtime_identity


# 定义配置目录名称。
LICENSE_CONFIG_DIR_NAME = "config"


# 定义授权输出目录名称。
LICENSE_OUTPUT_DIR_NAME = "license_outputs"


# 定义本机授权输出目录名称。
SELF_LICENSE_OUTPUT_DIR_NAME = "self"


# 定义同事授权输出目录名称。
COLLEAGUE_LICENSE_OUTPUT_DIR_NAME = "colleague"


# 定义默认运行授权路径解析函数。
def resolve_default_runtime_license_path():

    """
    解析程序运行时默认读取的授权文件路径。

    :return: 默认运行授权文件路径。
    :rtype: pathlib.Path
    """

    # 返回配置目录下的默认授权文件路径。
    return PROJECT_ROOT / LICENSE_CONFIG_DIR_NAME / LICENSE_FILE_NAME


# 定义交互式授权输出路径解析函数。
def resolve_interactive_license_output_path(use_current_machine):

    """
    根据授权目标解析交互式授权输出路径。

    :param use_current_machine: 是否使用当前电脑作为授权目标。
    :type use_current_machine: bool
    :return: 交互式授权输出路径。
    :rtype: pathlib.Path
    """

    # 解析授权目标目录名称。
    target_dir_name = SELF_LICENSE_OUTPUT_DIR_NAME if use_current_machine else COLLEAGUE_LICENSE_OUTPUT_DIR_NAME

    # 返回授权目标目录下的默认授权文件路径。
    return PROJECT_ROOT / LICENSE_CONFIG_DIR_NAME / LICENSE_OUTPUT_DIR_NAME / target_dir_name / LICENSE_FILE_NAME


# 定义参数解析器构建函数。
def build_parser():

    """
    构建授权生成工具命令行参数解析器。

    :return: 命令行参数解析器。
    :rtype: argparse.ArgumentParser
    """

    # 初始化命令行参数解析器。
    parser = argparse.ArgumentParser(description="生成 DDI 本地授权文件")

    # 添加私钥路径参数。
    parser.add_argument("--private-key", required=False, help="Ed25519 私钥 PEM 文件路径")

    # 添加本机机器码显示参数。
    parser.add_argument("--show-machine-code", action="store_true", help="只显示当前电脑授权机器码")

    # 添加输出路径参数。
    parser.add_argument("--output", default=str(resolve_default_runtime_license_path()), help="license.json 输出路径")

    # 添加授权编号参数。
    parser.add_argument("--license-id", default=f"DDI-{date.today().strftime('%Y%m%d')}-LOCAL", help="授权编号")

    # 添加过期日期参数。
    parser.add_argument("--expire-date", required=False, help="授权过期日期，格式为 YYYY-MM-DD")

    # 添加应用版本参数。
    parser.add_argument("--version", action="append", dest="versions", help="允许运行的 DDI 版本，可重复传入")

    # 添加机器码参数。
    parser.add_argument("--machine-code", action="append", dest="machine_codes", help="允许运行的机器码，可重复传入")

    # 添加电脑名称参数。
    parser.add_argument("--machine", action="append", dest="machines", help="允许运行的电脑名称，可重复传入")

    # 添加 Windows 用户参数。
    parser.add_argument("--user", action="append", dest="users", help="允许运行的 Windows 用户，可重复传入")

    # 添加业务负责人参数。
    parser.add_argument("--responsible-person", action="append", dest="responsible_persons", help="允许运行的业务负责人，可重复传入")

    # 添加全部负责人授权参数。
    parser.add_argument("--allow-all-responsible-persons", action="store_true", help="允许运行全部业务负责人")

    # 添加任意机器开关参数。
    parser.add_argument("--allow-any-machine", action="store_true", help="不限制机器码和电脑名称")

    # 添加任意用户开关参数。
    parser.add_argument("--allow-any-user", action="store_true", help="不限制 Windows 用户")

    # 添加停用授权开关参数。
    parser.add_argument("--disabled", action="store_true", help="生成停用状态授权")

    # 返回参数解析器。
    return parser


# 定义授权数据构建函数。
def build_license_data(args):

    """
    根据命令行参数构建授权数据。

    :param args: 命令行参数命名空间。
    :type args: argparse.Namespace
    :return: 未签名授权数据。
    :rtype: dict
    """

    # 构建当前运行环境身份信息。
    runtime_identity = build_runtime_identity()

    # 解析允许的版本列表。
    versions = args.versions or [DEFAULT_LICENSE_VERSION]

    # 解析允许的机器码列表。
    machine_codes = [] if args.allow_any_machine else args.machine_codes or [runtime_identity["machine_code"]]

    # 解析允许的电脑名称列表。
    machines = [] if args.allow_any_machine or args.machine_codes and not args.machines else args.machines or [runtime_identity["machine_name"]]

    # 解析允许的用户列表。
    users = [] if args.allow_any_user or args.machine_codes and not args.users else args.users or [runtime_identity["user_name"]]

    # 读取负责人授权范围。
    responsible_persons = getattr(args, "responsible_persons", None) or []

    # 读取全部负责人授权状态。
    allow_all_responsible_persons = bool(getattr(args, "allow_all_responsible_persons", False))

    # 校验负责人授权范围是否完整。
    if not allow_all_responsible_persons and not responsible_persons:

        # 抛出负责人授权范围缺失异常。
        raise ValueError("请指定授权负责人，或启用全部负责人权限")

    # 构建授权数据字典。
    license_data = {
        "license_id": args.license_id,
        "enabled": not bool(args.disabled),
        "expire_date": args.expire_date,
        "allowed_versions": versions,
        "allowed_machine_codes": machine_codes,
        "allowed_machines": machines,
        "allowed_users": users,
        "allow_all_responsible_persons": allow_all_responsible_persons,
        "allowed_responsible_persons": [] if allow_all_responsible_persons else responsible_persons,
        "issued_at": date.today().isoformat(),
    }

    # 返回未签名授权数据。
    return license_data


# 定义私钥加载函数。
def load_private_key(private_key_path):

    """
    从 PEM 文件读取 Ed25519 私钥。

    :param private_key_path: 私钥 PEM 文件路径。
    :type private_key_path: str
    :return: Ed25519 私钥对象。
    :rtype: object
    """

    # 转换私钥路径对象。
    path_obj = Path(private_key_path)

    # 判断私钥路径是否存在。
    if not path_obj.exists():

        # 抛出私钥文件不存在异常。
        raise ValueError(f"私钥文件不存在: {path_obj}")

    # 判断私钥路径是否为文件。
    if not path_obj.is_file():

        # 抛出私钥路径类型异常。
        raise ValueError(f"私钥路径不是文件: {path_obj}")

    # 读取私钥 PEM 字节。
    private_key_bytes = path_obj.read_bytes()

    # 加载私钥对象。
    private_key = load_pem_private_key(private_key_bytes, password=None)

    # 返回私钥对象。
    return private_key


# 定义授权签名函数。
def sign_license_data(license_data, private_key):

    """
    使用 Ed25519 私钥签名授权数据。

    :param license_data: 未签名授权数据。
    :type license_data: dict
    :param private_key: Ed25519 私钥对象。
    :type private_key: object
    :return: 已签名授权数据。
    :rtype: dict
    """

    # 构建授权签名载荷字节。
    payload_bytes = build_license_payload_bytes(license_data)

    # 生成授权签名字节。
    signature_bytes = private_key.sign(payload_bytes)

    # 复制授权数据。
    signed_data = dict(license_data)

    # 写入 Base64 签名文本。
    signed_data["signature"] = base64.b64encode(signature_bytes).decode("ascii")

    # 返回已签名授权数据。
    return signed_data


# 定义授权文件写入函数。
def write_license_file(output_path, license_data):

    """
    将授权数据写入 JSON 文件。

    :param output_path: 授权文件输出路径。
    :type output_path: str
    :param license_data: 已签名授权数据。
    :type license_data: dict
    :return: 授权文件输出路径。
    :rtype: pathlib.Path
    """

    # 转换输出路径对象。
    path_obj = Path(output_path)

    # 判断输出路径是否为已存在目录。
    if path_obj.exists() and path_obj.is_dir():

        # 将目录路径转换为默认授权文件路径。
        path_obj = path_obj / LICENSE_FILE_NAME

    # 确保输出目录存在。
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    # 序列化授权数据文本。
    license_text = json.dumps(license_data, ensure_ascii=False, indent=2)

    # 写入授权文件文本。
    path_obj.write_text(license_text + "\n", encoding="utf-8")

    # 返回输出路径对象。
    return path_obj


# 定义交互式输入读取函数。
def read_interactive_input(prompt_text, default_value=""):

    """
    读取交互式菜单输入内容。

    :param prompt_text: 输入提示文本。
    :type prompt_text: str
    :param default_value: 默认输入值。
    :type default_value: str
    :return: 用户输入值或默认值。
    :rtype: str
    """

    # 构建默认值展示文本。
    default_text = f" [{default_value}]" if default_value else ""

    # 读取用户输入文本。
    input_text = input(f"{prompt_text}{default_text}: ").strip()

    # 去除用户输入两侧引号。
    input_text = input_text.strip("\"'")

    # 判断用户是否显式选择默认值。
    if input_text == "." and default_value:

        # 返回默认值。
        return default_value

    # 返回用户输入值或默认值。
    return input_text or default_value


# 定义交互式菜单标题打印函数。
def print_interactive_title():

    """
    打印授权工具交互式菜单标题。

    :return: None。
    :rtype: None
    """

    # 打印标题空行。
    print()

    # 打印工具标题。
    print("DDI 授权工具")

    # 打印标题分隔线。
    print("=" * 36)


# 定义交互式菜单选项打印函数。
def print_interactive_options():

    """
    打印授权工具交互式菜单选项。

    :return: None。
    :rtype: None
    """

    # 打印本机机器码选项。
    print("1. 查看本机机器码")

    # 打印本机授权生成选项。
    print("2. 生成本机 license.json")

    # 打印外部机器授权生成选项。
    print("3. 根据对方机器码生成 license.json")

    # 打印退出选项。
    print("0. 退出")


# 定义交互式菜单执行函数。
def run_interactive_menu():

    """
    执行授权工具交互式菜单。

    :return: 进程退出码。
    :rtype: int
    """

    # 循环处理交互式菜单。
    while True:

        # 打印交互式菜单标题。
        print_interactive_title()

        # 打印交互式菜单选项。
        print_interactive_options()

        # 读取用户菜单选择。
        action_value = read_interactive_input("请选择", "1")

        # 判断用户是否选择查看机器码。
        if action_value == "1":

            # 打印当前运行环境身份信息。
            print_runtime_identity()

            # 等待用户确认继续。
            wait_interactive_continue()

            # 继续展示菜单。
            continue

        # 判断用户是否选择生成本机授权。
        if action_value == "2":

            # 执行本机授权生成流程。
            run_interactive_license_generation(use_current_machine=True)

            # 等待用户确认继续。
            wait_interactive_continue()

            # 继续展示菜单。
            continue

        # 判断用户是否选择生成外部机器授权。
        if action_value == "3":

            # 执行外部机器授权生成流程。
            run_interactive_license_generation(use_current_machine=False)

            # 等待用户确认继续。
            wait_interactive_continue()

            # 继续展示菜单。
            continue

        # 判断用户是否选择退出。
        if action_value == "0":

            # 返回成功退出码。
            return 0

        # 打印无效选择提示。
        print("菜单选择无效，请输入 1、2、3 或 0。")


# 定义交互式继续等待函数。
def wait_interactive_continue():

    """
    等待用户确认后继续展示菜单。

    :return: None。
    :rtype: None
    """

    # 读取继续确认输入。
    input("\n按回车继续...")


# 定义交互式授权生成函数。
def run_interactive_license_generation(use_current_machine):

    """
    执行交互式授权文件生成流程。

    :param use_current_machine: 是否使用当前电脑作为授权目标。
    :type use_current_machine: bool
    :return: 授权文件输出路径。
    :rtype: pathlib.Path
    """

    # 循环执行交互式授权生成流程。
    while True:

        # 捕获交互式授权生成异常。
        try:

            # 构建交互式授权参数。
            args = build_interactive_license_args(use_current_machine)

            # 加载 Ed25519 私钥。
            private_key = load_private_key(args.private_key)

            # 构建未签名授权数据。
            license_data = build_license_data(args)

            # 生成已签名授权数据。
            signed_data = sign_license_data(license_data, private_key)

            # 写入授权文件。
            output_path = write_license_file(args.output, signed_data)

            # 打印授权文件输出路径。
            print(f"\n授权文件已生成: {output_path}")

            # 返回授权文件输出路径。
            return output_path

        # 处理交互式授权生成异常。
        except Exception as error:

            # 打印授权生成失败原因。
            print(f"\n授权文件生成失败: {error}")

            # 读取是否重新填写的输入。
            retry_value = read_interactive_input("输入 1 重新填写，输入 0 返回菜单", "1")

            # 判断是否返回上级菜单。
            if retry_value == "0":

                # 返回空结果。
                return None


# 定义交互式授权参数构建函数。
def build_interactive_license_args(use_current_machine):

    """
    构建交互式授权生成参数。

    :param use_current_machine: 是否使用当前电脑作为授权目标。
    :type use_current_machine: bool
    :return: 授权生成参数命名空间。
    :rtype: argparse.Namespace
    """

    # 构建当前运行环境身份信息。
    runtime_identity = build_runtime_identity()

    # 读取私钥默认路径。
    default_private_key = read_default_private_key_path()

    # 读取私钥路径。
    private_key = read_interactive_input("请输入私钥 PEM 路径", default_private_key)

    # 读取授权过期日期。
    expire_date = read_interactive_input("请输入授权过期日期", build_default_expire_date())

    # 读取授权编号。
    license_id = read_interactive_input("请输入授权编号", f"DDI-{date.today().strftime('%Y%m%d')}-LOCAL")

    # 读取默认授权文件输出路径。
    default_output = str(resolve_interactive_license_output_path(use_current_machine))

    # 读取授权文件输出路径。
    output = read_interactive_input("请输入 license.json 输出路径", default_output)

    # 读取全部负责人授权状态。
    allow_all_responsible_persons = read_interactive_allow_all_responsible_persons()

    # 读取授权负责人列表。
    responsible_persons = [] if allow_all_responsible_persons else read_required_interactive_list("请输入授权负责人，多个负责人用英文逗号分隔")

    # 判断是否使用当前电脑机器码。
    if use_current_machine:

        # 构建当前电脑机器码列表。
        machine_codes = [runtime_identity["machine_code"]]

        # 构建当前电脑名称列表。
        machines = [runtime_identity["machine_name"]]

        # 构建当前 Windows 用户列表。
        users = [runtime_identity["user_name"]]

    # 处理外部机器授权参数。
    else:

        # 读取外部机器码列表。
        machine_codes = read_interactive_machine_codes()

        # 不限制外部电脑名称。
        machines = []

        # 不限制外部 Windows 用户。
        users = []

    # 构建命令行兼容参数命名空间。
    args = argparse.Namespace(private_key=private_key, output=output, license_id=license_id, expire_date=expire_date, versions=[DEFAULT_LICENSE_VERSION], machine_codes=machine_codes, machines=machines, users=users, responsible_persons=responsible_persons, allow_all_responsible_persons=allow_all_responsible_persons, allow_any_machine=False, allow_any_user=False, disabled=False)

    # 返回授权生成参数命名空间。
    return args


# 定义默认私钥路径读取函数。
def read_default_private_key_path():

    """
    读取交互式菜单使用的默认私钥路径。

    :return: 默认私钥路径。
    :rtype: str
    """

    # 读取环境变量私钥路径。
    env_private_key = os.environ.get("DDI_LICENSE_PRIVATE_KEY", "").strip()

    # 判断环境变量私钥路径是否有效。
    if env_private_key and Path(env_private_key).exists():

        # 返回环境变量私钥路径。
        return env_private_key

    # 初始化候选私钥路径列表。
    candidate_paths = [
        Path.home() / "ddi_license_private_key.pem",
        Path.home() / "Documents" / "Codex" / "ddi_license_private_key.pem",
        Path.home() / "Documents" / "Codex" / "2026-06-01" / "100-d-pycharmprojects-pythonproject-codex-ddi" / "outputs" / "ddi_license_private_key.pem",
        PROJECT_ROOT.parent / "ddi_license_private_key.pem",
        PROJECT_ROOT / "ddi_license_private_key.pem",
    ]

    # 遍历候选私钥路径列表。
    for candidate_path in candidate_paths:

        # 判断候选私钥路径是否存在。
        if candidate_path.exists():

            # 返回存在的候选私钥路径。
            return str(candidate_path)

    # 返回空私钥路径。
    return ""


# 定义默认过期日期构建函数。
def build_default_expire_date():

    """
    构建授权默认过期日期。

    :return: 默认过期日期文本。
    :rtype: str
    """

    # 构建当前年份最后一天日期。
    expire_date = date(date.today().year, 12, 31)

    # 返回 ISO 日期文本。
    return expire_date.isoformat()


# 定义全部负责人授权选择函数。
def read_interactive_allow_all_responsible_persons():

    """
    读取交互式输入中的全部负责人授权选择。
    :return: 是否授权全部负责人。
    :rtype: bool
    """

    # 持续读取全部负责人授权选择直到合法。
    while True:

        # 读取全部负责人授权选择。
        allow_all_value = read_interactive_input("是否授权全部负责人，1 否，2 是", "1")

        # 判断是否不授权全部负责人。
        if allow_all_value == "1":

            # 返回全部负责人授权关闭状态。
            return False

        # 判断是否授权全部负责人。
        if allow_all_value == "2":

            # 返回全部负责人授权开启状态。
            return True

        # 打印全部负责人授权选择无效提示。
        print("负责人授权选择无效，请输入 1 或 2。")


# 定义必填列表读取函数。
def read_required_interactive_list(prompt_text):

    """
    读取交互式输入中的必填文本列表。
    :param prompt_text: 输入提示文本。
    :type prompt_text: str
    :return: 文本列表。
    :rtype: list[str]
    """

    # 持续读取列表直到非空。
    while True:

        # 读取可选文本列表。
        value_list = read_optional_interactive_list(prompt_text)

        # 判断文本列表是否非空。
        if value_list:

            # 返回文本列表。
            return value_list

        # 打印列表缺失提示。
        print("授权负责人不能为空。")


# 定义可选列表读取函数。
def read_optional_interactive_list(prompt_text):

    """
    读取交互式输入中的可选文本列表。
    :param prompt_text: 输入提示文本。
    :type prompt_text: str
    :return: 文本列表。
    :rtype: list[str]
    """

    # 读取列表输入文本。
    value_text = read_interactive_input(prompt_text, "")

    # 标准化列表分隔符。
    normalized_text = value_text.replace("，", ",").replace("、", ",")

    # 返回过滤空值后的文本列表。
    return [item.strip() for item in normalized_text.split(",") if item.strip()]


# 定义外部机器码读取函数。
def read_interactive_machine_codes():

    """
    读取交互式输入的外部机器码列表。

    :return: 外部机器码列表。
    :rtype: list[str]
    """

    # 循环读取机器码直到非空。
    while True:

        # 读取机器码输入文本。
        machine_code_text = read_interactive_input("请输入对方机器码，多个机器码用英文逗号分隔")

        # 拆分机器码列表。
        machine_codes = [item.strip() for item in machine_code_text.split(",") if item.strip()]

        # 判断机器码列表是否为空。
        if machine_codes:

            # 返回机器码列表。
            return machine_codes

        # 打印机器码缺失提示。
        print("机器码不能为空。")


# 定义主函数。
def main():

    """
    执行授权文件生成流程。

    :return: 进程退出码。
    :rtype: int
    """

    # 判断是否没有传入命令行参数。
    if len(sys.argv) == 1:

        # 执行交互式菜单。
        return run_interactive_menu()

    # 构建命令行参数解析器。
    parser = build_parser()

    # 解析命令行参数。
    args = parser.parse_args()

    # 判断是否只显示当前机器码。
    if args.show_machine_code:

        # 打印当前运行环境身份信息。
        print_runtime_identity()

        # 返回成功退出码。
        return 0

    # 判断私钥路径是否为空。
    if not args.private_key:

        # 抛出私钥路径缺失参数错误。
        parser.error("--private-key 在生成授权文件时必须提供")

    # 判断授权过期日期是否为空。
    if not args.expire_date:

        # 抛出授权过期日期缺失参数错误。
        parser.error("--expire-date 在生成授权文件时必须提供")

    # 构建未签名授权数据。
    license_data = build_license_data(args)

    # 加载 Ed25519 私钥。
    private_key = load_private_key(args.private_key)

    # 生成已签名授权数据。
    signed_data = sign_license_data(license_data, private_key)

    # 写入授权文件。
    output_path = write_license_file(args.output, signed_data)

    # 打印授权文件路径。
    print(f"授权文件: {output_path}")

    # 打印当前运行环境身份信息。
    print_runtime_identity()

    # 返回成功退出码。
    return 0


# 定义运行环境身份打印函数。
def print_runtime_identity():

    """
    打印当前运行环境身份信息。

    :return: None。
    :rtype: None
    """

    # 构建当前运行环境身份信息。
    runtime_identity = build_runtime_identity()

    # 打印当前电脑名称。
    print(f"当前电脑: {runtime_identity['machine_name']}")

    # 打印当前用户名称。
    print(f"当前用户: {runtime_identity['user_name']}")

    # 打印当前机器码。
    print(f"当前机器码: {runtime_identity['machine_code']}")


# 判断当前文件是否以脚本方式执行。
if __name__ == "__main__":

    # 执行主函数并设置进程退出码。
    sys.exit(main())
