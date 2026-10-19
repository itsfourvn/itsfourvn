import os
import requests

GITHUB_ACTOR = os.getenv("GITHUB_ACTOR")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

def get_recent_events():
    url = f"https://api.github.com/users/{GITHUB_ACTOR}/events/public"
    headers = {"Authorization": f"token {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Lỗi khi gọi GitHub API: {response.status_code}")
        return []
    
    events = response.json()
    activity_lines = []
    count = 0
    
    for event in events:
        if count >= 25:  # Lấy tối đa 25 hoạt động
            break
            
        event_type = event.get("type")
        repo_name = event.get("repo", {}).get("name")
        repo_url = f"https://github.com/{repo_name}"
        
        if event_type == "PushEvent":
            payload = event.get("payload", {})
            commits = payload.get("commits", [])
            ref = payload.get("ref", "refs/heads/main")
            branch = ref.split("/")[-1]
            
            for commit in commits:
                if count >= 25:
                    break
                commit_sha = commit.get("sha")[:7]
                commit_url = f"{repo_url}/commit/{commit.get('sha')}"
                
                line = f"{count + 1}. 📦 Pushed [`{commit_sha}`]({commit_url}) to [`{branch}`]({repo_url}/tree/{branch}) in [`{repo_name}`]({repo_url})"
                activity_lines.append(line)
                count += 1
                
        elif event_type == "CreateEvent":
            payload = event.get("payload", {})
            ref_type = payload.get("ref_type")
            ref = payload.get("ref", "")
            
            if ref_type == "branch":
                line = f"{count + 1}. 🆕 Created branch {ref} in [`{repo_name}`]({repo_url})"
                activity_lines.append(line)
                count += 1

    return activity_lines

def update_readme(new_activities):
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print("Không tìm thấy tệp README.md!")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!--START_SECTION:activity-->"
    end_marker = "<!--END_SECTION:activity-->"
    
    if start_marker in content and end_marker in content:
        parts = content.split(start_marker)
        before = parts[0] + start_marker + "\n"
        after = parts[1].split(end_marker)[1]
        
        new_activity_block = "\n".join(new_activities) + "\n"
        
        new_content = before + new_activity_block + end_marker + after

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Đã cập nhật thành công Recent activity vào README.md!")
    else:
        print("Không tìm thấy thẻ START/END activity trong README.md")

if __name__ == "__main__":
    activities = get_recent_events()
    if activities:
        update_readme(activities)
