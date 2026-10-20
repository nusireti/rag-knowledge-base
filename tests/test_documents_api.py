"""文档上传的安全/边界测试。"""

from fastapi.testclient import TestClient

from backend.main import app


def _auth_client(username: str, kb_name: str):
    client = TestClient(app)
    reg = client.post(
        '/api/auth/register',
        json={
            'username': username,
            'password': 'Pass12345',
            'email': '',
            'verify_code': '',
        },
    )
    token = reg.json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    client.post(
        '/api/knowledge-bases/',
        json={'name': kb_name, 'display_name': kb_name},
        headers=headers,
    )
    return client, headers


def test_upload_empty_file_rejected():
    client, headers = _auth_client('emptyuser', 'empty-kb')

    res = client.post(
        '/api/documents/upload?kb_name=empty-kb',
        files={'file': ('empty.md', b'', 'text/markdown')},
        headers=headers,
    )

    assert res.status_code == 400
    assert '空' in res.json()['detail']


def test_upload_path_traversal_rejected():
    client, headers = _auth_client('travuser', 'trav-kb')

    res = client.post(
        '/api/documents/upload?kb_name=trav-kb',
        files={'file': ('../../evil.md', b'# evil', 'text/markdown')},
        headers=headers,
    )

    assert res.status_code == 400
    assert '非法文件名' in res.json()['detail']
