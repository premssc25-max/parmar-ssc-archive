import os
import re
import time
import yt_dlp
import subprocess
import json
from datetime import datetime, timezone

# --- SETTINGS ---
CHANNEL_URL = "https://www.youtube.com/@parmarssc"
#CHANNEL_URL = "https://www.youtube.com/@LofiGirl"
BASE_PATH = "/tmp/YouTubeClasses"
RCLONE_REMOTE = "gdrive"
COOKIES_FILE = "/tmp/cookies.txt"

# --- SUBJECT DETECTION ---
def get_subject_from_title(title):
    subjects = ["Geography", "Polity", "Economy", "History", "Science", "Maths", "English", "Reasoning"]
    for s in subjects:
        if re.search(s, title, re.IGNORECASE):
            return s.capitalize()
    return "Others"

# --- SCRAPE UPCOMING STREAMS ---
def scrape_upcoming_streams():
    upcoming_streams = []
    # This part now also uses cookies
    ydl_opts = {
        'dump_single_json': True,
        'quiet': True,
        'extract_flat': 'in_playlist',
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_dict = ydl.extract_info(f"{CHANNEL_URL}/streams", download=False)
            for video in playlist_dict.get('entries', []):
                if not video.get('is_live') and video.get('release_timestamp') and video.get('release_timestamp') > time.time():
                    stream_info = {
                        "title": video.get('title', 'Unknown Title'),
                        "startTime": datetime.fromtimestamp(video.get('release_timestamp'), tz=timezone.utc).isoformat()
                    }
                    upcoming_streams.append(stream_info)
            upcoming_streams.sort(key=lambda x: x['startTime'])
    except Exception as e:
        print(f"⚠️ Could not scrape upcoming streams: {e}")
    return upcoming_streams

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

# --- DOWNLOAD LIVE VIDEO ---
def download_live(url, info):
    title = info.get("title", "Unknown Live Class")
    subject = get_subject_from_title(title)
    folder = os.path.join(BASE_PATH, subject)
    os.makedirs(folder, exist_ok=True)
    sanitized_title = re.sub(r'[\\/:*?"<>|]', "", title)
    ydl_opts = {
        "outtmpl": os.path.join(folder, f"{sanitized_title} [%(id)s].%(ext)s"),
        "format": "bestvideo[height<=720]+bestaudio[ext=m4a]/best[height<=720]",
        "live_from_start": True,
        "ignoreerrors": True,
        "no_warnings": True,
        "fragment_retries": 50,
        "retries": 20,
        "cookiefile": COOKIES_FILE
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info_dict)
    except Exception as e:
        print(f"⚠️ Download error: {e}")
        return None

# --- MAIN FUNCTION ---
def main():
    # Create cookies file from GitHub Secret
    youtube_cookies = os.environ.get('YOUTUBE_COOKIES')
    if youtube_cookies:
        with open(COOKIES_FILE, 'w') as f:
            f.write(youtube_cookies)
        print("🍪 YouTube cookies file created.")
    else:
        print("⚠️ YOUTUBE_COOKIES secret not found.")
    
    # Update schedule file
    upcoming_schedule = scrape_upcoming_streams()
    with open('schedule.json', 'w') as f: json.dump(upcoming_schedule, f, indent=2)
    print("💾 schedule.json has been updated.")
    
    live_info = None
    ydl_opts_live = {
        'quiet': True,
        'skip_download': True,
        'dump_single_json': True,
        'cookiefile': COOKIES_FILE if youtube_cookies else None
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_live) as ydl:
            info = ydl.extract_info(f"{CHANNEL_URL}/live", download=False)
            if info and info.get('is_live'):
                live_info = info
    except Exception as e:
        print("--- DETAILED ERROR ---")
        print(f"Error finding live video: {e}")
        print("--------------------")

    new_video_json = None
    live_video_id = None
    
    if live_info:
        live_video_id = live_info.get("id")
        live_url = live_info.get("webpage_url")
        print(f"✅ Live stream found: {live_info.get('title')}")
        
        file_path = download_live(live_url, live_info)
        if file_path:
            downloaded_file = None
            base_path_without_ext = os.path.splitext(file_path)[0]
            for ext in ['.mp4', '.mkv', '.webm']:
                potential_file = base_path_without_ext + ext
                if os.path.exists(potential_file):
                    downloaded_file = potential_file
                    break

            if downloaded_file:
                subject = get_subject_from_title(live_info.get("title"))
                gdrive_url = upload_to_drive(downloaded_file, subject)
                if gdrive_url:
                    new_video_data = {
                        "id": live_info.get("id"),
                        "title": live_info.get("title"),
                        "duration": time.strftime('%H:%M:%S', time.gmtime(live_info.get("duration", 0))),
                        "uploadDate": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                        "startTime": "09:00",
                        "subject": subject,
                        "gdrive_url": gdrive_url
                    }
                    new_video_json = json.dumps(new_video_data)
    else:
        print("ℹ️ No stream is currently live.")
    
    with open('live.json', 'w') as f:
        json.dump({"liveVideoId": live_video_id}, f)
    print("💾 live.json has been updated.")
        
    print(f"\n::set-output name=new_video_json::{new_video_json or 'null'}")

if __name__ == "__main__":
    main()
