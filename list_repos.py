import requests, os
token = os.environ.get("GITHUB_TOKEN", "")
headers = {"Authorization": f"token {token}"} if token else {}
r = requests.get("https://api.github.com/users/nusireti/repos?per_page=50", headers=headers)
for repo in r.json():
    print(f"  [{repo['name']}] {repo['description'] or '无描述'}")
