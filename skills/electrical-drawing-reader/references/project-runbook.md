# 本项目运行与新模板适配

## 环境与定位

按任务读取当前工程的 README、相关入口和 `--help`，以下是整理时已确认的接口。原图问答无需加载解析工程；运行建库时才定位引擎、检查依赖。Skill 可全局安装，解析引擎仍来自用户提供的工程；路径变化后重新定位，不下载或假设存在另一份引擎。

```powershell
Set-Location 'D:\project\PDF_Vetor_Parser'
python -c "import sys,pymupdf,yaml,networkx,PIL; print(sys.executable); print(pymupdf.VersionBind)"
python main.py --help
python qa_cli.py --help
```

若默认 Python 缺少依赖，先检查已有环境。项目 README 中的 `conda activate circuit_pdf` 是历史环境示例。确需安装时，在选定环境按 `requirements.txt` 安装；照片识字才涉及 `requirements-photo.txt` 和额外模型。不要为普通矢量图解析安装照片 OCR。

## 预检与选页

预检完整图册可生成页码索引；先试运行时用 `--pages` 限定范围。以下页码仅演示参数语法，必须替换为新清单的实际页面：

```powershell
$SkillBase = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex\skills' }
$SkillRoot = Join-Path $SkillBase 'electrical-drawing-reader'
$Pdf = 'D:\drawings\新图册.pdf'
python -X utf8 "$SkillRoot\scripts\inspect_drawing.py" "$Pdf" --project-root "$PWD" --pages '1-3,12,30,41' --preview-pages '12,30,41' --out 'outputs\新图册预检样本'
```

`$SkillRoot` 取实际加载的 Skill 文件夹；上例使用个人安装位置，若使用项目内副本则显式改为该目录。预检目录包含 `inventory.json`、`inventory.csv` 和按需生成的 `page_NNNN.png`。输出目录必须不存在，避免混合两次结果。脚本不写数据库，不更新 `knowledge`。没有 `--project-root` 时只做 PDF 结构检查，图号/图种/柜体保持未知。`--project-root` 需指向信任的本地工程，因为会导入其 Python 模块。

检查目录/图例、各模板的代表页与同组关联页。尺寸或旋转异常、图号缺失、`OTHER`、图片覆盖、无线段等信号都需要看原图，不能单靠文本数量判定支持。

### 只定位设备文字或解释原图

无需预检全册或先建库。可用独立文字索引脚本定位候选页：

```powershell
python -X utf8 "$SkillRoot\scripts\index_pdf.py" "$Pdf" --pages '12,18-20' --find 'BGB1' --find 'MBO1'
python -X utf8 "$SkillRoot\scripts\index_pdf.py" "$Pdf" --out 'outputs\新图册_版本1_文字索引.jsonl'
```

页码和位号是参数语法示例；按当前图册替换。该脚本不导入解析引擎，只依赖 PyMuPDF，输出源文件 SHA256、PDF 页序号、PDF 页面标签、尺寸及文字。`pdf_label` 是 PDF 自身的页面标签，不能当成已核对的 Sheet。`--find` 多次出现按 OR 做忽略大小写的子串检索，不证明完整位号匹配或连接。

`--out` 必须是尚不存在的文件。无文字页会留下空文本记录；不能把未命中解释为没有设备。定位后仍查看原图及设备表，触点/机械虚线/接点的判读按 [动作解释](circuit-explanation.md) 执行。

无引擎时，可省略预检脚本的 `--project-root` 完成结构清点；需要批量电气拓扑时再补引擎。Windows 与 WSL 的解释器及路径分别确认：例如 Windows 的 D 盘路径在 WSL 通常映射到 `/mnt/d`；不要把两套路径拼进同一命令。大图册在挂载盘上反复读取可能较慢，先限制代表页，避免为一个位号全册提取几何。

## 试解析与查询

下列 `$Pages` 为语法示例；确认新图的 S/T/W 映射后再执行。每次用全新 `$Out`：**`main.run_pipeline` 会删除该输出目录已有的 topology.sqlite。** 不要指向旧快照或线上数据。

```powershell
$Pages = '12,30,41-42'
$Out = 'outputs\新图册_版本1_试解析'
if (Test-Path -LiteralPath $Out) { throw '输出目录已存在，请另选新目录' }
python main.py "$Pdf" --pages "$Pages" --out "$Out" --visualize
```

实际输出：`nodes.json`、`raw_connections.json`、`connections.json`、`conflicts.json`、`summary.json`、`topology.sqlite`、`visualizations/`。S 页可生成对象/候选拓扑/证据图，其他电气页按现有内容生成对象和证据图；全局 SVG 默认有节点数上限，不能据其省略内容判断数据库无连接。

- `--viz-scale 2.0` 控制渲染；`--viz-min-anchors 1` 保留只有一个锚点的候选图。
- 功能区默认开启；诊断成员归属用 `--debug-functional-regions`。若任务只需基础拓扑可用 `--skip-functional-regions`，在交付中注明跳过。功能区失效也必须报告，不能靠静默跳过声称完整成功。
- CLI 没有柜体适配、置信阈值或检查点参数；不要编造 `--cabinet`、`--confidence`、`--checkpoint-dir`。配置来自 `config.AppConfig`；`run_pipeline` 的 Python 接口才接受 `checkpoint_dir`。图纸库建库管理检查点。

查询示例中的位号也必须来自新数据库：

```powershell
python qa_cli.py 'X20:17接到哪里？' --db "$Out\topology.sqlite" --pdf "$Pdf" --out "$Out\qa"
python qa_cli.py 'X20:17到X20:30的回路路径怎么走？' --db "$Out\topology.sqlite" --pdf "$Pdf" --out "$Out\qa"
```

`--include-candidate` 只用于有说明的候选排查，默认不要开启。问答 CLI 没有柜体筛选参数；同名位号用工作台分组筛选、对象 ID 和原图来源消歧，不能直接取第一条。`--json` 可查看完整结果。`--save-json` 在生成图片时会把指定文件名保存到查询图片目录，未生成图片时保存到 `--out`，应以实际路径为准。

需要工作台时在用户要求启动的范围内执行：

```powershell
python demo.py --db "$Out\topology.sqlite" --pdf "$Pdf" --out "$Out\query_cache" --library "$Out\library" --port 8893
```

先确认端口空闲，使用本机 `127.0.0.1`。`--out` 是查询缓存，`--library` 是持久图纸库；独立服务不能共用图纸库目录。多 PDF 时必须显式指定 `--pdf`。建库结果不自动发布。上传/复核/版本管理细节以工程 `README_BUSINESS.md` 为准。

## 新厂家/新布局的适配地图

先确认是漏选关联页、输入不受支持还是规则不适配，再确定是否需要改代码。

| 现象 | 优先检查位置 | 需要保留的边界 |
| --- | --- | --- |
| 标题栏存在但图号/Sheet 为空 | `parser/pdf_vector_parser.py` 的 `parse_metadata`、`DRAWING_RE`、`SHEET_RE` | 标题栏优先，正文跨引图号不能抢占；多个不明候选保持未知 |
| S/T/W 页成为 OTHER | `parser/page_classifier.py` | 新后缀/标题词需从实际图纸确认；非电气页不强制分类 |
| 新图号被逐页隔离 | `core/drawing_scope.py`、`core/ids.py` | 当前匹配 `A数字…-柜型-S/T/W`；需一起检查 ID 与互证规则，不能仅改名称或取消隔离 |
| T 图端子漏识别/串列 | `parser/terminal_table_parser.py` | 当前端子数字行约为页高 45%–58%、编号 1–250，属于现模板假设；新方向/多行布局需抽样校准 |
| W 图漏设备或引脚挂错设备 | `parser/wiring_parser.py`、`knowledge/component_types.yaml` | 核对同列、最近上方标题及跨栏边界；长表底部也要抽查 |
| 位号分词、接口层级或点号异常 | `normalization/`、`parser/schematic_parser.py` | 保留原文与 bbox；设备接点与端子分开建模 |
| 导线漏并/误并、锚点偏移 | `topology/wire_detector.py`、`candidate_net_builder.py`、`pin_binder.py`、`config.py` | 当前距离单位是 PDF 坐标；缩放/DPI 不直接等于模型坐标；先检查几何再调容差 |
| 器件类型/端子语义不同 | `knowledge/component_types.yaml`、`pin_rules.yaml`、`symbol_rules.yaml` | 新规则需当前图例、设备资料或人工样本，不把常见编号当成所有厂家统一事实 |
| 功能区未找到或归属不明 | `parser/functional_region_parser.py`、`service/functional_membership_service.py` | 语义层不新增导通关系，公共母线可跨多个区 |

`knowledge/drawing_page_catalogue.json` 绑定旧源文件 SHA256，新版本即使页数相同也不能复用整册映射；`drawing_group_profiles.json` 只是页码定位线索，必须核对本次标题栏。预检输出不能直接覆盖这两个文件：它不含完整的人工核对与功能标题信息。

本项目现有 ABB 黄金用例只用于原图回归：`tests/test_known_cases.py` 中的 S54/T79/W98 与标签断言不能变成新图的验收标准。使用 `ABB_PDF_PATH` 时必须指向原 ABB 样本；不要为了测试通过而改断言套用新图纸。
