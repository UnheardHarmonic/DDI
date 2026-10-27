# DDI V10.0 项目协作说明

## 项目定位

本项目是 DDI 协议直连导出工具，核心目标是在不依赖人工页面操作的前提下，为不同商业平台实现登录、查询、导出、标准命名、日志记录和复制用 Excel 生成。

## 固定工作目录

- 项目根目录：`D:\PycharmProjects\pythonProject\CodeX\DDI\DDI V10.0`
- 主入口：`run_ddi.py`
- 平台适配器目录：`ddi_framework\platforms`
- 平台注册：`ddi_framework\platform_registry.py`
- 账号配置：`ddi_framework\account_config.py`
- 公共日志库：`ddi_framework\print_handler.py`
- 下载命名工具：`ddi_framework\download_watcher.py`
- 公共任务协调：`ddi_framework\task_core.py`
- 公共单商业执行：`ddi_framework\task_execution.py`
- 公共任务运行时：`ddi_framework\task_runtime.py`

## 终端与 GUI 分层边界

- 平台适配器、商业配置、登录、查询、导出、Excel 落地、复制用 Excel、授权、任务调度、运行期启停和结构化日志属于公共业务层；新增 DDI、协议修复或数据类型扩展只能修改这一层。
- `run_ddi.py` 仅负责命令行参数、终端菜单、终端展示和退出码；`run_ddi_gui.py` 仅负责窗口、筛选、队列展示和事件消费。两个入口不得互相导入。
- 终端入口不得导入 CustomTkinter、GUI 队列或窗口类型；GUI 入口不得导入终端入口、终端菜单或终端展示函数。
- 公共层通过 `TaskRequest`、`TaskResult`、`TaskEvent` 和 `TaskEventSink` 向展示层提供接口；公共层不得认识控件、窗口、ANSI 像素画或终端菜单。
- 公共业务层是全部功能的唯一实现与事实来源。新增 DDI、协议修复、数据类型、导出规则或任务能力时，先扩展公共服务及无界面接口；若现有接口无法表达需求，应扩展请求、结果、事件或纯 Python 服务，而不是在任一入口实现专属业务分支。
- 终端版的可运行性是公共层变更的基线：终端不需要感知 GUI 的存在，也不得为了 GUI 运行而安装或调用 GUI 依赖。GUI 仅通过公共接口自动获得新能力，不得为同一商业重复维护登录、查询、导出、字段映射、Excel 或启停规则。
- 新商业和新数据类型必须由 `account_config.py`、平台注册与适配器声明驱动。GUI 的商业、平台、负责人、大区、省份和数据类型选项必须从公共配置动态读取，不得维护第二份平台或数据类型业务清单。
- 开发新 DDI 时默认只验证公共业务层及终端回归；只要公共任务接口保持不变，GUI 无需为该商业另写登录、查询、导出、字段映射或 Excel 代码。

## DDI 开发红线

- 正式 DDI 默认必须走协议请求，不允许把 Playwright、Selenium、坐标点击、按钮 ID 点击作为最终实现。
- 浏览器自动化只允许用于探针、抓包、确认页面运行态，不得遗留在正式平台适配器中。
- 如果短期必须浏览器兜底，必须在最终回复中明确标注为临时方案，并说明未达到纯协议标准。
- 任何新增平台必须接入 `PrintHandler` 公共日志，不得硬编码自造日志格式。
- 每个数据类型开始查询时必须打印 `section` 分隔线，包含开始日期和结束日期。
- 库存文件命名使用导出当天日期，不使用查询结束日期。
- 流向文件命名使用查询开始日期所在月份。
- 正式导出的 Excel 默认必须保留接口返回的全部原始字段；标准字段可以前置，但不得裁剪原始字段。
- PowerShell 环境中的中文路径、中文参数和中文 JSON key 按 UTF-8/Unicode 已知限制处理，不要反复使用会破坏中文的管道或 Bash heredoc 写法。

## 新平台标准流程

1. 阅读既有适配器，优先复用项目已有结构和工具。
2. 先识别平台类型：普通 JSON、WebForms、FineUI、DevExpress、活字格/Forguncy、HReport、KCShop 等。
3. 抓包时记录登录、查询、分页、导出、文件下载接口，不把 UI 控件名当作业务协议。
4. 查清全局日期参数真正进入协议的位置，不能只看页面输入框显示值。
5. 协议查询必须验证返回数据日期范围，确认不是平台默认范围。
6. 导出 Excel 时先输出标准字段，再追加接口返回的其他原始字段，保证手工导出字段核对时不丢字段。
7. 新增平台类后同步：
   - `ddi_framework\platforms\<platform>.py`
   - `ddi_framework\__init__.py` 的平台导入与顶部模块索引注释
   - `ddi_framework\platform_registry.py`
   - `ddi_framework\account_config.py`
   - `ddi_framework\startup_changelog.py` 当前版本日志中的“新增商业 DDI”独立条目；条目只能写商业全名，不得把商业名称混入通用功能条目或作为缩进子项，也不得追加平台、协议、数据类型或实现说明。
8. 运行 `python -m py_compile` 校验 touched Python 文件。
9. 运行单商业 `query_excel` 验证记录数、文件名、日志分隔线、Excel 内容和字段完整性。

## DDI 交付附加要求

- 每完成一家新的 DDI，最终回复中必须单独给出这家商业可直接执行的任务命令。
- 该命令默认使用 `python -X utf8 .\run_ddi.py` 形式，至少包含 `--company`、`--action query_excel`、`--data-type`、`--start-date`、`--end-date`、`--output-dir`、`--log-dir` 等关键参数。
- 如果该商业包含多个已接入数据类型，最终回复中默认优先给出一条可直接批量执行全部数据类型的命令，不再默认拆成购进流向、配送流向、库存三条；只有用户明确要求拆开时才分别提供。
- 如果本次 DDI 命中了相应本地 Skill，最终回复中必须明确说明本次实际使用了哪些 Skill。
- 如果项目中新增了新的专项 Skill，或当前商业明确依赖某个既有 Skill 才能高质量继续，必须同步更新本文档“本地可用 Skill”章节。
- 新增商业交付前必须检索当前版本启动日志中的商业全名，并确认其位于“新增商业 DDI”独立分组且条目只包含商业全名；仅出现在功能描述、提交说明或历史版本日志中均视为未完成同步。

## 版本继承与发布核对

本项目通常通过复制上一版本目录后继续迭代。复制完成后，必须把历史内容与当前运行标识分开处理，不能因目录复制而沿用错误的产品版本信息。

1. 先确定当前产品版本、项目目录名和发布文件名。
2. 核对并更新当前版本的控制台标题、启动更新日志当前版本选择、打包 spec 名称、打包说明、同事使用说明、项目接力说明和正式文档标题。
3. 搜索上一版本标识，逐项判断：历史 changelog、历史归档和历史说明必须保留；当前运行入口、当前打包名称和当前交付文档必须更新。
4. 授权协议版本、授权文件允许版本和产品发布版本是独立概念；只有授权规则同步变更且可重新签名授权文件时，才调整授权版本标识。
5. 打包前运行入口帮助、源码编译、打包后可执行文件帮助和运行目录检查；交付 onedir 包时必须交付整个分发目录，不得只发送 `.exe`。
6. 打包前后均扫描分发目录，排除运行日志、导出 Excel、下载文件、Cookie、浏览器会话、抓包材料、个人参考资料、私钥和本机授权文件；构建后验证产生的运行目录必须在交付前清理。
7. PyInstaller 只解决运行环境分发，归档和字节码仍可能被提取与反编译，不能作为源码保密方案。对源码保密要求较高时，采用原生编译或将关键逻辑迁出客户端，并将其视为提高逆向成本而非绝对防护。

## 文档与个人参考边界

- `docs` 只保存同事使用、发布和正式交付所需的文档。
- 个人学习笔记、逆向教程、抓包截图、调试过程和临时验证材料必须放在 `runtime\archive\personal_reference` 或任务期临时目录，不得进入 `docs` 或同事交付包。
- 打包配置只收集运行所需代码、配置和同事使用说明，不得把个人参考材料打入分发目录。

## 常见平台判断

- ASP.NET WebForms：关注 `__VIEWSTATE`、`__EVENTVALIDATION`、验证码、按钮字段和登录 Session。
- 活字格/Forguncy：关注 `Home/GetMetadata`、`Home/GetTableDataODataFormula`、`Home/GetTableDataWithOffset`、`Home/GiveParam`、`Home/ExportFile`。
- 活字格日期查询不要只写输入框，应写入 `queryCommandInfo.paramList` 中的日期参数。
- 活字格导出如果可用协议查询，应使用 `GetTableDataWithOffset` 本地生成 Excel，而不是点击 `导出EXCEL`。

## 本地可用 Skill

- DDI 总控路由：`D:\skills\ddi-skill-router\SKILL.md`
- DDI 协议开发：`D:\skills\ddi-protocol-ddi\SKILL.md`
- ASP.NET WebForms：`D:\skills\aspnet-webforms-ddi\SKILL.md`
- PowerShell 中文 UTF-8：`D:\skills\powershell-utf8-chinese\SKILL.md`
- Web 协议恢复：`D:\skills\web-protocol-recovery\SKILL.md`
- 浏览器 hook 观察：`D:\skills\browser-hook-snippets\SKILL.md`
- JS 沙箱补环境：`D:\skills\env-patch\SKILL.md`
- JavaScript AST 解混淆：`D:\skills\ast-deobfuscate\SKILL.md`
- 瑞数轻量骨架：`D:\skills\rs-reverse\SKILL.md`
- 瑞数 iv8 回放：`D:\skills\iv8-ruishu-reverse\SKILL.md`
- 微信小程序逆向：`D:\skills\wechat-miniapp-reverse\SKILL.md`
- 滑块验证码链路分析：`D:\skills\captcha-slide-reverse\SKILL.md`
- 桌面玻璃 GUI：`C:\Users\Admin\.codex\skills\glass-desktop-gui\SKILL.md`

使用方式：在新对话框中明确说明“请读取并使用 `D:\skills\ddi-skill-router\SKILL.md`”，由总控路由决定本次任务需要继续加载哪些子 Skill，不要默认全局调用。

## 代码风格约束

- 函数、类、方法、模块级注释使用 Sphinx/reStructuredText 风格。
- 新增 Python 业务代码按项目已有注释密度和排版风格书写。
- 注释只解释业务逻辑、数据流向和代码行为，不写补丁过程、AI 身份或“修复痕迹”。
- 不回滚用户或其他对话框已经产生的无关修改。


