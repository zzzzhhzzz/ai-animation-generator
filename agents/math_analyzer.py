"""
数学分析 Agent - 步骤1: 分析题目，推导数学事实
"""

from typing import Dict, Any
from llm.factory import create_llm


class MathAnalyzer:
    """数学分析 Agent"""

    SYSTEM_PROMPT = """你是一个专业的数学老师。你擅长分析数学题目，推导数学事实，建立几何模型。

## 你的任务
根据给定的数学题目，进行严谨的数学分析，推导出解题所需的几何事实，并确定图形的构建方法。

## 输出格式要求

请严格按照以下格式输出：

```markdown
## 数学事实分析

### 已知条件
- 条件1：...
- 条件2：...

### 推导的事实
1. **事实名称**: 描述
   - 计算过程: ...
   - 数学表达: ...

### 图形构建方法
- 点的坐标: ...
- 边的关系: ...
- 圆/弧的定义: ...

### 需要证明的结论
- 结论1: ...
```

## 重要规则

1. **绝不使用坐标系计算** - 使用纯几何推理（等积变换、相似三角形、勾股定理、向量叉积等）
2. **所有结论都需要证明** - 包括几何关系、长度、角度等
3. **图形构建方法要具体** - 给出点的坐标（如果需要）、边的关系等
4. **数学表达要规范** - 使用标准的数学符号

## 示例

对于题目"在正方形ABCD中，E是AB的中点，F是BC的中点，求证AE=EF"：

### 已知条件
- ABCD是正方形（四条边相等，四个角都是直角）
- E是AB的中点
- F是BC的中点

### 推导的事实
1. **边长关系**: 设正方形边长为a，则AB=BC=CD=DA=a
2. **中点定义**: AE=BE=AB/2=a/2, BF=CF=BC/2=a/2
3. **三角形相似**: △AEF ~ △ABC（对应边成比例）

### 图形构建方法
- 正方形边长设为a（可缩放）
- A=(0,0), B=(a,0), C=(a,a), D=(0,a)
- E=(a/2, 0), F=(a, a/2)
- 坐标系仅用于**构建图形**，计算必须用纯几何方法

### 需要证明的结论
- AE = EF（通过相似三角形或勾股定理证明）

现在开始分析题目。"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.llm = create_llm(provider, **kwargs)

    def analyze(self, problem: str) -> Dict[str, Any]:
        """分析数学题目

        Args:
            problem: 数学题目文本

        Returns:
            分析结果
        """
        prompt = f"""请分析以下数学题目：

{problem}

{self.SYSTEM_PROMPT}

请直接输出分析结果，不要有其他说明。"""

        try:
            result = self.llm.chat(
                prompt,
                task_difficulty="hard",
                system_prompt="你是一个专业的数学老师，擅长几何证明。",
                max_tokens=4000
            )

            return {
                "success": True,
                "analysis": result,
                "problem": problem
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"数学分析失败: {e}"
            }

    def analyze_from_image(self, context: str, image_path: str) -> Dict[str, Any]:
        """从图片分析数学题目

        Args:
            context: 上下文/补充说明
            image_path: 图片路径

        Returns:
            分析结果
        """
        # TODO: 实现图片分析（需要使用 vision LLM）
        return self.analyze(context)
