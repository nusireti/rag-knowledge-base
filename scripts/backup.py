"""
备份 RAG 知识库数据。

包含：
- `data/rag.db`：用 SQLite 在线备份 API 取一致性快照（避免拷到一半的 WAL 状态）
- `knowledge_bases/`：文档与向量库
- `conversations/`：对话记录

用法：
    python scripts/backup.py                 # 写到 backups/，保留最近 7 份
    python scripts/backup.py --keep 14
    python scripts/backup.py --out D:/backups
"""

from __future__ import annotations

import argparse
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def create_backup(
    root: Path = ROOT,
    out_dir: Path | None = None,
    keep: int = 7,
) -> Path:
    """创建一份 zip 备份，返回归档路径。"""
    root = Path(root)
    out_dir = Path(out_dir) if out_dir else root / "backups"
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = out_dir / f"backup-{stamp}.zip"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = root / "data" / "rag.db"
        snapshot = tmp_path / "rag.db"

        if db_path.exists():
            # 在线备份：SQLite 会把一个一致的状态写入目标文件。
            # 必须显式 close —— 在 Windows 上连接不关会占着临时目录，
            # TemporaryDirectory 清理时直接 PermissionError。
            src = sqlite3.connect(str(db_path))
            dst = sqlite3.connect(str(snapshot))
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()

        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            if snapshot.exists():
                zf.write(snapshot, "data/rag.db")

            for folder in ("knowledge_bases", "conversations"):
                base = root / folder
                if not base.exists():
                    continue
                for file in base.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(root))

    # 保留最近 keep 份
    archives = sorted(
        out_dir.glob("backup-*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in archives[keep:]:
        old.unlink(missing_ok=True)

    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description="备份 RAG 知识库数据")
    parser.add_argument("--out", default=None, help="输出目录（默认 <项目>/backups）")
    parser.add_argument("--keep", type=int, default=7, help="保留最近几份（默认 7）")
    args = parser.parse_args()

    archive = create_backup(
        out_dir=Path(args.out) if args.out else None,
        keep=args.keep,
    )
    size_mb = archive.stat().st_size / 1024 / 1024
    print(f"备份完成: {archive} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
