# -*- coding: utf-8 -*-
"""
DDI 通用逆向能力库。

本模块封装各平台协议逆向过程中可复用的算法、编码、摘要和参数生成能力。
"""

# 导入哈希摘要模块。
import hashlib

# 导入 Base64 编解码模块。
import base64


# 定义 MD5 十六进制摘要函数。
def md5_hex(text, encoding="utf-8"):

    """
    计算文本的 MD5 十六进制摘要。

    :param text: 待摘要文本。
    :type text: str
    :param encoding: 文本编码。
    :type encoding: str
    :return: MD5 十六进制摘要。
    :rtype: str
    """

    # 将输入文本转换为字符串。
    plain_text = str(text)

    # 按指定编码转换为字节。
    plain_bytes = plain_text.encode(encoding)

    # 计算并返回 MD5 十六进制摘要。
    return hashlib.md5(plain_bytes).hexdigest()


# 定义 SHA256 十六进制摘要函数。
def sha256_hex(text, encoding="utf-8"):

    """
    计算文本的 SHA256 十六进制摘要。

    :param text: 待摘要文本。
    :type text: str
    :param encoding: 文本编码。
    :type encoding: str
    :return: SHA256 十六进制摘要。
    :rtype: str
    """

    # 将输入文本转换为字符串。
    plain_text = str(text)

    # 按指定编码转换为字节。
    plain_bytes = plain_text.encode(encoding)

    # 计算并返回 SHA256 十六进制摘要。
    return hashlib.sha256(plain_bytes).hexdigest()


# 定义 AES-CBC-PKCS7-Base64 加密函数。
def aes_cbc_pkcs7_base64(plain_text, secret_key, iv_text, encoding="utf-8"):

    """
    使用 AES-CBC-PKCS7 加密文本并返回 Base64 密文。

    :param plain_text: 待加密明文。
    :type plain_text: str
    :param secret_key: AES 密钥文本。
    :type secret_key: str
    :param iv_text: AES 初始向量文本。
    :type iv_text: str
    :param encoding: 文本编码。
    :type encoding: str
    :return: Base64 编码密文。
    :rtype: str
    """

    # 导入 AES 算法对象。
    from cryptography.hazmat.primitives.ciphers import Cipher

    # 导入 AES 算法配置。
    from cryptography.hazmat.primitives.ciphers import algorithms

    # 导入 CBC 分组模式配置。
    from cryptography.hazmat.primitives.ciphers import modes

    # 导入 PKCS7 填充对象。
    from cryptography.hazmat.primitives import padding

    # 将明文转换为字节。
    plain_bytes = str(plain_text).encode(encoding)

    # 将密钥转换为字节。
    key_bytes = str(secret_key).encode(encoding)

    # 将初始向量转换为字节。
    iv_bytes = str(iv_text).encode(encoding)

    # 创建 PKCS7 填充器。
    padder = padding.PKCS7(algorithms.AES.block_size).padder()

    # 填充明文字节。
    padded_bytes = padder.update(plain_bytes) + padder.finalize()

    # 创建 AES-CBC 加密器。
    encryptor = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes)).encryptor()

    # 生成密文字节。
    cipher_bytes = encryptor.update(padded_bytes) + encryptor.finalize()

    # 返回 Base64 编码密文。
    return base64.b64encode(cipher_bytes).decode("ascii")


# 定义 3DES-CBC-PKCS7-Base64 加密函数。
def triple_des_cbc_pkcs7_base64(plain_text, secret_key, iv_text, encoding="utf-8"):

    """
    使用 3DES-CBC-PKCS7 加密文本并返回 Base64 密文。

    :param plain_text: 待加密明文。
    :type plain_text: str
    :param secret_key: 3DES 密钥文本。
    :type secret_key: str
    :param iv_text: 3DES 初始向量文本。
    :type iv_text: str
    :param encoding: 文本编码。
    :type encoding: str
    :return: Base64 编码密文。
    :rtype: str
    """

    # 导入分组密码对象。
    from cryptography.hazmat.primitives.ciphers import Cipher

    # 导入 CBC 分组模式配置。
    from cryptography.hazmat.primitives.ciphers import modes

    # 导入 PKCS7 填充对象。
    from cryptography.hazmat.primitives import padding

    # 导入 3DES 算法对象。
    try:

        # 读取新版 cryptography 的 3DES 算法对象。
        from cryptography.hazmat.decrepit.ciphers import algorithms

    except ImportError:

        # 读取旧版 cryptography 的 3DES 算法对象。
        from cryptography.hazmat.primitives.ciphers import algorithms

    # 将明文转换为字节。
    plain_bytes = str(plain_text).encode(encoding)

    # 将密钥转换为 3DES 使用的 24 字节密钥。
    key_bytes = str(secret_key).encode(encoding)[:24]

    # 将初始向量转换为字节。
    iv_bytes = str(iv_text).encode(encoding)

    # 创建 PKCS7 填充器。
    padder = padding.PKCS7(64).padder()

    # 填充明文字节。
    padded_bytes = padder.update(plain_bytes) + padder.finalize()

    # 创建 3DES-CBC 加密器。
    encryptor = Cipher(algorithms.TripleDES(key_bytes), modes.CBC(iv_bytes)).encryptor()

    # 生成密文字节。
    cipher_bytes = encryptor.update(padded_bytes) + encryptor.finalize()

    # 返回 Base64 编码密文。
    return base64.b64encode(cipher_bytes).decode("ascii")
