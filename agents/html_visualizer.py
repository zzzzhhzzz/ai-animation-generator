"""
HTML 可视化 Agent - 步骤2: 生成 HTML + SVG 可视化
"""

from typing import Dict, Any
from llm.factory import create_llm


class HTMLVisualizer:
    """HTML 可视化 Agent"""

    SYSTEM_PROMPT = """你是一个专业的数学可视化专家。你擅长用 HTML + SVG 绘制几何图形，展示解题过程。

## 你的任务
根据数学分析结果，生成一个交互式的 HTML 文件，包含 SVG 图形来展示几何关系和解答流程。

## 输出要求

1. **文件命名**: `数学_{日期}_{题目简述}.html`
2. **内容结构**:
   - 题目陈述
   - SVG 图形（展示几何关系）
   - 分步解答（带动画效果）
   - 关键要素标注

3. **SVG 要求**:
   - 展示完整的几何图形
   - 标注所有关键点（A, B, C...）
   - 标注边长、角度
   - 使用不同颜色区分不同元素

4. **展示画图过程**（重要）:
   - 先画什么、后画什么
   - 动画顺序
   - 关键步骤的说明

## HTML 模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>数学可视化</title>
    <style>
        body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        .container { display: flex; gap: 20px; }
        .problem, .solution { flex: 1; }
        svg { border: 1px solid #ccc; background: #f9f9f9; }
        .step { margin: 20px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }
        h2 { color: #333; border-bottom: 2px solid #4ecca3; padding-bottom: 10px; }
        .label { font-size: 14px; fill: #333; }
    </style>
</head>
<body>
    <h1>数学可视化</h1>

    <div class="container">
        <div class="problem">
            <h2>题目</h2>
            <p>这里是题目内容...</p>
        </div>

        <div class="solution">
            <h2>图形</h2>
            <svg width="400" height="400" viewBox="-5 -5 10 10">
                <!-- SVG 图形内容 -->
            </svg>
        </div>
    </div>

    <h2>解答步骤</h2>
    <div class="step">
        <h3>步骤1: ...</h3>
        <p>说明...</p>
    </div>
</body>
</html>
```

## SVG 绘图规范

1. **坐标系**: 使用 viewBox="-5 -5 10 10" 表示 x∈[-5,5], y∈[-5,5]
2. **颜色方案**:
   - 背景: #f9f9f9
   - 线条: #333333
   - 高亮: #e94560 (红色)
   - 辅助线: #4ecca3 (青色)
   - 标注: #666666
3. **线条粗细**: 基础线条 2px，高亮线条 3px
4. **标注位置**: 避免重叠，适当偏移

## 重要提醒

1. SVG 只需要展示**最终图形**，不需要动画
2. 标注要清晰，点名要明确（A, B, C...）
3. 边长、角度要标注具体数值（如果已知）
4. 图形要居中，在可视区域内

现在开始生成 HTML 文件。"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.llm = create_llm(provider, **kwargs)

    def visualize(self, math_analysis: str) -> Dict[str, Any]:
        """生成 HTML 可视化

        Args:
            math_analysis: 数学分析结果

        Returns:
            HTML 内容
        """
        prompt = f"""请根据以下数学分析生成 HTML + SVG 可视化文件：

{math_analysis}

{self.SYSTEM_PROMPT}

请直接输出完整的 HTML 代码，不要有其他说明。"""

        try:
            result = self.llm.chat(
                prompt,
                task_difficulty="medium",
                system_prompt="你是一个数学可视化专家，擅长生成 SVG 图形。",
                max_tokens=6000
            )

            return {
                "success": True,
                "html": result,
                "analysis": math_analysis
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"HTML可视化失败: {e}"
            }
