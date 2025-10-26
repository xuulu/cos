import csv
import uuid
import shutil
import hashlib
import mimetypes
import asyncio
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor


# 顶层函数 —— Windows 下可被多进程安全调用
def calc_sha1_sampled(file_path: str, sample_size: int = 1024 * 1024 * 2) -> str:
    """采样计算视频哈希（前1MB + 中间1MB）"""
    path = Path(file_path)
    sha = hashlib.sha1()
    size = path.stat().st_size
    with open(path, 'rb') as f:
        sha.update(f.read(sample_size // 2))
        if size > sample_size:
            f.seek(max(0, size // 2 - sample_size // 4))
            sha.update(f.read(sample_size // 2))
    return sha.hexdigest()


class VideoDatasetManager:
    def __init__(self, root_dir, per_dir_limit=200, move=False, workers=4, hash_sample_size=1024 * 1024 * 2):
        self.root = Path(root_dir)
        self.root.mkdir(exist_ok=True)
        self.per_dir_limit = per_dir_limit
        self.move = move
        self.hash_sample_size = hash_sample_size
        self.executor = ProcessPoolExecutor(max_workers=workers)

    # -----------------------------
    # 工具方法
    # -----------------------------
    @staticmethod
    def _read_csv_hashes(csv_path: Path) -> set:
        hashes = set()
        if not csv_path.exists():
            return hashes
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                h = row.get('hash')
                if h:
                    hashes.add(h)
        return hashes

    async def _load_hashes_from_all_csv(self) -> set:
        """并发读取所有csv哈希"""
        loop = asyncio.get_running_loop()
        tasks = []
        for csv_file in self.root.glob("*.csv"):
            tasks.append(loop.run_in_executor(None, self._read_csv_hashes, csv_file))
        if not tasks:
            return set()
        results = await asyncio.gather(*tasks)
        return set().union(*results)

    def _get_next_dir(self) -> Path:
        subdirs = sorted([p for p in self.root.iterdir() if p.is_dir()])
        if not subdirs:
            new_dir = self.root / "001"
            new_dir.mkdir()
            return new_dir
        last = subdirs[-1]
        count = len(list(last.glob("*")))
        if count < self.per_dir_limit:
            return last
        new_id = str(int(last.name) + 1).zfill(3)
        new_dir = self.root / new_id
        new_dir.mkdir(exist_ok=True)
        return new_dir

    def _get_next_id(self, csv_path: Path) -> int:
        if not csv_path.exists():
            return 1
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                ids = [int(row['id']) for row in reader if row.get('id')]
            return max(ids) + 1 if ids else 1
        except Exception:
            return 1

    # -----------------------------
    # 主逻辑
    # -----------------------------
    async def add_videos(self, src):
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(src)

        print("🎬 正在加载全局视频哈希索引...")
        all_hashes = await self._load_hashes_from_all_csv()
        print(f"✅ 已加载 {len(all_hashes)} 条记录")

        files = [src_path] if src_path.is_file() else list(src_path.glob("*"))
        files = [f for f in files if f.is_file()]
        print(f"📹 发现 {len(files)} 个视频文件")

        # 过滤非视频文件
        video_files = []
        for f in files:
            mime_type = mimetypes.guess_type(f)[0]
            if mime_type and mime_type.startswith('video'):
                video_files.append(f)
            else:
                print(f"⏭️ 跳过非视频文件: {f.name}")

        files = video_files
        if not files:
            print("⚠️ 没有找到任何视频文件")
            return

        # 使用顶层函数进行多进程哈希计算
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(
                self.executor, calc_sha1_sampled, str(f), self.hash_sample_size
            )
            for f in files
        ]
        hashes = await asyncio.gather(*tasks)

        # 统计数据
        processed_count = 0
        skipped_count = 0
        duplicated_count = 0

        for file, h in zip(files, hashes):
            if h in all_hashes:
                print(f"⚠️ 跳过重复: {file.name}")
                duplicated_count += 1
                continue

            target_dir = self._get_next_dir()
            new_name = f"{uuid.uuid4().hex}{file.suffix.lower()}"
            target_path = target_dir / new_name

            if self.move:
                shutil.move(str(file), target_path)
            else:
                shutil.copy2(file, target_path)

            csv_path = self.root / f"{target_dir.name}.csv"
            next_id = self._get_next_id(csv_path)
            write_header = not csv_path.exists()

            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'filename', 'hash'])
                if write_header:
                    writer.writeheader()
                writer.writerow({
                    'id': next_id,
                    'filename': new_name,
                    'hash': h
                })

            all_hashes.add(h)
            processed_count += 1
            print(f"✅ 已添加 #{next_id} → {target_dir.name}/{new_name}")

        print("🎉 视频处理完成！")
        print(f"📊 处理报告:")
        print(f"   - 成功处理: {processed_count} 个文件")
        print(f"   - 重复跳过: {duplicated_count} 个文件")
        print(f"   - 非视频跳过: {skipped_count} 个文件")

    def close(self):
        self.executor.shutdown()
