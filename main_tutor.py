#!/usr/bin/env python3
"""
Tutor 工作流入口 - 数学辅导视频生成系统

使用方式：
    python main_tutor.py "在正方形ABCD中，E是AB的中点，F是BC的中点，求证AE=EF"
    python main_tutor.py --image path/to/problem.png "分析这个题目"
    python main_tutor.py --step 5 --end 8 "继续生成视频"
"""

import sys
import os
import argparse
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import TutorOrchestrator


def main():
    parser = argparse.ArgumentParser(description="数学辅导视频生成系统")
    parser.add_argument("problem", nargs="?", help="数学题目")
    parser.add_argument("--image", "-i", help="题目图片路径（可选）")
    parser.add_argument("--step", "-s", type=int, default=1, help="起始步骤（1-8）")
    parser.add_argument("--end", "-e", type=int, default=8, help="结束步骤（1-8）")
    parser.add_argument("--output", "-o", default="tutor_output", help="输出目录")
    parser.add_argument("--provider", "-p", default="anthropic", help="LLM 提供商")

    args = parser.parse_args()

    # 如果没有提供题目，提示用户
    if not args.problem:
        # 尝试从环境变量或文件读取
        print("请输入数学题目，或使用以下方式：")
        print("  python main_tutor.py \"你的题目\"")
        print("  python main_tutor.py --image path/to/image.png \"分析图片\"")
        return

    print("=" * 60)
    print("数学辅导视频生成系统 - 8步工作流")
    print("=" * 60)
    print(f"题目: {args.problem}")
    if args.image:
        print(f"图片: {args.image}")
    print(f"步骤: {args.step} → {args.end}")
    print(f"输出: {args.output}")
    print(f"LLM: {args.provider}")
    print()

    # 创建协调器
    orchestrator = TutorOrchestrator(provider=args.provider)

    # 运行工作流
    result = orchestrator.run(
        problem=args.problem,
        image_path=args.image,
        output_dir=args.output,
        start_step=args.step,
        end_step=args.end
    )

    print()
    if result.get("success"):
        print("=" * 60)
        print("生成完成！")
        print("=" * 60)
        print(f"输出目录: {result.get('output_dir')}")
        print(f"数学分析: {result.get('state', {}).get('math_analysis')}")
        print(f"分镜文件: {result.get('state', {}).get('storyboard_file')}")
        print(f"代码文件: {result.get('state', {}).get('script_file')}")
        print(f"视频文件: {result.get('state', {}).get('video_file')}")
    else:
        print("=" * 60)
        print("生成失败")
        print("=" * 60)
        print(f"错误: {result.get('error')}")

        # 显示失败的步骤
        if "steps" in result:
            for step_name, step_result in result["steps"].items():
                if not step_result.get("success"):
                    print(f"  - {step_name}: {step_result.get('error')}")


if __name__ == "__main__":
    main()
