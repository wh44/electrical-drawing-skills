# 电气工程识图与新图册接入 Skill

将图册清点、预检、查线、回路动作解释和证据核对组织成可复用的 Codex Skill。安装入口：`skills/electrical-drawing-reader`。批量解析建库还需要另外提供 `PDF_Vetor_Parser` 引擎；本仓库不携带工程原图或历史数据库。后续需要更方便的安装和发现时，可再封装成插件。[官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)、[插件打包文档](https://developers.openai.com/plugins/build/plugins)。

本包是可本地使用的 Skill 源码包，不是已发布的插件。

## 取得分享包后能做什么

| 层次 | 接收者取得什么 | 还需要什么 |
| --- | --- | --- |
| 原图问答 | 图册范围、触点状态、动作链及证据核对流程 | 能使用 Skill 和读取图像/PDF 的 Codex 环境，以及自己的图纸 |
| 结构预检/文字定位 | 两个辅助 Python 脚本 | Python、PyMuPDF 和自己的 PDF |
| 批量解析与建库 | 调用步骤、样本核对及适配方法 | 另行取得 `PDF_Vetor_Parser` 工程，安装其 `requirements.txt`，确认新模板兼容 |

引擎源码不包含在这个 Skill 分享包中。提供引擎时，在仓库说明其获取地址、版本或提交标识，以及依赖安装方式；接收者以本机实际路径传入 `--project-root`。本包不会自动下载引擎。

工程图纸、历史数据库、现场照片和运行目录各自管理。本分享包的回路示例为人为构造的通用例子，不携带当前工程的原图或接线数据。

## 推荐的仓库结构

```text
electrical-drawing-skills/
├── README.md
├── GROUP_MEETING.md
├── requirements-preflight.txt
└── skills/
    └── electrical-drawing-reader/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── references/
        └── scripts/
```

上传时使用这个整理后的包作为仓库内容。后续可按 `v0.1.0` 等标签记录发布版本，并在 README 中同步对应的引擎版本和实际验证范围。仓库是否公开按团队的共享范围决定；组内试用可以使用私有仓库。

## 接收者的安装方式

### 方式一：从 GitHub 安装

在 Codex 中输入下面的安装请求：

```text
使用 $skill-installer 安装这个 Skill：
https://github.com/wh44/electrical-drawing-skills/tree/main/skills/electrical-drawing-reader
```

官方文档支持从其他仓库安装 Skill。确认安装后，在下一次消息中调用；若技能列表未显示，重启 Codex。[官方说明](https://learn.chatgpt.com/docs/build-skills)。

### 方式二：直接复制完整文件夹

接收者也可以解压分享包，将 `skills/electrical-drawing-reader` 整个文件夹复制到本机支持的 Skill 搜索目录。当前官方文档列出的目录包括：

- 仅当前工程使用：工程中的 `.agents/skills/electrical-drawing-reader/`。
- 当前用户跨工程使用：用户主目录中的 `.agents/skills/electrical-drawing-reader/`。

不要只复制 `SKILL.md`，它引用同目录下的工具和资料。某些现有安装仍通过 `~/.codex/skills` 管理本地技能；以接收者当前产品和安装器实际使用的目录为准，不要在多个搜索路径重复安装同名技能。[搜索目录说明](https://learn.chatgpt.com/docs/build-skills)。

## 安装后的第一次使用

在包含自己图纸的工程中发出：

```text
使用 $electrical-drawing-reader 帮我快速上手这份图纸：这里填写 PDF 路径。
先确认文件版本、柜体和图页范围，给出图册导航及支持情况。
若需要批量建库，再用新输出目录试解析并核对原图。
PDF_Vetor_Parser 工程路径：这里填写本机引擎路径；没有引擎时先完成原图阅读和预检。
```

运行辅助脚本前，在选定 Python 环境安装 `requirements-preflight.txt`，或直接使用已安装 PyMuPDF 的环境：

```text
python -m pip install -r requirements-preflight.txt
```

下面的 `SKILL_ROOT`、`PDF`、`OUTPUT` 和 `PROJECT_ROOT` 均为需替换的路径，不是环境变量展开语法：

```text
python SKILL_ROOT/scripts/inspect_drawing.py PDF --pages 1-3 --out OUTPUT
python SKILL_ROOT/scripts/index_pdf.py PDF --find 目标位号
```

需要标题栏/图种/柜体规则时，在预检命令中增加 `--project-root PROJECT_ROOT`。输出路径必须是新目录/新文件，不能指向旧库；实际调用以 Skill 的运行参考为准。

## 复用成功应检查什么

先确认 Skill 被加载、工具在选定 Python 下能运行、图纸和柜体范围一致、代表页可读且来源可追溯。需要建库时，再核对同组 S/T/W 样本和接入记录。安装成功、预检完成和识图准确率是不同的验证对象；不以安装或脚本通过替代新图样本核对。

## 后续扩展为插件

需要面向更多人分发时，可以在 Skill 外增加插件清单和安装元数据，按官方插件打包流程维护。Skill 源码仍保存在 `skills/electrical-drawing-reader/`，GitHub 仓库继续承担版本管理。[官方插件打包说明](https://developers.openai.com/plugins/build/plugins)。

本地依赖也要在说明中明确：插件分发本身不会给每位使用者自动部署解析引擎。若未来希望使用者无需本地引擎，可另行设计托管解析服务及相应工具接口，这属于后续开发。
