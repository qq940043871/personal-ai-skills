---
name: tool-remove-watermark
description: 去除图片右下角水印工具。支持智能修复(inpaint)和裁剪(crop)两种模式。当用户提到"去除水印"、"去掉水印"、"remove watermark"、"删除水印"、或需要批量处理图片水印时使用。自动检测右下角水印区域并使用OpenCV图像修复算法填充。
---

# tool-remove-watermark — 图片水印去除

一键去除图片右下角水印，支持批量处理和自动检测。

## 功能

- **inpaint 修复模式**（默认）：使用 OpenCV 图像修复算法智能填充水印区域，保持原尺寸
- **crop 裁剪模式**：直接裁掉右下角指定区域
- **自动检测**：通过边缘检测自动定位水印边界
- **批量处理**：一次处理整个目录的所有图片

## 依赖

```bash
pip install opencv-python pillow numpy
```

## 使用步骤

### 1. 将脚本复制到目标项目

将此 skill 目录下的 `remove_watermark.py` 复制到目标项目根目录：

```bash
cp <skill-dir>/remove_watermark.py <target-project>/
```

或者直接在目标项目中运行（使用绝对路径）。

### 2. 基本用法

```bash
# 处理 image/ 目录下所有 png 图片（默认 inpaint 模式）
python remove_watermark.py

# 处理指定图片
python remove_watermark.py image/my_image.png

# 处理多张图片
python remove_watermark.py image/img1.png image/img2.png

# 指定输出目录
python remove_watermark.py -o output_dir/
```

### 3. 模式选择

```bash
# inpaint 修复模式（默认，保持原尺寸）
python remove_watermark.py --mode inpaint

# crop 裁剪模式（图片会缩小）
python remove_watermark.py --mode crop
```

### 4. 调整参数

```bash
# 自定义水印区域大小（默认 120x50 像素）
python remove_watermark.py --w 150 --h 60

# 调整 inpaint 修复半径（默认 5）
python remove_watermark.py --radius 8

# 自动检测水印边界
python remove_watermark.py --auto

# 自定义自动检测扫描区域大小（默认 200 像素）
python remove_watermark.py --auto --corner-size 300
```

### 5. 组合使用

```bash
# 自动检测 + 指定输出目录 + 调整修复半径
python remove_watermark.py --auto --radius 10 -o clean_images/

# 裁剪模式 + 自定义水印大小 + 指定图片
python remove_watermark.py --mode crop --w 80 --h 40 image/photo.jpg
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入图片路径，不指定则处理 `image/` 目录下所有 PNG | `image/*.png` |
| `--mode` | 去除模式：`inpaint`(修复) / `crop`(裁剪) | `inpaint` |
| `--w` / `--watermark-width` | 水印宽度(像素) | `120` |
| `--h` / `--watermark-height` | 水印高度(像素) | `50` |
| `--radius` | inpaint 修复半径 | `5` |
| `--auto` | 自动检测水印边界 | 关闭 |
| `--corner-size` | 自动检测时的右下角扫描区域大小 | `200` |
| `--output` / `-o` | 输出目录 | 源文件同目录 `_nowm` 后缀 |

## 模式对比

| 特性 | inpaint | crop |
|------|---------|------|
| 输出尺寸 | 保持原尺寸 | 变小 |
| 处理效果 | 智能填充，自然过渡 | 直接切除 |
| 处理速度 | 较慢（需计算） | 快 |
| 适用场景 | 需要保持原尺寸/构图 | 不关心尺寸变化 |

## 在对话中使用

当用户要求去除图片水印时：

1. 确认目标图片目录和文件格式
2. 将 `remove_watermark.py` 复制到目标项目
3. 运行命令处理图片
4. 如果默认参数效果不理想，建议用户调整 `--w`、`--h`、`--radius` 参数

**快速指令示例**：
```bash
# 最常用的命令：处理所有图片，输出到 image_nowm/ 目录
python remove_watermark.py -o image_nowm/
```
