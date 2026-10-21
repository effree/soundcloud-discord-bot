import os
import json
import time
import requests

CLIENT_ID = os.getenv("SOUNDCLOUD_CLIENT_ID")
CLIENT_SECRET = os.getenv("SOUNDCLOUD_CLIENT_SECRET")
INITIAL_REFRESH_TOKEN = os.getenv("SOUNDCLOUD_REFRESH_TOKEN")
USER_ID = os.getenv("SOUNDCLOUD_USER_ID")
WEBHOOK_WIPS = os.getenv("DISCORD_WEBHOOK_WIPS")
WEBHOOK_PUBLISHED = os.getenv("DISCORD_WEBHOOK_PUBLISHED")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_MINUTES", 10)) * 60

STATE_FILE = "/app/data/state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state_data):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state_data, f)

def get_fresh_access_token():
    state = load_state()
    refresh_token = state.get("refresh_token") or INITIAL_REFRESH_TOKEN

    if not refresh_token:
        print("Error: No refresh token available!")
        return None

    token_url = "https://secure.soundcloud.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token
    }
    headers = {"Accept": "application/json"}

    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code != 200:
        print(f"Failed to refresh access token: {response.status_code} - {response.text}")
        return None

    token_data = response.json()
    new_access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token")

    # Save the new single-use refresh token for the next cycle
    if new_refresh_token:
        state["refresh_token"] = new_refresh_token
        save_state(state)

    return new_access_token

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
    
    access_token = get_fresh_access_token()
    if not access_token:
        return

    state = load_state()
    posted_tracks = state.get("posted_tracks", [])

    # Use Bearer scheme for official OAuth 2.1 tokens
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json; charset=utf-8"
    }
    
    # Fetch user tracks via SoundCloud API v2 (removed redundant client_id from query)
    url = f"https://api.soundcloud.com/users/{USER_ID}/tracks?limit=5"
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
        if len(posted_tracks) > 100:
            posted_tracks.pop(0)
            
        state["posted_tracks"] = posted_tracks
        save_state(state)

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