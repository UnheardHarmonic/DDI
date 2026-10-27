# DDI V9.0 项目接力说明（2026-06-10 当前快照）

## 新对话启动方式

新对话建议先发送：

```text
请读取并使用 D:\skills\ddi-skill-router\SKILL.md
项目路径：D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0
另外读取项目接力说明：D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0\DDI_V9.0_项目接力说明_20260610_当前快照.md
```

长期规则仍以项目根目录的 `AGENTS.md` 和 `D:\skills\ddi-protocol-ddi\SKILL.md` 为准。

## 固定项目入口

- 项目根目录：`D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0`
- 主入口：`run_ddi.py`
- 平台适配器目录：`ddi_framework\platforms`
- 平台注册：`ddi_framework\platform_registry.py`
- 账号配置：`ddi_framework\account_config.py`
- 运行期开关：`account_runtime.json`

## 本轮最新完成事项

### 江苏澳洋医药物流有限公司

- 平台标识：`jsay`
- 账号：`jxsbt`
- 密码：`888`
- 登录页：`http://fr.aoyang.com/WebReport/decision/login`
- 系统类型：FineReport / FineDecision
- 适配器：`ddi_framework\platforms\jsay.py`
- 已注册：
  - `ddi_framework\__init__.py`
  - `ddi_framework\platform_registry.py`
  - `ddi_framework\account_config.py`
  - `account_runtime.json`

映射关系：

- 库存 = 库存
- 购进 = 购进流向
- 销售 = 配送流向

FineReport 关键协议：

- 登录页：`GET /WebReport/decision/login`
- 登录接口：`POST /WebReport/decision/login`
- 报表入口：`GET /WebReport/decision/v10/entry/access/10870e87-35d4-487b-8906-1a849438f19c`
- 参数提交：`POST /WebReport/decision/view/report?op=fr_dialog&cmd=parameters_d&sessionID=<sessionID>`
- Sheet 内容：`GET /WebReport/decision/view/report?...&op=fr_view&cmd=view_content&sessionID=<sessionID>&reportIndex=<0|1|2>`

FineDecision 登录要点：

- 登录页中的 `Dec.system` 使用 `JSON.parse(...)` 嵌套转义 JSON。
- `transmissionEncryption=2` 对应 AES，而不是 SM4。
- 密码加密方式：AES-ECB-PKCS7，密钥为 `frontSeed`。
- 本次前端密钥为 `uUOKCBMFIhWwWRjU`，但正式适配器会从登录页动态解析。
- 登录成功后必须写入 Cookie：
  - `fine_auth_token=<accessToken>`
  - `fine_remember_login=-1`
  - `tenantId=default`
- 后续请求同时带 `Authorization: Bearer <accessToken>`。

报表 Sheet 索引：

- `reportIndex=0`：库存
- `reportIndex=1`：购进
- `reportIndex=2`：销售

日期参数：

- 参数字段通过 `__parameters__` 表单字段提交。
- JSON 内容为：

```json
{"起始日期":"2026-05-01","结束日期":"2026-05-31","商品名称":""}
```

注意事项：

- 该报表页面提示单次最多查询三个月，适配器中按 90 天限制校验。
- FineReport 原生导出接口 `op=export&format=excel&extype=simple` 本轮测试返回的 Excel 不完整，只包含每个 Sheet 的第一列表头。
- 正式适配器没有使用浏览器自动化，当前采用协议登录、参数提交、`view_content` 读取 Sheet HTML、本地生成 Excel。
- 当前实现保留 FineReport Sheet 展示出来的全部字段，不做主观裁剪。
- 后续如果用户提供手工导出，需要重点核对字段数量和列名；如果手工导出字段更多，要继续追 FineReport 原生导出或底层数据接口。

验证命令：

```powershell
python -m py_compile "D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0\ddi_framework\platforms\jsay.py" "D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0\ddi_framework\__init__.py" "D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0\ddi_framework\platform_registry.py" "D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0\ddi_framework\account_config.py"
python -m json.tool "D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V9.0\config\account_runtime.json"
python -X utf8 run_ddi.py --company "江苏澳洋医药物流有限公司" --action query_excel --data-type 全部 --start-date 2026-05-01 --end-date 2026-05-31 --no-menu
```

验证结果：

- 登录成功。
- Cookie 保存成功。
- 购进流向：0 行，10 字段。
- 配送流向：3 行，13 字段。
- 库存：5 行，8 字段。
- 复制用配送流向 Excel 也已生成。

生成文件：

- `downloads\江苏澳洋医药物流有限公司26.5月购进流向.xlsx`
- `downloads\江苏澳洋医药物流有限公司26.5月配送流向.xlsx`
- `downloads\江苏澳洋医药物流有限公司26.5月配送流向_复制用.xlsx`
- `downloads\江苏澳洋医药物流有限公司26.6.10库存.xlsx`

抽查表头：

- 购进流向：`日期`、`购进单位`、`商品编号`、`商品名称`、`生产厂家`、`商品规格`、`数量`、`单价`、`金额`、`批号`
- 配送流向：`日期`、`销售单位`、`商品编号`、`商品名称`、`生产厂家`、`商品规格`、`数量`、`单价`、`金额`、`批号`、`单位识别`、`区域分类`、`销售员`
- 库存：`商品编号`、`商品名称`、`生产厂家`、`商品规格`、`数量`、`批号`、`生产日期`、`失效日期`

## 上一项待保留状态

### 江苏恒泰华洋医药有限公司

- 平台标识：`jshthy`
- 登录适配器已新增，RSA 登录链路此前已跑通过。
- 用户反馈抓包时错密码过多导致账号暂时封号。
- 当前已关闭：
  - `account_config.py` 中 `"启用": False`
  - `account_runtime.json` 中 `"江苏恒泰华洋医药有限公司": false`
- 后续等账号解封后再继续数据接口。

## 当前项目注意事项

- 新增平台必须继续同步：
  - `ddi_framework\__init__.py` 顶部模块索引注释
  - `ddi_framework\__init__.py` 导入
  - `ddi_framework\platform_registry.py`
  - `ddi_framework\account_config.py`
  - `account_runtime.json`
- 正式适配器必须协议优先，不遗留 Playwright、Selenium、按钮 ID、CSS selector 或页面导出点击。
- 每个数据类型查询必须打印 `PrintHandler.section(...)`，包含开始日期和结束日期。
- 库存文件名使用导出当天日期。
- 流向文件名使用查询开始日期所在月份。
- 默认保留接口或报表返回的全部原始字段，后续手工导出核对时优先修字段缺失。

## 下一轮建议

1. 如果用户继续做新商业，先读 `D:\skills\ddi-skill-router\SKILL.md` 和本接力文件。
2. 如果用户提供江苏澳洋手工导出，优先比对字段名和字段数；数量差异其次。
3. 如果江苏澳洋手工导出字段多于当前 DDI，继续追 FineReport 原生导出接口或报表底层数据源，不要把当前 `view_content` 解析结果当成最终不可变结论。
4. 如果继续江苏恒泰华洋，先确认账号是否解封，再从已存在的 `jshthy.py` 登录链路往数据接口抓包推进。


