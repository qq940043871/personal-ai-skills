#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
去除图片右下角水印的工具。
支持两种模式：
  - crop:  直接裁掉右下角指定区域（简单粗暴，会改变图片尺寸）
  - inpaint: 使用OpenCV图像修复算法智能填充水印区域（保持原尺寸）

用法:
  python remove_watermark.py                        # 处理所有image/目录下的png图片
  python remove_watermark.py --mode crop            # 使用裁剪模式
  python remove_watermark.py --mode inpaint         # 使用修复模式（默认）
  python remove_watermark.py --w 120 --h 50         # 自定义水印区域宽高
  python remove_watermark.py image/doubao_image_1.png  # 处理单张图片
"""

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def detect_watermark_region(img_bgr: np.ndarray, corner_size: int = 200) -> tuple | None:
    """
    自动检测右下角水印边界。
    通过分析右下角区域像素的颜色/透明度变化来找到水印边界。
    返回 (x1, y1, x2, y2) 或 None。
    """
    h, w = img_bgr.shape[:2]

    # 截取右下角检测区域
    x0, y0 = max(0, w - corner_size), max(0, h - corner_size)
    roi = img_bgr[y0:h, x0:w].copy()

    # 转灰度
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 用边缘检测找水印边界
    edges = cv2.Canny(gray, 30, 100)
    # 找到非零像素的边界框
    ys, xs = np.where(edges > 0)

    if len(ys) < 50:  # 边缘太少，可能没有明显水印
        return None

    y_min, y_max = ys.min(), ys.max()
    x_min, x_max = xs.min(), xs.max()

    # 膨胀一点确保完全覆盖水印
    margin = 4
    x1 = max(0, x0 + x_min - margin)
    y1 = max(0, y0 + y_min - margin)
    x2 = min(w, x0 + x_max + margin)
    y2 = min(h, y0 + y_max + margin)

    return (x1, y1, x2, y2)


def remove_watermark_crop(
    img_bgr: np.ndarray,
    watermark_width: int,
    watermark_height: int,
) -> np.ndarray:
    """裁剪模式：直接裁掉右下角指定区域。"""
    h, w = img_bgr.shape[:2]
    new_w = w - watermark_width
    new_h = h - watermark_height
    return img_bgr[0:new_h, 0:new_w]


def remove_watermark_inpaint(
    img_bgr: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    inpaint_radius: int = 5,
) -> np.ndarray:
    """修复模式：使用OpenCV inpainting去除水印区域。"""
    h, w = img_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255
    result = cv2.inpaint(img_bgr, mask, inpaint_radius, cv2.INPAINT_TELEA)
    return result


def process_image(
    input_path: str,
    output_dir: str | None,
    mode: str,
    watermark_width: int,
    watermark_height: int,
    inpaint_radius: int,
    auto_detect: bool,
    corner_size: int,
) -> bool:
    """处理单张图片。"""
    filename = Path(input_path).name
    print(f"处理: {filename}")

    # 读取图片
    img_bgr = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if img_bgr is None:
        print(f"  错误: 无法读取图片 {input_path}")
        return False

    h, w = img_bgr.shape[:2]
    print(f"  尺寸: {w}x{h}")

    if mode == "inpaint":
        if auto_detect:
            bbox = detect_watermark_region(img_bgr, corner_size)
            if bbox is None:
                print("  未检测到水印，使用默认右下角区域")
                x1, y1 = w - watermark_width, h - watermark_height
                x2, y2 = w, h
            else:
                x1, y1, x2, y2 = bbox
                print(f"  检测到水印区域: ({x1},{y1}) -> ({x2},{y2})")
        else:
            x1, y1 = w - watermark_width, h - watermark_height
            x2, y2 = w, h
            print(f"  水印区域: ({x1},{y1}) -> ({x2},{y2})")

        result = remove_watermark_inpaint(img_bgr, x1, y1, x2, y2, inpaint_radius)
        print(f"  修复完成 (inpaint radius={inpaint_radius})")
    else:
        result = remove_watermark_crop(img_bgr, watermark_width, watermark_height)
        print(f"  裁剪完成，新尺寸: {result.shape[1]}x{result.shape[0]}")

    # 保存结果
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_nowm{ext}"

    cv2.imwrite(output_path, result)
    print(f"  已保存: {os.path.basename(output_path)}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="去除图片右下角水印",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python remove_watermark.py                          # 处理所有图片(默认inpaint模式)
  python remove_watermark.py --mode crop              # 裁剪模式
  python remove_watermark.py --mode inpaint --auto    # 自动检测水印
  python remove_watermark.py --w 150 --h 60           # 自定义水印区域大小
  python remove_watermark.py image/doubao_image_1.png # 处理单张图片
  python remove_watermark.py --output output/         # 输出到指定目录
        """,
    )
    parser.add_argument(
        "input", nargs="*",
        help="输入图片路径，不指定则处理 image/ 目录下所有png图片",
    )
    parser.add_argument(
        "--mode", choices=["inpaint", "crop"], default="inpaint",
        help="去除模式: inpaint(修复,默认) / crop(裁剪)",
    )
    parser.add_argument(
        "--w", "--watermark-width", dest="watermark_width",
        type=int, default=120,
        help="水印宽度(像素)，默认120",
    )
    parser.add_argument(
        "--h", "--watermark-height", dest="watermark_height",
        type=int, default=50,
        help="水印高度(像素)，默认50",
    )
    parser.add_argument(
        "--radius", type=int, default=5,
        help="inpaint修复半径，默认5",
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="自动检测水印边界(inpaint模式)",
    )
    parser.add_argument(
        "--corner-size", type=int, default=200,
        help="自动检测时扫描的右下角区域大小，默认200",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="输出目录，默认在源文件同目录下添加_nowm后缀",
    )

    args = parser.parse_args()

    # 确定输入文件列表
    if args.input:
        input_files = args.input
    else:
        image_dir = Path(__file__).parent / "image"
        if not image_dir.exists():
            print(f"错误: 目录不存在 {image_dir}")
            sys.exit(1)
        input_files = sorted(str(p) for p in image_dir.glob("*.png"))

    if not input_files:
        print("没有找到要处理的图片")
        sys.exit(0)

    # 处理统计
    success, fail = 0, 0
    print(f"模式: {args.mode}")
    print(f"待处理: {len(input_files)} 张图片")
    print("-" * 50)

    for path in input_files:
        if "原子游骑兵" in path:
            print(f"跳过(非AI生成图): {os.path.basename(path)}")
            continue
        if process_image(
            path, args.output, args.mode,
            args.watermark_width, args.watermark_height,
            args.radius, args.auto, args.corner_size,
        ):
            success += 1
        else:
            fail += 1

    print("-" * 50)
    print(f"完成: 成功 {success}, 失败 {fail}")


if __name__ == "__main__":
    main()
