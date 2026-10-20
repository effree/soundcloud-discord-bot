import os
import json
import time
import requests

# Load Environment Variables
CLIENT_ID = os.getenv("SOUNDCLOUD_CLIENT_ID")
OAUTH_TOKEN = os.getenv("SOUNDCLOUD_OAUTH_TOKEN")
USER_ID = os.getenv("SOUNDCLOUD_USER_ID")
WEBHOOK_WIPS = os.getenv("DISCORD_WEBHOOK_WIPS")
WEBHOOK_PUBLISHED = os.getenv("DISCORD_WEBHOOK_PUBLISHED")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_MINUTES", 10)) * 60

STATE_FILE = "/app/data/posted_tracks.json"

def load_posted_tracks():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_posted_tracks(tracks):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(tracks, f)

def send_to_discord(webhook_url, message):
    if not webhook_url:
        print("Webhook URL not set, skipping message.")
        return
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload)
    if response.status_code not in [200, 204]:
        print(f"Failed to send to Discord: {response.status_code}, {response.text}")

def check_soundcloud():
    print("Checking SoundCloud for new tracks...")
    posted_tracks = load_posted_tracks()

    headers = {
        "Authorization": f"OAuth {OAUTH_TOKEN}",
        "Accept": "application/json; charset=utf-8"
    }
    
    # Fetch user tracks via SoundCloud API v2
    url = f"https://api.soundcloud.com/users/{USER_ID}/tracks?client_id={CLIENT_ID}&limit=5"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching SoundCloud tracks: {response.status_code} - {response.text}")
        return

    data = response.json()
    tracks = data.get("collection", [])

    # Process oldest to newest
    for track in reversed(tracks):
        track_id = str(track.get("id"))
        
        if track_id in posted_tracks:
            continue

        title = track.get("title")
        sharing = track.get("sharing") # 'private' or 'public'
        permalink_url = track.get("permalink_url")

        if sharing == "private":
            secret_token = track.get("secret_token")
            # Construct the unique private shareable link format
            if secret_token:
                track_url = f"{permalink_url}/s-{secret_token}"
            else:
                track_url = permalink_url
            
            message = f"🎵 **New Private WIP Posted!**\n> **{title}**\nListen here: {track_url}"
            print(f"Found new private track: {title}")
            send_to_discord(WEBHOOK_WIPS, message)
            
        else:
            message = f"🚀 **New Track Published!**\n> **{title}**\nListen here: {permalink_url}"
            print(f"Found new public track: {title}")
            send_to_discord(WEBHOOK_PUBLISHED, message)

        posted_tracks.append(track_id)
        # Keep track list trimmed to last 100 entries
        if len(posted_tracks) > 100:
            posted_tracks.pop(0)
            
        save_posted_tracks(posted_tracks)

def main():
    print("SoundCloud-to-Discord Bot started.")
    while True:
        try:
            check_soundcloud()
        except Exception as e:
            print(f"Error in execution loop: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()