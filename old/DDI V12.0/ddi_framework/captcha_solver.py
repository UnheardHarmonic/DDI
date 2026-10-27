# -*- coding: utf-8 -*-
"""
验证码处理工具。

本模块封装滑块验证码、点选验证码和普通图片验证码的识别入口。
"""

# 导入 Base64 编解码模块。
import base64

# 导入 JSON 编解码模块。
import json

# 导入内存字节流模块。
from io import BytesIO

# 导入操作系统接口模块。
import os

# 导入正则表达式模块。
import re

# 导入 PNG 尺寸解析模块。
import struct

# 导入类型标注对象。
from typing import Any, Dict, Optional, Tuple


class AesEcbEncryptor:
    """
    AES-ECB-PKCS7 加密器。

    :return: AES 加密器实例。
    :rtype: AesEcbEncryptor
    """

    @staticmethod
    def encrypt_to_base64(plain_text, secret_key):
        """
        加密明文并返回 Base64 密文。

        :param plain_text: 待加密明文。
        :type plain_text: str
        :param secret_key: 16 字节 AES 密钥。
        :type secret_key: str
        :return: Base64 编码密文。
        :rtype: str
        """

        # 导入 AES 算法对象。
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        # 导入加密后端。
        from cryptography.hazmat.backends import default_backend

        # 编码 AES 密钥字节。
        key_bytes = secret_key.encode("utf-8")

        # 校验 AES 密钥长度。
        if len(key_bytes) not in [16, 24, 32]:

            # 抛出密钥长度异常。
            raise ValueError(f"AES 密钥长度必须为 16、24 或 32 字节，当前长度：{len(key_bytes)}")

        # 编码明文字节。
        plain_bytes = plain_text.encode("utf-8")

        # 计算 PKCS7 填充长度。
        padding_size = 16 - (len(plain_bytes) % 16)

        # 生成 PKCS7 填充后的明文。
        padded_bytes = plain_bytes + bytes([padding_size]) * padding_size

        # 创建 AES-ECB 加密器。
        encryptor = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend()).encryptor()

        # 执行 AES 加密。
        encrypted_bytes = encryptor.update(padded_bytes) + encryptor.finalize()

        # 返回 Base64 密文。
        return base64.b64encode(encrypted_bytes).decode("ascii")


class CaptchaSolver:
    """
    通用验证码识别器。

    :return: 通用验证码识别器实例。
    :rtype: CaptchaSolver
    """

    def __init__(self):
        """
        初始化通用验证码识别器。

        :return: None。
        :rtype: None
        """

        # 初始化 ddddocr 普通识别器。
        self.ocr = self._create_ocr(det=False, ocr=True)

        # 初始化 ddddocr 滑块识别器。
        self.slide_ocr = self._create_ocr(det=False, ocr=False)

        # 初始化最近一次 OpenCV 识别错误。
        self.last_cv2_error = ""

    def solve_text_image(self, image_bytes, min_length=4):
        """
        识别普通图片验证码。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :param min_length: 最小有效长度。
        :type min_length: int
        :return: 验证码文本。
        :rtype: str
        """

        # 校验 OCR 识别器是否可用。
        if self.ocr is None:
            return ""

        # 执行普通验证码识别。
        result = self.ocr.classification(image_bytes)

        # 清洗识别结果。
        cleaned = "".join([char for char in result if char.isalnum()])

        # 返回满足长度的识别结果。
        return cleaned if len(cleaned) >= min_length else ""

    def solve_raw_text_image(self, image_bytes):
        """
        识别普通图片验证码并保留原始文本。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :return: 原始验证码文本。
        :rtype: str
        """

        # 校验 OCR 识别器是否可用。
        if self.ocr is None:

            # 返回空识别结果。
            return ""

        # 执行普通验证码识别。
        result = self.ocr.classification(image_bytes)

        # 返回原始识别文本。
        return str(result or "").strip()

    def solve_raw_text_image_with_ranges(self, image_bytes, charset_range):
        """
        按限定字符范围识别普通图片验证码。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :param charset_range: 字符范围。
        :type charset_range: str | list[str]
        :return: 原始验证码文本。
        :rtype: str
        """

        # 校验 OCR 识别器是否可用。
        if self.ocr is None:

            # 返回空识别结果。
            return ""

        # 捕获字符范围设置异常。
        try:

            # 设置识别字符范围。
            self.ocr.set_ranges(charset_range)

            # 执行普通验证码识别。
            result = self.ocr.classification(image_bytes)

        # 字符范围设置失败时回退到普通识别。
        except Exception:

            # 执行普通验证码识别。
            result = self.ocr.classification(image_bytes)

        # 返回原始识别文本。
        return str(result or "").strip()

    def solve_math_image(self, image_bytes, right_operand_max_digits=None):
        """
        识别算式图片验证码并返回计算结果。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :param right_operand_max_digits: 右侧操作数最大位数。
        :type right_operand_max_digits: int | None
        :return: 算式验证码答案。
        :rtype: str
        """

        # 构建算式验证码答案候选列表。
        math_candidates = self.build_math_code_candidates(image_bytes, right_operand_max_digits=right_operand_max_digits)

        # 返回算式验证码答案。
        return math_candidates[0] if math_candidates else ""

    def build_math_code_candidates(self, image_bytes, right_operand_max_digits=None):
        """
        构建算式图片验证码答案候选列表。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :param right_operand_max_digits: 右侧操作数最大位数。
        :type right_operand_max_digits: int | None
        :return: 算式验证码答案候选列表。
        :rtype: list[str]
        """

        # 初始化候选答案列表。
        code_candidates = []

        # 遍历验证码图片预处理结果。
        for prepared_bytes in self.build_math_image_candidates(image_bytes):

            # 识别当前预处理图片。
            candidate_text = self.solve_raw_text_image_with_ranges(prepared_bytes, "0123456789+-*/")

            # 解析候选文本对应的算式答案。
            candidate_code = self.parse_math_captcha(candidate_text, right_operand_max_digits=right_operand_max_digits)

            # 保存非重复候选答案。
            if candidate_code and candidate_code not in code_candidates:

                # 追加候选答案。
                code_candidates.append(candidate_code)

        # 返回候选答案列表。
        return code_candidates

    def recognize_math_text(self, image_bytes):
        """
        识别算式图片验证码文本。

        :param image_bytes: 验证码图片字节流。
        :type image_bytes: bytes
        :return: 算式验证码识别文本。
        :rtype: str
        """

        # 初始化候选识别文本列表。
        candidate_texts = []

        # 遍历验证码图片预处理结果。
        for prepared_bytes in self.build_math_image_candidates(image_bytes):

            # 识别当前预处理图片。
            candidate_text = self.solve_raw_text_image_with_ranges(prepared_bytes, "0123456789+-*/")

            # 判断候选文本是否有效。
            if candidate_text:

                # 追加候选识别文本。
                candidate_texts.append(candidate_text)

        # 遍历候选文本查找可解析算式。
        for candidate_text in candidate_texts:

            # 判断候选文本是否可解析为算式。
            if self.parse_math_captcha(candidate_text):

                # 返回可解析候选文本。
                return candidate_text

        # 返回首个候选文本。
        return candidate_texts[0] if candidate_texts else ""

    def build_math_image_candidates(self, image_bytes):
        """
        构建算式验证码识别候选图片。

        :param image_bytes: 原始验证码图片字节流。
        :type image_bytes: bytes
        :return: 候选图片字节流列表。
        :rtype: list[bytes]
        """

        # 导入图片处理对象。
        from PIL import Image

        # 使用内存字节流读取验证码图片。
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        # 初始化候选图片列表。
        candidates = [image_bytes]

        # 读取验证码图片宽度。
        image_width = image.size[0]

        # 读取验证码图片高度。
        image_height = image.size[1]

        # 构建动态裁剪区域。
        crop_boxes = [
            (0, 0, min(image_width, 100), min(image_height, 60)),
            (0, 0, min(image_width, 110), min(image_height, 60)),
            (0, 0, image_width, image_height),
            (max(0, int(image_width * 0.03)), 0, min(image_width, int(image_width * 0.97)), image_height),
            (0, max(0, int(image_height * 0.08)), image_width, min(image_height, int(image_height * 0.92))),
        ]

        # 遍历固定裁剪区域。
        for crop_box in crop_boxes:

            # 裁剪表达式主体区域。
            cropped_image = image.crop(crop_box)

            # 放大表达式主体区域。
            resized_image = cropped_image.resize((cropped_image.width * 4, cropped_image.height * 4), Image.Resampling.LANCZOS)

            # 追加普通放大候选图片。
            candidates.append(self.image_to_png_bytes(resized_image))

            # 追加蓝色笔画候选图片。
            candidates.append(self.extract_blue_strokes(resized_image))

            # 追加深色笔画候选图片。
            candidates.append(self.extract_dark_strokes(resized_image))

        # 返回候选图片列表。
        return candidates

    def extract_blue_strokes(self, image):
        """
        提取验证码中的蓝色字符笔画。

        :param image: 验证码图片对象。
        :type image: Image.Image
        :return: 蓝色笔画二值化 PNG 字节流。
        :rtype: bytes
        """

        # 导入图片处理对象。
        from PIL import Image

        # 读取图片宽度。
        width = image.size[0]

        # 读取图片高度。
        height = image.size[1]

        # 创建白底图片。
        output_image = Image.new("RGB", (width, height), "white")

        # 遍历横向像素。
        for x in range(width):

            # 遍历纵向像素。
            for y in range(height):

                # 读取像素 RGB。
                red, green, blue = image.getpixel((x, y))

                # 判断像素是否属于蓝色笔画。
                if blue > 70 and blue > red + 25 and blue > green + 10:

                    # 写入黑色笔画像素。
                    output_image.putpixel((x, y), (0, 0, 0))

        # 返回 PNG 字节流。
        return self.image_to_png_bytes(output_image)

    def extract_dark_strokes(self, image):
        """
        提取验证码中的深色字符笔画。

        :param image: 验证码图片对象。
        :type image: Image.Image
        :return: 深色笔画二值化 PNG 字节流。
        :rtype: bytes
        """

        # 导入图片处理对象。
        from PIL import Image

        # 读取图片宽度。
        width = image.size[0]

        # 读取图片高度。
        height = image.size[1]

        # 创建白底图片。
        output_image = Image.new("RGB", (width, height), "white")

        # 遍历横向像素。
        for x in range(width):

            # 遍历纵向像素。
            for y in range(height):

                # 读取像素 RGB。
                red, green, blue = image.getpixel((x, y))

                # 计算像素平均亮度。
                brightness = int((red + green + blue) / 3)

                # 判断像素是否属于深色笔画。
                if brightness < 180:

                    # 写入黑色笔画像素。
                    output_image.putpixel((x, y), (0, 0, 0))

        # 返回 PNG 字节流。
        return self.image_to_png_bytes(output_image)

    def image_to_png_bytes(self, image):
        """
        转换图片对象为 PNG 字节流。

        :param image: 图片对象。
        :type image: Image.Image
        :return: PNG 字节流。
        :rtype: bytes
        """

        # 创建内存字节流。
        buffer = BytesIO()

        # 保存图片为 PNG。
        image.save(buffer, format="PNG")

        # 返回 PNG 字节数据。
        return buffer.getvalue()

    def parse_math_captcha(self, raw_text, right_operand_max_digits=None):
        """
        解析算式验证码答案。

        :param raw_text: 原始验证码识别文本。
        :type raw_text: str
        :param right_operand_max_digits: 右侧操作数最大位数。
        :type right_operand_max_digits: int | None
        :return: 算式答案或空字符串。
        :rtype: str
        """

        # 统一算式符号文本。
        normalized_text = self.normalize_math_text(raw_text)

        # 读取算式中的左侧数字、运算符和右侧数字文本。
        match = re.search(r"(\d+)\s*([+\-*/])\s*(\d+)", normalized_text)

        # 未识别到算式时尝试解析缺失减号的单数字算式。
        if not match:

            # 解析缺失减号的单数字算式答案。
            inferred_code = self.parse_missing_minus_captcha(normalized_text, right_operand_max_digits)

            # 返回缺失减号的单数字算式答案。
            return inferred_code

        # 读取左侧数字。
        left_value = int(match.group(1))

        # 读取运算符。
        operator = match.group(2)

        # 读取右侧数字文本。
        right_text = match.group(3)

        # 按最大位数截取右侧操作数。
        right_text = right_text[:right_operand_max_digits] if right_operand_max_digits else right_text

        # 读取右侧数字。
        right_value = int(right_text)

        # 处理加法算式。
        if operator == "+":

            # 返回加法结果。
            return str(left_value + right_value)

        # 处理减法算式。
        if operator == "-":

            # 返回减法结果。
            return str(left_value - right_value)

        # 处理乘法算式。
        if operator == "*":

            # 返回乘法结果。
            return str(left_value * right_value)

        # 处理除法算式。
        if operator == "/" and right_value != 0:

            # 返回整数除法结果。
            return str(left_value // right_value)

        # 返回空算式答案。
        return ""

    def parse_missing_minus_captcha(self, normalized_text, right_operand_max_digits=None):
        """
        解析缺失减号的单数字算式验证码答案。

        :param normalized_text: 归一化算式文本。
        :type normalized_text: str
        :param right_operand_max_digits: 右侧操作数最大位数。
        :type right_operand_max_digits: int | None
        :return: 算式答案或空字符串。
        :rtype: str
        """

        # 校验是否启用单数字操作数模式。
        if right_operand_max_digits != 1:

            # 返回空算式答案。
            return ""

        # 匹配纯数字识别文本。
        match = re.fullmatch(r"(\d)(\d)\d?", normalized_text)

        # 未匹配到纯数字文本时返回空字符串。
        if not match:

            # 返回空算式答案。
            return ""

        # 读取左侧单数字操作数。
        left_value = int(match.group(1))

        # 读取右侧单数字操作数。
        right_value = int(match.group(2))

        # 返回减法算式结果。
        return str(left_value - right_value)

    def normalize_math_text(self, raw_text):
        """
        归一化算式验证码识别文本。

        :param raw_text: 原始验证码识别文本。
        :type raw_text: str
        :return: 归一化算式文本。
        :rtype: str
        """

        # 转换原始文本为字符串。
        text = str(raw_text or "")

        # 移除空白字符。
        text = re.sub(r"\s+", "", text)

        # 替换常见乘法符号。
        text = text.replace("×", "*").replace("X", "*").replace("x", "*")

        # 替换常见除法符号。
        text = text.replace("÷", "/")

        # 替换常见减号误识别。
        text = text.replace("一", "-").replace("_", "-")

        # 替换常见加号误识别。
        text = re.sub(r"(?<=\d)[tT](?=\d)", "+", text)

        # 保留算式相关字符。
        text = "".join([char for char in text if char.isdigit() or char in "+-*/"])

        # 返回归一化文本。
        return text

    def solve_slide_distance(self, original_image, jigsaw_image):
        """
        识别滑块验证码横向移动距离。

        :param original_image: 背景图片字节流。
        :type original_image: bytes
        :param jigsaw_image: 拼图图片字节流。
        :type jigsaw_image: bytes
        :return: 标准 310 像素坐标系下的横向移动距离。
        :rtype: float
        """

        # 构建滑块距离候选列表。
        distance_candidates = self.solve_slide_distance_candidates(original_image, jigsaw_image)

        # 返回首个滑块距离候选。
        if distance_candidates:

            # 返回最高优先级候选距离。
            return distance_candidates[0]

        # 抛出滑块识别失败异常。
        raise RuntimeError(f"滑块距离识别失败：{self.last_cv2_error or '无详细错误'}")

    def solve_slide_distance_candidates(self, original_image, jigsaw_image):
        """
        识别滑块验证码横向移动距离候选列表。

        :param original_image: 背景图片字节流。
        :type original_image: bytes
        :param jigsaw_image: 拼图图片字节流。
        :type jigsaw_image: bytes
        :return: 标准 310 像素坐标系下的横向移动距离候选列表。
        :rtype: list[float]
        """

        # 初始化距离候选列表。
        distance_candidates = []

        # 使用图像边缘匹配缺口位置。
        cv_distance = self._solve_slide_by_cv2(original_image, jigsaw_image)

        # 保存图像边缘匹配结果。
        self._append_distance_candidate(distance_candidates, cv_distance)

        # 使用滑块识别器匹配缺口位置。
        ocr_distance = self._solve_slide_by_ocr(original_image, jigsaw_image)

        # 保存滑块识别器匹配结果。
        self._append_distance_candidate(distance_candidates, ocr_distance)

        # 校验是否存在可用距离候选。
        if not distance_candidates:

            # 抛出滑块识别失败异常。
            raise RuntimeError(f"滑块距离识别失败：{self.last_cv2_error or '无详细错误'}")

        # 返回距离候选列表。
        return distance_candidates

    def _append_distance_candidate(self, distance_candidates, distance_value):
        """
        追加非重复滑块距离候选。

        :param distance_candidates: 距离候选列表。
        :type distance_candidates: list[float]
        :param distance_value: 距离候选值。
        :type distance_value: float | None
        :return: None。
        :rtype: None
        """

        # 跳过空候选距离。
        if distance_value is None:

            # 返回空值。
            return

        # 转换候选距离为一位小数。
        normalized_value = round(float(distance_value), 1)

        # 跳过越界候选距离。
        if normalized_value < 0 or normalized_value > 310:

            # 返回空值。
            return

        # 跳过重复候选距离。
        if normalized_value in distance_candidates:

            # 返回空值。
            return

        # 保存候选距离。
        distance_candidates.append(normalized_value)

    def _solve_slide_by_ocr(self, original_image, jigsaw_image):
        """
        使用滑块识别器识别横向移动距离。

        :param original_image: 背景图片字节流。
        :type original_image: bytes
        :param jigsaw_image: 拼图图片字节流。
        :type jigsaw_image: bytes
        :return: 横向移动距离或空值。
        :rtype: Optional[float]
        """

        try:
            # 校验滑块识别器是否可用。
            if self.slide_ocr is None:
                return None

            # 执行滑块匹配。
            match_result = self.slide_ocr.slide_match(jigsaw_image, original_image, simple_target=True)

            # 读取目标坐标。
            target = match_result.get("target") or match_result.get("target_point") or []

            # 校验目标坐标。
            if not target:
                return None

            # 读取背景图片宽度。
            image_width = self._read_png_size(original_image)[0]

            # 转换为前端标准坐标。
            normalized_x = float(target[0]) * 310.0 / float(image_width or 310)

            # 返回一位小数坐标。
            return round(normalized_x, 1)

        except Exception as error:
            # 记录识别错误。
            self.last_cv2_error = str(error)

            # 返回空值并交由备用识别路径处理。
            return None

    def build_anji_slide_payload(self, captcha_payload, move_distance, client_uid):
        """
        构建 Anji Plus 滑块验证码校验请求体。

        :param captcha_payload: 验证码上下文。
        :type captcha_payload: Dict[str, Any]
        :param move_distance: 滑块横向移动距离。
        :type move_distance: float
        :param client_uid: 客户端唯一标识。
        :type client_uid: str
        :return: 验证码校验请求体与登录二次校验密文。
        :rtype: Tuple[Dict[str, Any], str]
        """

        # 构建点位 JSON。
        point_json = self._point_json(move_distance)

        # 加密点位 JSON。
        encrypted_point = AesEcbEncryptor.encrypt_to_base64(point_json, captcha_payload["secretKey"])

        # 构建验证码校验请求体。
        check_payload = {"captchaType": "blockPuzzle", "pointJson": encrypted_point, "token": captcha_payload["token"], "clientUid": client_uid, "ts": int(__import__("time").time() * 1000)}

        # 构建登录二次校验明文。
        verification_plain = f"{captcha_payload['token']}---{point_json}"

        # 加密登录二次校验参数。
        captcha_verification = AesEcbEncryptor.encrypt_to_base64(verification_plain, captcha_payload["secretKey"])

        # 返回校验请求体与登录参数。
        return check_payload, captcha_verification

    def solve_click_points(self, image_bytes, prompt_words):
        """
        识别点选验证码坐标。

        :param image_bytes: 点选验证码图片字节流。
        :type image_bytes: bytes
        :param prompt_words: 需要依次点击的文字列表。
        :type prompt_words: list[str]
        :return: 点选坐标列表。
        :rtype: list[dict]
        """

        # 点选验证码保留统一入口。
        raise NotImplementedError("点选验证码识别需要按具体平台补充模型或人工兜底")

    def decode_base64_image(self, data_url_or_base64):
        """
        解码 Base64 图片。

        :param data_url_or_base64: data URL 或纯 Base64 字符串。
        :type data_url_or_base64: str
        :return: 图片字节流。
        :rtype: bytes
        """

        # 读取 Base64 内容。
        raw_base64 = data_url_or_base64.split("base64,", 1)[-1]

        # 返回解码后的图片字节。
        return base64.b64decode(raw_base64)

    def _solve_slide_by_cv2(self, original_image, jigsaw_image):
        """
        使用 OpenCV 模板匹配识别滑块距离。

        :param original_image: 背景图片字节流。
        :type original_image: bytes
        :param jigsaw_image: 拼图图片字节流。
        :type jigsaw_image: bytes
        :return: 横向移动距离或空值。
        :rtype: Optional[float]
        """

        try:
            # 导入内存字节流模块。
            import io

            # 导入 OpenCV 模块。
            import cv2

            # 导入 NumPy 模块。
            import numpy as np

            # 导入 PIL 图片模块。
            from PIL import Image

            # 解码背景图。
            background_array = cv2.imdecode(np.frombuffer(original_image, np.uint8), cv2.IMREAD_COLOR)

            # 解码拼图图。
            jigsaw_array = np.array(Image.open(io.BytesIO(jigsaw_image)).convert("RGBA"))

            # 读取透明通道。
            alpha_channel = jigsaw_array[:, :, 3]

            # 获取非透明像素坐标。
            y_indexes, x_indexes = np.where(alpha_channel > 10)

            # 校验非透明区域。
            if len(x_indexes) == 0 or len(y_indexes) == 0:
                return None

            # 裁剪拼图有效区域。
            jigsaw_crop = jigsaw_array[y_indexes.min():y_indexes.max() + 1, x_indexes.min():x_indexes.max() + 1, :3]

            # 转换背景为灰度图。
            background_gray = cv2.cvtColor(background_array, cv2.COLOR_BGR2GRAY)

            # 转换拼图为灰度图。
            jigsaw_gray = cv2.cvtColor(jigsaw_crop, cv2.COLOR_RGB2GRAY)

            # 提取背景边缘。
            background_edge = cv2.Canny(background_gray, 100, 200)

            # 提取拼图边缘。
            jigsaw_edge = cv2.Canny(jigsaw_gray, 100, 200)

            # 执行模板匹配。
            match_result = cv2.matchTemplate(background_edge, jigsaw_edge, cv2.TM_CCOEFF_NORMED)

            # 读取最大置信度位置。
            _, confidence, _, max_location = cv2.minMaxLoc(match_result)

            # 校验匹配置信度。
            if confidence < 0.35:
                return None

            # 读取背景图宽度。
            image_width = self._read_png_size(original_image)[0]

            # 转换为前端标准坐标。
            normalized_x = float(max_location[0]) * 310.0 / float(image_width or 310)

            # 返回一位小数坐标。
            return round(normalized_x, 1)

        except Exception as error:
            # 记录 OpenCV 识别错误。
            self.last_cv2_error = str(error)

            # 返回空值并交由备用识别器处理。
            return None

    def _read_png_size(self, image_bytes):
        """
        读取 PNG 图片尺寸。

        :param image_bytes: PNG 图片字节流。
        :type image_bytes: bytes
        :return: 图片宽度和高度。
        :rtype: Tuple[int, int]
        """

        # 校验 PNG 文件头。
        if len(image_bytes) < 24 or image_bytes[:8] != b"\x89PNG\r\n\x1a\n":
            return 310, 155

        # 读取 PNG 宽度。
        width = struct.unpack(">I", image_bytes[16:20])[0]

        # 读取 PNG 高度。
        height = struct.unpack(">I", image_bytes[20:24])[0]

        # 返回图片尺寸。
        return width, height

    def _point_json(self, move_distance):
        """
        生成滑块点位 JSON 字符串。

        :param move_distance: 滑块横向移动距离。
        :type move_distance: float
        :return: 点位 JSON 字符串。
        :rtype: str
        """

        # 转换横向距离为浏览器数字格式。
        x_value = int(move_distance) if float(move_distance).is_integer() else move_distance

        # 返回紧凑 JSON 文本。
        return json.dumps({"x": x_value, "y": 5}, ensure_ascii=False, separators=(",", ":"))

    def _create_ocr(self, det, ocr):
        """
        创建 ddddocr 识别器。

        :param det: 是否启用检测。
        :type det: bool
        :param ocr: 是否启用字符识别。
        :type ocr: bool
        :return: ddddocr 识别器或空值。
        :rtype: Any
        """

        try:
            # 导入 ddddocr 模块。
            import ddddocr

            # 返回 ddddocr 识别器。
            return ddddocr.DdddOcr(det=det, ocr=ocr, show_ad=False)

        except Exception as error:
            # 记录 OCR 初始化错误。
            self.last_cv2_error = str(error)

            # 返回兼容入口创建的识别器。
            return self._create_ocr_from_compat(det, ocr)

    def _create_ocr_from_compat(self, det, ocr):
        """
        通过兼容入口创建普通验证码识别器。

        :param det: 是否启用检测。
        :type det: bool
        :param ocr: 是否启用字符识别。
        :type ocr: bool
        :return: 验证码识别器或空值。
        :rtype: Any
        """

        try:
            # 导入模块加载工具。
            import importlib

            # 导入模块类型构造器。
            import types

            # 导入模块搜索路径对象。
            import sys

            # 导入路径处理对象。
            from pathlib import Path

            # 读取当前解释器中的站点包目录。
            site_paths = [Path(path) for path in sys.path if path]

            # 定位验证码库安装目录。
            package_paths = [path / "ddddocr" for path in site_paths if (path / "ddddocr").exists()]

            # 校验验证码库安装目录是否存在。
            if not package_paths:

                # 返回空值表示当前环境没有可用识别器。
                return None

            # 读取第一个匹配的验证码库安装目录。
            package_path = package_paths[0]

            # 构造临时包对象以避开入口文件冲突。
            package_module = types.ModuleType("ddddocr")

            # 写入临时包搜索路径。
            package_module.__path__ = [str(package_path)]

            # 写入临时包文件路径。
            package_module.__file__ = str(package_path / "__init__.py")

            # 注册临时包对象。
            sys.modules["ddddocr"] = package_module

            # 导入兼容识别入口。
            compat_module = importlib.import_module("ddddocr.compat.legacy")

            # 返回兼容入口创建的识别器。
            return compat_module.DdddOcr(det=det, ocr=ocr, show_ad=False)

        except Exception as error:
            # 记录兼容入口初始化错误。
            self.last_cv2_error = str(error)

            # 返回空值。
            return None
