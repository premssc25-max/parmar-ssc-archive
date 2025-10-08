import os
import re
import time
import yt_dlp
import requests
import subprocess
import json
from datetime import datetime, timezone

# ---------- SETTINGS ----------
CHANNEL_STREAMS_URL = "https://www.youtube.com/@parmarssc/streams"
BASE_PATH = "/tmp/YouTubeClasses"
RCLONE_REMOTE = "gdrive"

# ---------- SUBJECT DETECTION ----------
def get_subject_from_title(title):
    subjects = ["Geography", "Polity", "Economy", "History", "Science", "Maths", "English", "Reasoning"]
    for s in subjects:
        if re.search(s, title, re.IGNORECASE):
            return s.capitalize()
    return "Others"

# ---------- SCRAPE UPCOMING STREAMS ----------
def scrape_upcoming_streams():
    upcoming_streams = []
    try:
        ydl_opts = {'dump_single_json': True, 'quiet': True, 'extract_flat': 'in_playlist'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_dict = ydl.extract_info(CHANNEL_STREAMS_URL, download=False)
            for video in playlist_dict.get('entries', []):
                if not video.get('is_live') and video.get('release_timestamp') and video.get('release_timestamp') > time.time():
                    stream_info = {
                        "title": video.get('title', 'Unknown Title'),
                        "startTime": datetime.fromtimestamp(video.get('release_timestamp'), tz=timezone.utc).isoformat()
                    }
                    upcoming_streams.append(stream_info)
            upcoming_streams.sort(key=lambda x: x['startTime'])
            return upcoming_streams
    except Exception: return []

# ---------- FIND CURRENT LIVE STREAM ----------
def resolve_current_live_url():
    try:
        live_page_url = CHANNEL_STREAMS_URL.replace("/streams", "/live")
        r = requests.get(live_page_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
        match = re.search(r'"videoId":"([\w-]{11})"', r.text)
        if match: return f"https://www.youtube.com/watch?v={match.group(1)}"
    except Exception: return None

def fetch_live_info(url):
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "dump_single_json": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get("is_live"): return info
    except Exception: return None

# --- UPLOAD TO GOOGLE DRIVE (rclone version) ---
def upload_to_drive(local_path, subject):
    if not os.path.exists(local_path):
        return None
    
    remote_path_folder = f"{RCLONE_REMOTE}:Parmar_SSC_Classes/{subject}"
    file_name = os.path.basename(local_path)
    remote_path_full = f"{remote_path_folder}/{file_name}"

    try:
        subprocess.run(["rclone", "mkdir", remote_path_folder], check=True, capture_output=True, text=True)
        print(f"☁️ Uploading '{file_name}' to Google Drive...")
        subprocess.run(["rclone", "move", local_path, remote_path_folder, "--progress", "--drive-chunk-size", "64M"], check=True, capture_output=True, text=True)
        print("✅ Upload successful.")
        
        result = subprocess.run(["rclone", "lsjson", remote_path_full], check=True, capture_output=True, text=True)
        file_info = json.loads(result.stdout)
        file_id = file_info[0]['ID']
        
        return f"https://drive.google.com/file/d/{file_id}/preview" # Return full preview URL

    except Exception as e:
        print(f"⚠️ An error occurred during upload: {e}")
        return None

def download_live(url, info):
    title = info.get("title", "Unknown Live Class")
    subject = get_subject_from_title(title)
    folder = os.path.join(BASE_PATH, subject)
    os.makedirs(folder, exist_ok=True)
    sanitized_title = re.sub(r'[\\/:*?"<>|]', "", title)
    ydl_opts = {"outtmpl": os.path.join(folder, f"{sanitized_title} [%(id)s].%(ext)s"), "format": "bestvideo[height<=720]+bestaudio[ext=m4a]/best[height<=720]", "live_from_start": True, "ignoreerrors": True, "no_warnings": True, "fragment_retries": 50, "retries": 20}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            base_path_without_ext = os.path.splitext(file_path)[0]
            for ext in ['.mp4', '.mkv', '.webm']:
                if os.path.exists(base_path_without_ext + ext):
                    file_path = base_path_without_ext + ext; break
            else: return None, None, None
            return file_path, subject, info
    except Exception as e:
        print(f"⚠️ Download error: {e}")
        return None, None, None

def main():
    upcoming_schedule = scrape_upcoming_streams()
    with open('schedule.json', 'w') as f: json.dump(upcoming_schedule, f, indent=2)
    print("💾 schedule.json has been updated.")
    
    new_video_json = None
    live_video_id = None # <-- NAYI LINE
    
    live_url = resolve_current_live_url()
    if live_url:
        info = fetch_live_info(live_url)
        if info:
            live_video_id = info.get("id") # <-- NAYI LINE
            file_path, subject, video_info = download_live(live_url, info)
            if file_path and subject and video_info:
                gdrive_url = upload_to_drive(file_path, subject)
                if gdrive_url:
                    new_video_data = {"id": video_info.get("id"),"title": video_info.get("title"),"duration": time.strftime('%H:%M:%S', time.gmtime(video_info.get("duration", 0))),"uploadDate": datetime.now().strftime('%Y-%m-%d'),"startTime": "09:00","subject": subject,"gdrive_url": gdrive_url}
                    new_video_json = json.dumps(new_video_data)
    else:
        print("ℹ️ No stream is currently live.")
    
    # --- NAYA PART START ---
    # live.json file ko update karein
    live_data = {"liveVideoId": live_video_id}
    with open('live.json', 'w') as f:
        json.dump(live_data, f)
    print("💾 live.json has been updated.")
    # --- NAYA PART END ---
        
    print(f"\n::set-output name=new_video_json::{new_video_json or 'null'}")

if __name__ == "__main__":
    main()
