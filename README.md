# COS - 内容组织系统

COS (Content Organization System) 是一个用于管理和组织大量图像和视频文件的Python工具脚本。它支持自动去重、分目录存储和元数据维护等功能。

## 功能特点

- **自动去重**: 基于SHA-1哈希值对图像和视频进行去重处理
- **智能分目录**: 自动将文件分配到子目录中，避免单个目录文件过多
- **文件名唯一**: 使用uuid作为文件名，确保文件名的唯一性
- **元数据维护**: 自动生成并维护CSV格式的文件元数据记录
- **支持复制和移动**: 可选择复制或移动文件模式
- **高性能处理**: 使用异步并发处理提高大量文件的处理速度

## 安装

确保你已经安装了Python 3.13或更高版本。

```bash
# 克隆项目
git clone https://github.com/xuulu/cos.git
cd cos

# 安装依赖
pip install -r requirements.txt

# 或者使用uv包管理器:
uv sync
```

## 使用方法

### 图像文件管理

```python
from script.image_dataset_manager import ImageDatasetManager
import asyncio

async def main():
    # 创建管理器实例
    manager = ImageDatasetManager(
        root_dir="./images",     # 数据集根目录
        per_dir_limit=500,       # 每个子目录文件上限
        move=False,              # False=复制, True=移动
        workers=4                # 并发工作进程数
    )

    # 添加图像（支持单文件或目录）
    await manager.add_images("./new_images")

    # 释放资源
    manager.close()

asyncio.run(main())
```

### 视频文件管理

```python
from script.video_dataset_manager import VideoDatasetManager
import asyncio

async def main():
    # 创建管理器实例
    manager = VideoDatasetManager(
        root_dir="./videos",     # 数据集根目录
        per_dir_limit=200,       # 每个子目录文件上限
        move=False,              # False=复制, True=移动
        workers=4                # 并发工作进程数
    )

    # 添加视频（支持单文件或目录）
    await manager.add_videos("./new_videos")

    # 释放资源
    manager.close()

asyncio.run(main())
```

## 项目结构

```
cos/
├── script/
│   ├── image_dataset_manager.py   # 图像数据集管理器
│   └── video_dataset_manager.py   # 视频数据集管理器
├── images/                        # 图像存储目录
│   ├── 001/                       # 子目录1
│   ├── 001.csv                    # 子目录1的数据记录
│   ├── 002/                       # 子目录2
│   ├── 002.csv                    # 子目录2的数据记录
│   └── ...
├── videos/                        # 视频存储目录
│   ├── 001/                       # 子目录1
│   ├── 001.csv                    # 子目录1的数据记录
│   ├── 002/                       # 子目录2
│   ├── 002.csv                    # 子目录2的数据记录
│   └── ...
├── main.py                        # 主程序入口
└── pyproject.toml                 # 项目配置文件
```

## 技术细节

### 图像去重原理

图像去重使用完整的SHA-1哈希值计算，确保完全相同的图像文件被识别为重复文件。

### 视频去重原理

由于视频文件通常较大，为了提高处理效率，视频去重采用采样哈希方式：
- 读取视频文件的前1MB数据
- 读取视频文件中间部分的1MB数据
- 基于这些数据计算SHA-1哈希值

这种方式在保证去重准确性的同时大大提高了处理速度。

## 许可证

本项目采用GNU通用公共许可证v3.0（GPL-3.0）开源协议。详情请参见[LICENSE](LICENSE)文件。