"""安全回归测试

每条安全修复都对应这里的用例：修复一旦被改回去，测试立刻会红。

覆盖三类：
1. 路径穿越 —— kb_name / filename / conv_id 都来自用户输入
2. 多租户隔离 —— 资源访问必须带 owner 归属
3. API 层 —— 越权返回 404、非法输入返回 400、未登录返回 401
"""

import os

import pytest


# ==================== 1. 路径穿越 ====================

class TestKbNameValidation:
    @pytest.mark.parametrize("bad", [
        "../../evil", "..", ".", "a/b", "a\\b", "C:", "x" * 65, "kb name", "", None,
    ])
    def test_reject_bad_kb_name(self, bad):
        from kb_manager import validate_kb_name
        with pytest.raises(ValueError):
            validate_kb_name(bad)

    @pytest.mark.parametrize("good", ["kb", "my-kb", "my_kb", "KB123"])
    def test_accept_good_kb_name(self, good):
        from kb_manager import validate_kb_name
        assert validate_kb_name(good) == good


class TestSafeDocPath:
    @pytest.mark.parametrize("evil", [
        "../../x", "..\\..\\x", "sub/dir/x.txt", "C:\\Windows\\x.txt",
        "../../../../etc/passwd", "....//....//x",
    ])
    def test_traversal_cannot_escape(self, evil):
        """无论怎么写，拼出来的路径都必须落在知识库文档目录里"""
        from kb_manager import create_knowledge_base, safe_doc_path, get_documents_dir

        create_knowledge_base("kb1", owner_id="u1")
        docs_dir = os.path.abspath(get_documents_dir("kb1"))
        full = os.path.abspath(safe_doc_path("kb1", evil))
        assert full.startswith(docs_dir + os.sep), f"{evil!r} 逃出了文档目录: {full}"

    @pytest.mark.parametrize("bad", ["..", "", ".hidden", "/", "\\"])
    def test_reject_empty_or_hidden(self, bad):
        from kb_manager import create_knowledge_base, safe_doc_path

        create_knowledge_base("kb1", owner_id="u1")
        with pytest.raises(ValueError):
            safe_doc_path("kb1", bad)


class TestDeleteCannotTouchOutside:
    def test_delete_document_keeps_outside_file(self, tmp_path):
        """知识库目录外的文件，用任何写法都不该被删掉"""
        from kb_manager import create_knowledge_base, delete_document

        create_knowledge_base("kb1", owner_id="u1")
        outside = tmp_path / "secret.txt"
        outside.write_text("机密内容", encoding="utf-8")

        for evil in ["../secret.txt", "..\\secret.txt", "../../secret.txt"]:
            assert delete_document("kb1", evil) is False
        assert outside.exists(), "❌ 知识库外的文件被删掉了"

    def test_delete_kb_rejects_traversal(self, tmp_path):
        """delete_knowledge_base 内部是 rmtree，穿越写法必须被拦下"""
        from kb_manager import delete_knowledge_base

        important = tmp_path / "important_dir"
        important.mkdir()
        (important / "data.txt").write_text("重要数据", encoding="utf-8")

        with pytest.raises(ValueError):
            delete_knowledge_base("../important_dir")
        assert important.exists(), "❌ 知识库外的目录被 rmtree 了"

    def test_preview_and_list_reject_traversal(self):
        from kb_manager import preview_document, get_documents

        with pytest.raises(ValueError):
            preview_document("../../", "x.txt")
        with pytest.raises(ValueError):
            get_documents("../../")


class TestConvIdValidation:
    @pytest.mark.parametrize("bad", ["../../x", "a/b", "..", "", "x.json", "a\\b"])
    def test_reject_bad_conv_id(self, bad):
        from chat_history import validate_conv_id
        with pytest.raises(ValueError):
            validate_conv_id(bad)

    def test_conversation_path_cannot_escape(self, tmp_path):
        """conv_id 直接来自 URL 路径，同样不能穿越"""
        import chat_history

        outside = tmp_path / "secret.json"
        outside.write_text('{"id":"secret"}', encoding="utf-8")

        with pytest.raises(ValueError):
            chat_history.load_conversation("../secret")
        assert outside.exists(), "❌ 对话目录外的文件被读/删了"


# ==================== 2. 多租户隔离 ====================

class TestKnowledgeBaseIsolation:
    def test_list_filtered_by_owner(self):
        from kb_manager import create_knowledge_base, list_knowledge_bases

        create_knowledge_base("alice-kb", owner_id="alice")
        create_knowledge_base("bob-kb", owner_id="bob")

        assert {k["name"] for k in list_knowledge_bases(owner_id="alice")} == {"alice-kb"}
        assert {k["name"] for k in list_knowledge_bases(owner_id="bob")} == {"bob-kb"}
        # 不传 owner_id 时不筛选（内部/迁移用）
        assert len(list_knowledge_bases()) == 2

    def test_kb_belongs_to(self):
        from kb_manager import create_knowledge_base, kb_belongs_to

        create_knowledge_base("alice-kb", owner_id="alice")
        assert kb_belongs_to("alice-kb", "alice") is True
        assert kb_belongs_to("alice-kb", "bob") is False
        assert kb_belongs_to("not-exist", "alice") is False
        assert kb_belongs_to("../../etc", "alice") is False

    def test_name_collision_returns_false_and_keeps_owner(self):
        """
        知识库名就是目录名，全局唯一 —— 重名时必须返回 False，
        而且不能篡改原归属。

        这是"新用户被带进别人 default 库"那个漏洞的根因：
        create 静默失败后，调用方若无脑 switch，就进了别人的库。
        """
        from kb_manager import create_knowledge_base, get_knowledge_base_info

        assert create_knowledge_base("shared", owner_id="alice") is True
        assert create_knowledge_base("shared", owner_id="bob") is False
        assert get_knowledge_base_info("shared")["owner_id"] == "alice", "原归属被篡改了"

    def test_ownerless_kb_invisible_until_migrated(self):
        """历史数据没有 owner_id，迁移前谁也看不到，迁移后归指定用户"""
        from kb_manager import (
            create_knowledge_base, list_knowledge_bases, migrate_ownerless_kbs,
        )

        create_knowledge_base("legacy-kb", owner_id="")
        assert list_knowledge_bases(owner_id="alice") == []

        assert migrate_ownerless_kbs("alice") == 1
        assert {k["name"] for k in list_knowledge_bases(owner_id="alice")} == {"legacy-kb"}


class TestConversationIsolation:
    def test_conversation_isolation(self):
        import chat_history as ch

        cid_alice = ch.create_conversation(owner_id="alice")
        ch.create_conversation(owner_id="bob")

        assert {c["id"] for c in ch.list_conversations(owner_id="alice")} == {cid_alice}
        # 别人的对话读不到
        assert ch.load_conversation(cid_alice, owner_id="bob") is None
        # 别人的对话删不掉
        assert ch.delete_conversation(cid_alice, owner_id="bob") is False
        assert ch.load_conversation(cid_alice, owner_id="alice") is not None
        # 导出也拿不到
        assert ch.export_markdown(cid_alice, owner_id="bob") is None

    def test_migrate_ownerless_conversations(self):
        import chat_history as ch

        cid = ch.create_conversation(owner_id="")
        assert ch.list_conversations(owner_id="alice") == []

        assert ch.migrate_ownerless_conversations("alice") == 1
        assert {c["id"] for c in ch.list_conversations(owner_id="alice")} == {cid}


# ==================== 2.5 XSS ====================

# 注入 HTML 时允许直接插值的"内部变量"白名单。
# 这些都是程序自己算出来的，不含用户输入；有新变量要加进来必须想清楚来源。
_SAFE_INTERPOLATIONS = {
    "doc_count",     # len() 的结果，数字
    "file_count",    # 同上
    "total_tokens",  # 计数器，数字
    "pct",           # min() 算出的百分比，数字
    "badge_cls",     # 代码里写死的类名
    "badge_style",   # 代码里写死的样式串
    "act_cls",       # 代码里写死的类名
    "display",       # 构造时已对 answer/tag 分别 esc（见 ui.py 中 display 赋值处）
}


class TestNoUnescapedHtml:
    """
    静态检查：ui.py 里所有 unsafe_allow_html 的插值都必须转义

    这是给 XSS 修复上的一道锁 —— 单靠人眼 review 迟早会漏，
    新增一处未转义的插值，这个测试立刻会红。
    """

    def test_all_interpolations_escaped(self):
        import ast
        import io
        import os

        ui_path = os.path.join(os.path.dirname(__file__), "..", "app", "web", "ui.py")
        tree = ast.parse(io.open(ui_path, encoding="utf-8").read())

        def is_unsafe_html_call(node):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                return False
            if node.func.attr not in ("markdown", "caption"):
                return False
            return any(
                k.arg == "unsafe_allow_html" and getattr(k.value, "value", False) is True
                for k in node.keywords
            )

        def is_constant_expr(node):
            """纯常量，或"常量 if 条件 else 常量"—— 不可能携带用户输入"""
            if isinstance(node, ast.Constant):
                return True
            if isinstance(node, ast.IfExp):
                return is_constant_expr(node.body) and is_constant_expr(node.orelse)
            return False

        offenders = []
        for node in ast.walk(tree):
            if not is_unsafe_html_call(node):
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.JoinedStr):
                    continue
                for value in sub.values:
                    if not isinstance(value, ast.FormattedValue):
                        continue
                    expr = ast.unparse(value.value)
                    if expr.startswith("esc("):
                        continue
                    if is_constant_expr(value.value):
                        continue
                    if expr in _SAFE_INTERPOLATIONS:
                        continue
                    offenders.append(f"L{value.lineno}: {expr}")

        assert not offenders, (
            "以下插值进了 unsafe_allow_html 但没有转义，存在 XSS 风险：\n  "
            + "\n  ".join(offenders)
        )


class TestHtmlEscaping:
    def test_escape_neutralizes_script_payload(self):
        from html import escape

        payload = '<img src=x onerror="alert(1)">'
        out = escape(payload)
        # 尖括号被转义后不再是标签，但内容仍可见（不是粗暴删除）
        assert "<img" not in out
        assert "&lt;img" in out

    def test_escape_neutralizes_script_tag(self):
        from html import escape

        out = escape("<script>steal()</script>")
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_dangerous_filename_is_escaped_when_rendered(self):
        """
        含 HTML 特殊字符的文件名，渲染前必须转义

        注意：Windows 禁止文件名出现 < >，所以这里用 & 和单引号构造。
        部署到 Linux 时文件名可以含 < >，转义逻辑同样要挡住（见下一个用例）。
        """
        from html import escape
        from kb_manager import save_uploaded_file, create_knowledge_base, get_documents

        create_knowledge_base("kb1", owner_id="u1")
        evil_name = "a&b' onmouseover='x.txt"
        save_uploaded_file("kb1", evil_name, "内容".encode("utf-8"))

        stored = get_documents("kb1")[0]["name"]
        assert "'" in stored, "原始文件名里的引号应当被保留存储"
        rendered = escape(stored)
        assert "&amp;" in rendered, "& 未被转义"
        assert "&#x27;" in rendered, "单引号未被转义"

    def test_escape_handles_linux_style_filename(self):
        """Linux 下文件名可以含尖括号，转义后不能再是标签"""
        from html import escape

        rendered = escape("<img src=x onerror=alert(1)>.txt")
        assert "<img" not in rendered
        assert "&lt;img" in rendered


# ==================== 3. API 层 ====================

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


def _auth(user_id: str) -> dict:
    """给指定 user_id 造一个合法 token（validate_session 只校验签名与有效期）"""
    from app.auth import create_session
    return {"Authorization": f"Bearer {create_session(user_id)}"}


class TestApiAuth:
    def test_missing_header_returns_401(self, client):
        assert client.get("/api/knowledge-bases/").status_code == 401

    def test_bad_token_returns_401(self, client):
        # HTTP header 只能是 ASCII，这里用伪造的签名值
        r = client.get("/api/knowledge-bases/",
                       headers={"Authorization": "Bearer v2.forged.token.value.deadbeef"})
        assert r.status_code == 401


class TestApiTenantIsolation:
    def test_list_returns_only_own(self, client):
        from kb_manager import create_knowledge_base

        create_knowledge_base("alice-kb", owner_id="alice")
        create_knowledge_base("bob-kb", owner_id="bob")

        r = client.get("/api/knowledge-bases/", headers=_auth("bob"))
        assert r.status_code == 200
        assert [k["name"] for k in r.json()["data"]] == ["bob-kb"]

    def test_cannot_read_others_kb(self, client):
        from kb_manager import create_knowledge_base

        create_knowledge_base("alice-kb", owner_id="alice")
        r = client.get("/api/knowledge-bases/alice-kb", headers=_auth("bob"))
        assert r.status_code == 404

    def test_cannot_delete_others_kb(self, client):
        from kb_manager import create_knowledge_base, get_knowledge_base_info

        create_knowledge_base("alice-kb", owner_id="alice")
        r = client.delete("/api/knowledge-bases/alice-kb", headers=_auth("bob"))
        assert r.status_code == 404
        assert get_knowledge_base_info("alice-kb") is not None, "❌ 别人的知识库被删了"

    def test_own_kb_delete_ok(self, client):
        from kb_manager import create_knowledge_base, get_knowledge_base_info

        create_knowledge_base("bob-kb", owner_id="bob")
        r = client.delete("/api/knowledge-bases/bob-kb", headers=_auth("bob"))
        assert r.status_code == 200
        assert get_knowledge_base_info("bob-kb") is None

    def test_cannot_list_others_documents(self, client):
        from kb_manager import create_knowledge_base

        create_knowledge_base("alice-kb", owner_id="alice")
        r = client.get("/api/documents/", params={"kb_name": "alice-kb"}, headers=_auth("bob"))
        assert r.status_code == 404

    def test_conversations_isolated(self, client):
        import chat_history as ch

        cid = ch.create_conversation(owner_id="alice")

        r = client.get("/api/chat/conversations", headers=_auth("bob"))
        assert r.json()["data"] == []

        assert client.get(f"/api/chat/conversations/{cid}", headers=_auth("bob")).status_code == 404
        assert client.delete(f"/api/chat/conversations/{cid}", headers=_auth("bob")).status_code == 404
        assert ch.load_conversation(cid, owner_id="alice") is not None


class TestApiInputValidation:
    @pytest.mark.parametrize("evil_kb", ["../../", "..", "a/b", "C:"])
    def test_traversal_kb_name_rejected(self, client, evil_kb):
        r = client.get("/api/documents/", params={"kb_name": evil_kb}, headers=_auth("bob"))
        assert r.status_code in (400, 404, 422), f"{evil_kb!r} 没被拒绝: {r.status_code}"

    def test_traversal_conv_id_rejected(self, client):
        r = client.get("/api/chat/conversations/..%2F..%2Fetc", headers=_auth("bob"))
        assert r.status_code in (400, 404)

    def test_ask_with_others_kb_rejected(self, client):
        from kb_manager import create_knowledge_base

        create_knowledge_base("alice-kb", owner_id="alice")
        r = client.post(
            "/api/chat/ask",
            json={"question": "你好", "kb_name": "alice-kb", "mode": "rag"},
            headers=_auth("bob"),
        )
        assert r.status_code == 404, "❌ 用别人的知识库提问没被拦住"
