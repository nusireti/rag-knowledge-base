"""备份脚本测试。"""

import os
import sqlite3
import zipfile

from scripts.backup import create_backup


def _make_project(tmp_path):
    root = tmp_path / "proj"
    (root / "data").mkdir(parents=True)
    (root / "knowledge_bases" / "kb1").mkdir(parents=True)
    (root / "conversations").mkdir()

    (root / "knowledge_bases" / "kb1" / "a.md").write_text(
        "hello", encoding="utf-8"
    )
    (root / "conversations" / "c1.json").write_text("{}", encoding="utf-8")

    conn = sqlite3.connect(root / "data" / "rag.db")
    try:
        conn.execute("create table t (id integer)")
        conn.execute("insert into t values (1)")
        conn.commit()
    finally:
        conn.close()
    return root


def test_create_backup_contains_all_parts(tmp_path):
    root = _make_project(tmp_path)
    archive = create_backup(root=root, out_dir=root / "backups", keep=7)

    assert archive.exists()
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        assert "data/rag.db" in names
        assert "knowledge_bases/kb1/a.md" in names
        assert "conversations/c1.json" in names


def test_backup_retention(tmp_path):
    root = _make_project(tmp_path)
    out = root / "backups"
    out.mkdir()

    # 造 3 份旧备份，按 mtime 排出新旧
    for i in range(3):
        old = out / f"backup-2026010{i + 1}-000000.zip"
        old.write_bytes(b"x")
        os.utime(old, (1000 + i, 1000 + i))

    create_backup(root=root, out_dir=out, keep=2)

    remaining = list(out.glob("backup-*.zip"))
    assert len(remaining) == 2
