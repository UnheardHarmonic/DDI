# DDI V14.0 项目协作说明

## 项目定位

本项目是 DDI 协议直连导出工具，核心目标是在不依赖人工页面操作的前提下，为不同商业平台实现登录、查询、导出、标准命名、日志记录和复制用 Excel 生成。

## 固定工作目录

- 项目根目录：`D:\PycharmProjects\pythonProject\King_Code\DDI\DDI V14.0`
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
- 正式原始 Excel 的列字段标题、列字段顺序和全部原始字段必须与当前商业页面或接口返回的真实列定义完全一致；不得将标准字段前置、改名、增加前缀、重排或套用其他商业的字段定义。标准字段只能写入独立的复制用 Excel，不得改变正式原始 Excel。
- PowerShell 环境中的中文路径、中文参数和中文 JSON key 按 UTF-8/Unicode 已知限制处理，不要反复使用会破坏中文的管道或 Bash heredoc 写法。

## 共享平台基类与商业字段隔离

- 相同平台可以复用登录、请求签名、会话、分页、重试、页面解析框架、文件命名和 Excel 写入等通用能力；不得因为复用基类而继承另一家商业的原始列标题、列顺序、字段别名、数组槽位或标准字段映射。
- 每家商业、每个数据类型必须从自身页面表头、接口列元数据或手工导出中取得原始字段契约，并以当前商业实际返回的标题列表及顺序作为正式原始 Excel 的唯一来源。平台级默认字段只能用于协议结构识别，不能作为正式表头回退值。
- 内部解析需要去重键、规范化键或索引键时，必须与原始表头序列分离保存；写入正式原始 Excel 时仍按原始标题文本和原始位置输出，重复标题也不得以追加序号、改名或合并的方式改变展示结果。
- 分页、不同样本或不同报表页签出现原始字段标题或顺序不一致时，必须记录差异并停止交付或明确处理规则；不得静默沿用首家商业、首个样本或基类中的静态字段列表。
- 标准字段别名和商业字段映射只服务于独立的复制用 Excel。新商业与已有商业共用平台时，映射配置必须按商业名称和数据类型隔离，不能把一家的字段别名提升为另一家正式原始导出的默认定义。
- 有手工导出或页面表头证据时，验收必须逐列比较标题文本、列数和列顺序；仅比较字段集合或字段数量不视为通过。

## 新平台标准流程

1. 阅读既有适配器，优先复用项目已有结构和工具。
2. 先识别平台类型：普通 JSON、WebForms、FineUI、DevExpress、活字格/Forguncy、HReport、KCShop 等。
3. 抓包时记录登录、查询、分页、导出、文件下载接口，不把 UI 控件名当作业务协议。
4. 查清全局日期参数真正进入协议的位置，不能只看页面输入框显示值。
5. 协议查询必须验证返回数据日期范围，确认不是平台默认范围。
6. 先取得当前商业、当前数据类型的页面或接口原始表头，并记录标题文本、列数和列顺序；不得用同平台其他商业的静态表头、字段别名或数组槽位替代。
7. 正式原始 Excel 直接按当前商业原始表头及顺序输出全部原始字段；如需标准字段，另行生成复制用 Excel。
8. 新增平台类后同步：
   - `ddi_framework\platforms\<platform>.py`
   - `ddi_framework\__init__.py` 的平台导入与顶部模块索引注释
   - `ddi_framework\platform_registry.py`
   - `ddi_framework\account_config.py`
   - `ddi_framework\startup_changelog.py` 当前版本日志中的“新增商业 DDI”独立条目；条目只能写商业全名，不得把商业名称混入通用功能条目或作为缩进子项，也不得追加平台、协议、数据类型或实现说明。
9. 运行 `python -m py_compile` 校验 touched Python 文件。
10. 运行单商业 `query_excel` 验证记录数、文件名、日志分隔线、Excel 内容、原始字段标题和原始列顺序；有手工导出时逐列核对。

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

## 打包发布规则（固定执行，无需用户重复说明）

项目有两种固定分发形态，构建与验证按本节执行。

### 形态一：onedir 标准版（默认，交付同事使用）

- 构建配置：`packaging\DDI_V14.0.spec` + `packaging\DDI_V14.0_GUI.spec`。
- 构建命令：`powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1`。
- 产物：`dist\DDI_V14.0\` 整个目录（终端 exe + GUI exe + `_cli_internal` + `_internal` + `config` + `COLLEAGUE_GUIDE.md`），交付必须给整个目录。

### 形态二：单文件版（用户自用携带）

- 构建配置：`packaging\DDI_V14.0_onefile.spec` + `packaging\DDI_V14.0_GUI_onefile.spec`。
- 构建命令（两条分别执行）：
  - `python -m PyInstaller packaging\DDI_V14.0_onefile.spec --noconfirm --clean --distpath dist_onefile --workpath runtime\archive\generated\build\onefile_cli`
  - `python -m PyInstaller packaging\DDI_V14.0_GUI_onefile.spec --noconfirm --clean --distpath dist_onefile --workpath runtime\archive\generated\build\onefile_gui`
- 产物：`dist\DDI_V14.0_单文件版\` 内只有 `DDI_V14.0.exe` 与 `DDI_V14.0_GUI.exe` 两个文件。
- 单文件版特性：每次启动自解压约 10 秒属正常现象；配置、授权、运行产物从 exe 所在目录读取，`license.json` 放 exe 旁 `config\` 内即可生效。

### 全量账密内嵌策略（2026-10-09 明令，固定执行）

- 四个 spec 均已把 `ddi_framework\account_config_local.py` 内嵌为运行资源：打包环境优先读取 exe 旁的覆盖文件，不存在时读取内嵌全量账密，同事无需自行配置账号。
- `account_config.py` 的 frozen 路径逻辑承载该策略：exe 旁存在 `account_config_local.py` 时整体覆盖内嵌版本；修改读取逻辑必须同步验证两种形态。
- `license_tool.py`、`ddi_license_private_key.pem`、`ddi_license_public_key.pem` 是维护者专属签发材料，永不入包；三者无任何代码引用，构建后扫描确认。

### 两种形态共同的固定规则

- spec 的 `excludes` 必须包含 `torch`、`torchvision`、`tensorboard`、`huggingface_hub`：这些是被依赖分析误收集的大体积无关依赖（约 366MB×2），DDI 代码与验证码识别链路（ddddocr/onnxruntime）完全不使用。
- 构建前置验证：`run_ddi.py --help`、全部源码 `python -m py_compile`、`python -X utf8 -m unittest discover -s tests -p "test_*.py"` 全绿。
- 构建后验证：终端 exe `--help` 实跑；GUI exe 拉起进程确认存活即可；运行 exe 会在分发目录触发目录自愈（生成 runtime 树和 `===== 说明 =====.md` 空壳目录），交付前必须删除这些运行副产物，只保留产品文件。
- 构建后体积与排除项核对：分发目录 1.8G 上下为正常体量；必须实测确认 `torch`/`torchvision`/`tensorboard`/`huggingface_hub` 零命中（约 730M 无关依赖，V14.0 发布时曾发现 onedir 双 spec 的 excludes 为空数组导致漏排，与 onefile spec 漂移，发布前逐 spec 核对）。
- 分发目录红线扫描：不得包含导出 Excel、运行日志、Cookie、`license.json`、`license_tool.py`、私钥与公钥（`.pem`）、抓包材料和个人参考材料；`account_config_local.py` 按全量账密内嵌策略允许存在于构建配置与运行时资源中；`certifi` 的 CA 证书属运行必需，不算违规。
- 版本升级时必须同步重命名四个 spec 文件并更新其内部 `name` 字段、`build_release.ps1` 路径、本节文件名和 `packaging\README.md`。
- 构建日志写入 `runtime\work\validation`，验证完成后随其他可再生材料一并清理。

## 文档与个人参考边界

- `docs` 只保存同事使用、发布和正式交付所需的文档。
- 个人学习笔记、逆向教程、抓包截图、调试过程和临时验证材料必须放在 `runtime\archive\personal_reference` 或任务期临时目录，不得进入 `docs` 或同事交付包。
- 打包配置只收集运行所需代码、配置和同事使用说明，不得把个人参考材料打入分发目录。

## 国控安徽导出链路改造计划

国控安徽信息服务平台（gykgah）的登录与会话已协议直连，Excel 导出环节当前依赖受控浏览器会话点击页面导出按钮，账号配置已显式声明「临时浏览器兜底」。
协议化路线：对 FineUI 导出请求做协议还原（参考本工程 fjjztzh 的 FineUI __FSTATE 直连实现），以 GetTableDataWithOffset 类接口加本地 Excel 生成替换浏览器导出；完成后移除兜底声明与浏览器链路。


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



## 多设备同步纪律（GitHub 唯一接入点）

- 本项目唯一远程仓库：GitHub 私有仓库 UnheardHarmonic/DDI（master 分支，2026-10-16 由废仓 shybyf-ddi-releases 改名承接，旧 SHYBYF 历史已按董事长口径清退）。
- 换设备或收工前 push，开工前 pull；接手他机产出先核对最新提交与启动更新日志的版本现状。
- 零凭据入库铁律：`account_config_local.py`（真实账号密码）、`config/license.json`、`config/account_runtime.json`、`runtime/`、`dist/`、`.venv/` 一律由 .gitignore 排除，推送前必须复扫历史与暂存区零泄漏。
- 本机远程地址内嵌按仓隔离的细粒度令牌（与公司仓同一管理口径）；令牌轮换时同步更新 remote URL 与记忆台账。
