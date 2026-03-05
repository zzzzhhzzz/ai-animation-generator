#!/usr/bin/env python3
"""
多 Agent 动画自动生成系统

使用方式：
    python main.py "帮我制作一个讲解勾股定理的视频"
    python main.py --image path/to/image.png "分析这个题目"
    python main.py --mode simple "制作一个数学题讲解视频"
"""

import sys
import os
import argparse
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import Orchestrator


def main():
    parser = argparse.ArgumentParser(description="多 Agent 动画自动生成系统")
    parser.add_argument("requirement", help="用户需求描述")
    parser.add_argument("--image", "-i", help="图片路径（可选）")
    parser.add_argument("--mode", "-m", choices=["full", "simple", "storyboard_only"],
                       default="full", help="运行模式")
    parser.add_argument("--output", "-o", default="output", help="输出目录")
    parser.add_argument("--provider", "-p", default="openai",
                       choices=["openai", "anthropic"], help="LLM 提供商")

    args = parser.parse_args()

    print("="*60)
    print("多 Agent 动画自动生成系统")
    print("="*60)
    print(f"需求: {args.requirement}")
    if args.image:
        print(f"图片: {args.image}")
    print(f"模式: {args.mode}")
    print(f"输出: {args.output}")
    print(f"LLM: {args.provider}")
    print()

    # 创建协调器
    orchestrator = Orchestrator(provider=args.provider)

    # 运行工作流程
    result = orchestrator.run(
        requirement=args.requirement,
        image_path=args.image,
        mode=args.mode,
        output_dir=args.output
    )

    print()
    if result.get("success"):
        print("="*60)
        print("生成完成！")
        print("="*60)
        print(f"输出目录: {result.get('output_dir')}")
        print(f"分镜文件: {result.get('storyboard_path')}")
        print(f"代码文件: {result.get('code_path')}")
        print(f"音频目录: {result.get('audio_dir')}")
    else:
        print("="*60)
        print("生成失败")
        print("="*60)
        print(f"错误: {result.get('error')}")

        # 显示失败的步骤
        if "results" in result:
            for step_name, step_result in result["results"].get("steps", []):
                if not step_result.get("success"):
                    print(f"  - {step_name}: {step_result.get('error')}")


if __name__ == "__main__":
    main()
