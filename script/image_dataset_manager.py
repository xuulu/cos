import csv
import uuid
import shutil
import hashlib
import asyncio
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor


class ImageDatasetManager:
    def __init__(self, root_dir, per_dir_limit=500, move=False, workers=4):
        """
        初始化图像数据集管理器

        :param root_dir: 数据集根目录路径
        :param per_dir_limit: 每个子目录最多存放的文件数量，默认500
        :param move: 文件操作模式，True表示移动文件，False表示复制文件
        :param workers: 用于并发处理的进程数
        """
        self.root = Path(root_dir)
        self.root.mkdir(exist_ok=True)  # 创建根目录（如果不存在）
        self.per_dir_limit = per_dir_limit
        self.move = move
        self.executor = ProcessPoolExecutor(max_workers=workers)  # 创建进程池

    # -----------------------------
    # 基础方法
    # -----------------------------
    @staticmethod
    def _sha1(file_path: Path) -> str:
        """同步计算文件的SHA-1哈希值"""
        sha = hashlib.sha1()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha.update(chunk)
        return sha.hexdigest()

    async def _calc_sha1(self, file_path: Path) -> str:
        """异步封装哈希计算，在进程池中执行"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._sha1, file_path)

    @staticmethod
    def _read_csv_hashes(csv_path: Path) -> set:
        """同步读取CSV文件中的hash列，返回哈希值集合"""
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
        """异步读取根目录下所有CSV文件的哈希值"""
        tasks = []
        for csv_file in self.root.glob("*.csv"):
            loop = asyncio.get_running_loop()
            tasks.append(loop.run_in_executor(None, self._read_csv_hashes, csv_file))
        if not tasks:
            return set()
        results = await asyncio.gather(*tasks)
        return set().union(*results)

    # -----------------------------
    # 逻辑部分
    # -----------------------------
    def _get_next_dir(self) -> Path:
        """返回当前可写入的子目录路径"""
        # 获取所有已存在的子目录并排序
        subdirs = sorted([p for p in self.root.iterdir() if p.is_dir()])

        # 如果没有子目录，创建第一个目录001
        if not subdirs:
            new_dir = self.root / "001"
            new_dir.mkdir()
            return new_dir

        # 检查最后一个目录是否还有空间
        last = subdirs[-1]
        count = len(list(last.glob("*")))
        if count < self.per_dir_limit:
            return last

        # 如果最后一个目录已满，创建新目录
        new_id = str(int(last.name) + 1).zfill(3)
        new_dir = self.root / new_id
        new_dir.mkdir(exist_ok=True)
        return new_dir

    def _get_next_id(self, csv_path: Path) -> int:
        """获取CSV中最大ID+1，作为新记录的ID"""
        if not csv_path.exists():
            return 1
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                ids = [int(row['id']) for row in reader if row.get('id')]
            return max(ids) + 1 if ids else 1
        except Exception:
            return 1

    async def add_images(self, src):
        """添加图片到数据集（支持单文件或整个目录）"""
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(src)

        print("📂 正在加载哈希索引...")
        all_hashes = await self._load_hashes_from_all_csv()
        print(f"✅ 已加载 {len(all_hashes)} 条记录")

        # 收集待处理的文件列表
        files = [src_path] if src_path.is_file() else list(src_path.glob("*"))
        files = [f for f in files if f.is_file()]
        print(f"📸 发现 {len(files)} 张图片")

        # 并发计算所有文件的哈希值
        tasks = [self._calc_sha1(f) for f in files]
        hashes = await asyncio.gather(*tasks)

        # 处理每个文件
        for file, h in zip(files, hashes):
            # 如果哈希值已存在，跳过该文件（去重）
            if h in all_hashes:
                print(f"⚠️ 跳过重复: {file.name}")
                continue

            # 获取可用的目标子目录
            target_dir = self._get_next_dir()
            # 生成新的唯一文件名
            new_name = f"{uuid.uuid4().hex}{file.suffix.lower()}"
            target_path = target_dir / new_name

            # 根据设置移动或复制文件
            if self.move:
                shutil.move(str(file), target_path)
            else:
                shutil.copy2(file, target_path)

            # 确定对应的CSV文件路径（与子目录同名）
            csv_path = self.root / f"{target_dir.name}.csv"
            next_id = self._get_next_id(csv_path)
            write_header = not csv_path.exists()

            # 将记录写入CSV文件
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'filename', 'hash'])
                if write_header:
                    writer.writeheader()
                writer.writerow({
                    'id': next_id,
                    'filename': new_name,
                    'hash': h
                })

            # 更新内存中的哈希集合
            all_hashes.add(h)
            print(f"✅ 已添加 #{next_id} → {target_dir.name}/{new_name}")

        print("🎉 全部完成！")

    def close(self):
        """关闭进程池，释放资源"""
        self.executor.shutdown()

