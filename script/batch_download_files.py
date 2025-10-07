import requests
from pathlib import Path
import concurrent.futures
from urllib.parse import urlparse
import os

def batch_download_files(url_file_path, download_dir="./downloads", max_workers=5):
    """
    批量下载文件链接列表中的文件

    Args:
        url_file_path (str): 包含文件链接的文本文件路径（每行一个链接）
        download_dir (str): 下载文件保存目录，默认为"./downloads"
        max_workers (int): 最大并发下载数，默认为5

    Returns:
        dict: 下载结果统计信息
    """

    # 创建下载目录
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    # 读取URL列表
    with open(url_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    # 下载统计信息
    results = {
        "total": len(urls),
        "success": 0,
        "failed": 0,
        "failed_urls": []
    }

    def download_single_file(url):
        """下载单个文件"""
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # 从URL中提取文件名
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name

            # 如果无法从URL获取文件名，则使用默认名称
            if not filename or '.' not in filename:
                filename = f"file_{hash(url) % 10000}"

            file_path = Path(download_dir) / filename

            # 写入文件
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"成功下载: {url} -> {file_path}")
            return True, url, None

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"下载失败: {url} - {error_msg}")
            return False, url, error_msg

    # 并发下载
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(download_single_file, url): url for url in urls}

        for future in concurrent.futures.as_completed(future_to_url):
            success, url, error = future.result()
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_urls"].append({"url": url, "error": error})

    # 打印总结信息
    print(f"\n下载完成统计:")
    print(f"总计: {results['total']}")
    print(f"成功: {results['success']}")
    print(f"失败: {results['failed']}")

    return results

# 使用示例
if __name__ == "__main__":
    # 示例用法
    # batch_download_files("urls.txt", "./downloads", max_workers=3)
    pass
