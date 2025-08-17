# upload_to_gdrive.py
import os, sys, json, base64
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def normalize_json_string(s: str) -> str:
    """清洗常见粘贴问题：去掉```代码块、首尾引号、花引号、BOM等；若是base64也尝试解码"""
    if not s:
        return s
    t = s.strip()
    # 去掉 Markdown 代码块包裹
    if t.startswith("```"):
        lines = [ln for ln in t.splitlines()]
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    # 去掉首尾额外一层引号
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    # 替换花引号为直引号
    t = (t.replace("“", '"').replace("”", '"')
           .replace("‘", "'").replace("’", "'"))
    # 尝试直接解析；不行再试base64
    try:
        json.loads(t)
        return t
    except Exception:
        pass
    try:
        tb = base64.b64decode(t, validate=True).decode("utf-8", "replace").strip()
        json.loads(tb)  # 确认可解析
        return tb
    except Exception:
        return t  # 让上层给出清晰错误

def load_service_account_info():
    """
    优先用环境变量中的 Secret，自动清洗；失败再尝试读取本地 creds.json。
    成功后把规范化JSON写回 creds.json，供 Google 客户端读取。
    """
    raw = os.environ.get("DRIVE_CREDENTIALS_JSON", "")
    if raw:
        text = normalize_json_string(raw)
        try:
            info = json.loads(text)
            with open("creds.json", "w", encoding="utf-8") as f:
                json.dump(info, f)  # 规范化写回
            return info
        except Exception as e:
            print("❌ 无法解析环境变量 DRIVE_CREDENTIALS_JSON 为合法 JSON。")
            raise

    # 回退：读取已经存在的文件（不推荐，但保底）
    with open("creds.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    return info

def main():
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    file_path = os.environ.get("LATEST_CSV")
    if not folder_id:
        print("❌ 缺少环境变量 GDRIVE_FOLDER_ID"); sys.exit(1)
    if not file_path or not os.path.exists(file_path):
        print(f"❌ 找不到要上传的文件：{file_path}"); sys.exit(1)

    info = load_service_account_info()
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)

    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    file_name = os.path.basename(file_path)
    print(f"📤 准备上传：{file_name}")

    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype="text/csv", resumable=True)

    res = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink, webContentLink"
    ).execute()

    print("✅ 上传成功")
    print(f"   • fileId: {res.get('id')}")
    print(f"   • 查看链接: {res.get('webViewLink')}")
    print(f"   • 直接下载: {res.get('webContentLink')}")

if __name__ == "__main__":
    main()
