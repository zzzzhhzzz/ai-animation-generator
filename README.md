# 多 Agent 动画自动生成系统

一个基于多 Agent 协作的自动化动画视频生成系统。使用不同难度的 LLM 来完成不同复杂度的任务。

## 功能特点

- 🤖 **多 Agent 协作** - 图片理解、脚本编写、分镜编写、代码生成、音频制作、审核
- 🧠 **智能 LLM 选择** - 根据任务难度选择合适的 LLM
- 🎬 **完整流程** - 从需求到视频的端到端自动化
- ✅ **质量保证** - 内置 Schema 验证和自动修复机制
- 🔄 **自动重试** - 验证失败自动修复并重试

## 系统架构

```
用户需求
    │
    ▼
┌─────────────────────┐
│  Orchestrator      │ ← 协调器（理解需求，调度 Agent）
└─────────────────────┘
    │
    ├──▶ Image Analyzer ─▶ Script Writer ─▶ Storyboard Writer
    │     (图片理解)       (脚本编写)       (分镜编写)
    │
    ├──▶ Code Generator ─▶ Audio Producer
    │     (代码生成)       (音频制作)
    │
    └──▶ Reviewer
          (审核)
```

## 环境要求

- Python 3.8 或更高版本
- API 密钥（OpenAI 或 Anthropic）

## 安装步骤

### 1. 克隆项目

```bash
cd /Users/mac/skills/tutor
```

### 2. 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API 密钥

**方式一：环境变量（推荐）**

```bash
# OpenAI
export OPENAI_API_KEY="你的OpenAI密钥"
# Windows PowerShell:
$env:OPENAI_API_KEY="你的OpenAI密钥"

# Anthropic
export ANTHROPIC_API_KEY="你的Anthropic密钥"
# Windows PowerShell:
$env:ANTHROPIC_API_KEY="你的Anthropic密钥"
```

**方式二：修改代码**

编辑 `llm/factory.py`，找到 `OpenAILLM` 或 `AnthropicLLM` 类，直接填入你的 API 密钥。

## 使用方法

### 命令行使用

```bash
# 基本用法
python main.py "帮我制作一个讲解勾股定理的教学视频"

# 指定输出目录
python main.py "制作一个数学教学视频" -o my_video

# 简化模式（跳过脚本步骤，更快）
python main.py "制作一个科普视频" --mode simple

# 带图片需求
python main.py --image path/to/problem.png "分析这个题目"

# 使用 Anthropic 模型
python main.py "制作视频" --provider anthropic
```

### 运行模式

| 模式 | 说明 |
|------|------|
| `full` | 完整流程：图片分析 → 脚本 → 分镜 → 音频 → 代码 |
| `simple` | 简化流程：直接需求 → 分镜 → 音频 → 代码 |
| `storyboard_only` | 仅生成分镜 |

### Python 代码中使用

```python
from agents import Orchestrator

# 创建协调器
orchestrator = Orchestrator(provider="openai")

# 运行工作流程
result = orchestrator.run(
    requirement="帮我制作一个勾股定理讲解视频",
    image_path="problem.png",  # 可选
    mode="full",
    output_dir="output"
)

if result["success"]:
    print(f"生成完成!")
    print(f"分镜文件: {result['storyboard_path']}")
    print(f"代码文件: {result['code_path']}")
    print(f"音频目录: {result['audio_dir']}")
else:
    print(f"生成失败: {result['error']}")
```

## 输出结果

运行完成后，在输出目录中你会看到：

```
output/
├── storyboard.md    # 分镜脚本（可以用文本编辑器查看）
├── script.py        # Manim 动画代码
└── audio/           # 生成的音频文件
    ├── audio_001_开场.wav
    ├── audio_002_讲解.wav
    └── ...
```

## 生成视频

生成分镜和代码后，使用 Manim 生成视频：

```bash
cd output
manim -pql script.py SceneName
```

参数说明：
- `-pql`：低质量预览（快速生成）
- `-pqh`：高质量输出（较慢）
- `-pl`：中等质量

更多 Manim 使用方法请参考 [Manim 官方文档](https://docs.manim.org.cn/)

## 质量保证机制

本系统内置了多层质量保证，确保生成内容的可靠性：

### 1. Schema 验证
每个 Agent 输出都会验证格式是否正确：
- **脚本验证**：检查标题、类型、内容结构
- **分镜验证**：检查字幕长度、读白长度、幕号连续性
- **代码验证**：检查 Python 语法、manim 导入、Scene 类

### 2. 自动重试
验证失败会自动修复并重试：
- 最多重试 3 次
- 自动生成修复提示
- 每次重试增加"严格模式"提示

### 3. 业务规则检查
- 字幕 ≤ 20 字
- 读白 ≥ 5 字
- 幕号从 1 开始连续
- 代码语法正确

### 4. 详细日志
运行时会显示：
- 验证警告
- 重试次数
- 错误详情

## Agent 说明

| Agent | 功能 | LLM 难度 | 验证器 |
|-------|------|----------|--------|
| Image Analyzer | 理解图片内容 | 高 | - |
| Script Writer | 生成视频脚本 | 中 | ScriptValidator |
| Storyboard Writer | 编写分镜 | 中 | StoryboardValidator |
| Code Generator | 生成 Manim 代码 | 高 | CodeValidator |
| Audio Producer | 生成 TTS 语音 | 无 | - |
| Reviewer | 审核视频质量 | 高 | - |

## LLM 选择

系统支持根据任务难度自动选择合适的 LLM：

| 难度 | OpenAI | Anthropic |
|------|--------|-----------|
| 简单 (simple) | GPT-4o mini | Claude Haiku |
| 中等 (medium) | GPT-4o | Claude Sonnet |
| 困难 (hard) | GPT-4 Turbo | Claude 3.5 Sonnet |
| 视觉 (vision) | GPT-4o | Claude 3.5 Sonnet |

## 项目结构

```
multi_agent_animation/
├── agents/                  # Agent 实现
│   ├── orchestrator.py     # 协调器
│   ├── image_analyzer.py   # 图片理解
│   ├── script_writer.py    # 脚本编写
│   ├── storyboard_writer.py # 分镜编写
│   ├── code_generator.py   # 代码生成
│   ├── audio_producer.py   # 音频制作
│   └── reviewer.py         # 审核
├── llm/                    # LLM 接口
│   └── factory.py          # LLM 工厂
├── validators/             # 验证器（质量保证）
│   ├── base.py             # 验证基类
│   ├── storyboard.py       # 分镜验证
│   ├── code.py             # 代码验证
│   └── script.py           # 脚本验证
├── fallback.py             # 降级处理
├── main.py                 # 入口文件
└── requirements.txt        # 依赖列表
```

## 依赖

- openai
- anthropic
- edge-tts
- manim
- mutagen

## 常见问题

### Q: 运行时报错 "No module named 'openai'"

**A**: 需要先安装依赖，运行 `pip install -r requirements.txt`

### Q: 报错 "AuthenticationError" 或 "API 密钥无效"

**A**: 检查 API 密钥是否正确设置：
1. 确认环境变量已设置
2. 确认 API 密钥有效（余额充足）
3. 可尝试编辑 `llm/factory.py` 直接填入密钥

### Q: 生成视频太慢

**A**:
1. 使用 `-pql` 参数先预览低质量版本
2. 检查网络连接
3. 确认 API 配额充足

### Q: 音频文件没有生成

**A**:
- Windows 自带 edge-tts
- macOS/Linux 可能需要额外配置音频输出

### Q: 代码验证失败怎么办

**A**:
- 系统会自动尝试修复（最多3次）
- 如果仍失败，会保存代码供手动修改
- 查看错误信息，手动修正后重新运行

### Q: 怎么查看分镜内容？

**A**: 分镜保存在 `output/storyboard.md`，用任何文本编辑器或 VS Code 打开查看

## 注意事项

1. 使用前需要配置相应的 API Key
2. 部分功能需要网络访问
3. 生成的视频需要 Manim 环境才能渲染
4. 建议先在简单需求上测试，确认识证配置正确
