"""第 3 轮工程卫生的回归测试。"""

import os
import sys
import types

import pytest

import app.rag.hybrid as hybrid
import kb_manager


@pytest.fixture(autouse=True)
def _clean_rerank():
    hybrid.clear_rerank_model()
    yield
    hybrid.clear_rerank_model()


def _install_fake_cross_encoder(monkeypatch, calls):
    class FakeCrossEncoder:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.CrossEncoder = FakeCrossEncoder
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)


def test_rerank_model_is_reused(monkeypatch):
    """连续取两次必须是同一个实例，且只加载一次权重。"""
    calls = []
    _install_fake_cross_encoder(monkeypatch, calls)

    first = hybrid.get_rerank_model()
    second = hybrid.get_rerank_model()

    assert first is second
    assert len(calls) == 1


def test_clear_rerank_model_forces_reload(monkeypatch):
    """clear 之后应重新加载，而不是复用旧实例。"""
    calls = []
    _install_fake_cross_encoder(monkeypatch, calls)

    first = hybrid.get_rerank_model()
    hybrid.clear_rerank_model()
    second = hybrid.get_rerank_model()

    assert first is not second
    assert len(calls) == 2


def test_delete_knowledge_base_removes_directory():
    """正常情况：目录应被彻底删除。"""
    assert kb_manager.create_knowledge_base('del-me', '删除测试', owner_id='u1')
    path = kb_manager._kb_path('del-me')
    assert os.path.exists(path)

    assert kb_manager.delete_knowledge_base('del-me') is True
    assert not os.path.exists(path)


def test_delete_knowledge_base_survives_locked_files(monkeypatch):
    """文件被占用时不能抛异常：下线知识库并留下墓碑目录。"""
    assert kb_manager.create_knowledge_base('locked-kb', owner_id='u1')
    original = kb_manager._kb_path('locked-kb')

    def locked(_path):
        raise PermissionError('file is locked')

    monkeypatch.setattr(kb_manager.shutil, 'rmtree', locked)

    assert kb_manager.delete_knowledge_base('locked-kb') is True

    # config.json 被移除后，列表里看不到它
    assert kb_manager.get_knowledge_base_info('locked-kb') is None
    # 原目录已改名为墓碑
    assert not os.path.exists(original)
    tombstones = [n for n in os.listdir(kb_manager.KB_ROOT) if '.deleted-' in n]
    assert len(tombstones) == 1


def test_cleanup_deleted_kbs_only_removes_marked():
    """启动清理只删带标记的目录，不误伤普通目录。"""
    marked = os.path.join(kb_manager.KB_ROOT, 'orphan-kb')
    keep = os.path.join(kb_manager.KB_ROOT, 'keep-me')
    os.makedirs(marked, exist_ok=True)
    os.makedirs(keep, exist_ok=True)
    with open(os.path.join(marked, '.deleting'), 'w', encoding='utf-8') as f:
        f.write('')

    kb_manager.cleanup_deleted_kbs()

    assert not os.path.exists(marked)
    assert os.path.exists(keep)
