import os
import re
import time
import requests
import subprocess
import json
from datetime import datetime, timezone
import yt_dlp # Moved import to the top

# --- SETTINGS ---
#CHANNEL_ID = "UC4h_7L2n2aC_j-gN-V_f_xw" # Parmar SSC Channel ID
CHANNEL_ID = "UCSJ4gkVC6NrvII8umztf0Ow" # Lo-fi Girl Channel ID
BASE_PATH = "/tmp/YouTubeClasses"
RCLONE_REMOTE = "gdrive"
API_KEY = os.environ.get('YOUTUBE_API_KEY')
YOUTUBE_COOKIES = os.environ.get('YOUTUBE_COOKIES')
COOKIES_FILE = "/tmp/cookies.txt"

# --- SUBJECT DETECTION ---
def get_subject_from_title(title):
    subjects = ["Geography", "Polity", "Economy", "History", "Science", "Maths", "English", "Reasoning"]
    for s in subjects:
        if re.search(s, title, re.IGNORECASE):
            return s.capitalize()
    return "Others"

# --- UPLOAD TO GOOGLE DRIVE ---
def upload_to_drive(local_path, subject):
    if not os.path.exists(local_path):
        return None
    remote_path_folder = f"{RCLONE_REMOTE}:Parmar_SSC_Classes/{subject}"
    file_name = os.path.basename(local_path)
    try:
        subprocess.run(["rclone", "mkdir", remote_path_folder], check=True, capture_output=True, text=True)
        print(f"☁️ Uploading '{file_name}' to Google Drive...")
        subprocess.run(["rclone", "move", local_path, remote_path_folder, "--progress", "--drive-chunk-size", "64M"], check=True, capture_output=True, text=True)
        print("✅ Upload successful.")
        result = subprocess.run(["rclone", "lsjson", f"{remote_path_folder}/{file_name}"], check=True, capture_output=True, text=True)
        file_info = json.loads(result.stdout)
        file_id = file_info[0]['ID']
        return f"https://drive.google.com/file/d/{file_id}/preview" 
    except Exception as e:
        print(f"⚠️ An error occurred during upload: {e}")
        return None

# --- DOWNLOAD LIVE VIDEO (NOW USES COOKIES) ---
def download_live(url, info):
    title = info.get("title", "Unknown Live Class")
    subject = get_subject_from_title(title)
    folder = os.path.join(BASE_PATH, subject)
    os.makedirs(folder, exist_ok=True)
    sanitized_title = re.sub(r'[\\/:*?"<>|]', "", title)
    ydl_opts = {
        "outtmpl": os.path.join(folder, f"{sanitized_title} [%(id)s].%(ext)s"),
        "format": "bestvideo[height<=720]+bestaudio[ext=m4a]/best[height<=720]",
        "live_from_start": True, "ignoreerrors": True, "no_warnings": True,
        "fragment_retries": 50, "retries": 20,
        "cookiefile": COOKIES_FILE if YOUTUBE_COOKIES else None # Use cookies for downloading
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            downloaded_file = None
            base_path_without_ext = os.path.splitext(file_path)[0]
            for ext in ['.mp4', '.mkv', '.webm']:
                potential_file = base_path_without_ext + ext
                if os.path.exists(potential_file):
                    downloaded_file = potential_file
                    break
            return downloaded_file
    except Exception as e:
        print(f"⚠️ Download error: {e}")
        return None

# --- MAIN FUNCTION ---
def main():
    if YOUTUBE_COOKIES:
        with open(COOKIES_FILE, 'w') as f:
            f.write(YOUTUBE_COOKIES)
        print("🍪 YouTube cookies file created.")

    if not API_KEY:
        print("🔴 ERROR: YOUTUBE_API_KEY secret not found.")
        # ... (rest of the error handling)
        with open('live.json', 'w') as f: json.dump({"liveVideoId": None}, f)
        with open('schedule.json', 'w') as f: json.dump([], f)
        return

    live_info = None
    upcoming_schedule = []

    try:
        # ... (API search logic is unchanged)
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&eventType=live&type=video&key={API_KEY}"
        response = requests.get(search_url).json()
        if response.get('items'):
            live_item = response['items'][0]
            live_info = {
                "id": live_item['id']['videoId'],
                "title": live_item['snippet']['title'],
                "webpage_url": f"https://www.youtube.com/watch?v={live_item['id']['videoId']}"
            }
        
        search_url_upcoming = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&eventType=upcoming&type=video&key={API_KEY}"
        response_upcoming = requests.get(search_url_upcoming).json()
        if response_upcoming.get('items'):
            for item in response_upcoming['items']:
                upcoming_schedule.append({
                    "title": item['snippet']['title'],
                    "startTime": item['snippet']['publishTime']
                })
    except Exception as e:
        print(f"--- API ERROR --- \n {e} \n-----------------")

    with open('schedule.json', 'w') as f: json.dump(upcoming_schedule, f, indent=2)
    print("💾 schedule.json has been updated via API.")

    new_video_json = None
    live_video_id = None
    
    if live_info:
        live_video_id = live_info.get("id")
        print(f"✅ Live stream found via API: {live_info.get('title')}")
        
        file_path = download_live(live_info.get("webpage_url"), live_info)
        if file_path:
            subject = get_subject_from_title(live_info.get("title"))
            gdrive_url = upload_to_drive(file_path, subject)
            if gdrive_url:
                new_video_data = {
                    "id": live_info.get("id"), "title": live_info.get("title"),
                    "duration": "N/A", "uploadDate": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                    "startTime": "09:00", "subject": subject, "gdrive_url": gdrive_url
                }
                new_video_json = json.dumps(new_video_data)
    else:
        print("ℹ️ No stream is currently live.")
    
    with open('live.json', 'w') as f: json.dump({"liveVideoId": live_video_id}, f)
    print("💾 live.json has been updated via API.")
        
    if new_video_json:
        # This part is for the deprecated set-output, which is fine to leave as is
        print(f"\n::set-output name=new_video_json::{new_video_json}")

if __name__ == "__main__":
    main()
