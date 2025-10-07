from script.image_dataset_manager import ImageDatasetManager
from script.video_dataset_manager import VideoDatasetManager
from script.batch_download_files import batch_download_files
import asyncio


# 图片数据集管理
async def main_for_image_dataset_manager():
    # 创建管理器实例
    manager = ImageDatasetManager(
        root_dir=r"./images",  # 要保存的根目录
        per_dir_limit=500,  # 每个子目录文件上限
        move=False,  # False=复制, True=移动
        workers=4  # 并发工作进程数
    )

    # 添加图像（支持单文件或目录）
    await manager.add_images(r"D:\images")

    # 释放资源
    manager.close()


# 视频数据集管理
async def main_for_video_dataset_manager():
    # 创建管理器实例
    manager = VideoDatasetManager(
        root_dir="./videos",  # 要保存的根目录
        per_dir_limit=200,  # 每个子目录文件上限
        move=False,  # False=复制, True=移动
        workers=4  # 并发工作进程数
    )

    # 添加视频（可传入单个视频或目录
    await manager.add_videos(r"C:\Users\a\Downloads\downloads")

    # 释放资源
    manager.close()


async def main_for_batch_download_files():
    # 批量下载文件(读取指定文件，一行一个url，并发下载到指定目录)
    results = batch_download_files(
        url_file_path=r"C:\Users\a.txt",  # 链接文件路径
        download_dir=r"C:\Users\a\downloads",  # 下载目录
        max_workers=8  # 并发下载数
    )
    print(results)

if __name__ == "__main__":
    # 图片数据集管理
    # asyncio.run(main_for_image_dataset_manager())
    # 视频数据集管理
    asyncio.run(main_for_video_dataset_manager())
