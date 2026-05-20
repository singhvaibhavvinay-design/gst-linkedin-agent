
import os
import requests
import xml.etree.ElementTree as ET

# 1. Load secret keys
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")

def fetch_gst_news():
    url = "https://news.google.com/rss/search?q=GST+India&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            latest_item = root.find('.//item')
            if latest_item is not None:
                return latest_item.find('title').text, latest_item.find('link').text
    except Exception as e:
        print(f"[ERROR] Fetching news failed: {e}")
    return None, None

def ask_gemini_to_draft(title, link):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    prompt = (
        f"Analyze this GST News: '{title}'. "
        f"If it is an important update or amendment, draft an engaging LinkedIn post summarizing it. "
        f"Include hashtags and the link: {link}. "
        f"If it is not important, reply exactly with the word 'SKIP'."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, timeout=15)
        text_output = response.json()['candidates'][0]['content']['parts'][0]['text']
        return text_output.strip()
    except Exception as e:
        print(f"[ERROR] Gemini API failed: {e}")
        return "SKIP"

def get_linkedin_user_id():
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json().get("sub")
    else:
        print(f"[ERROR] Could not fetch LinkedIn user ID: {response.text}")
        return None

def post_to_linkedin(content):
    user_id = get_linkedin_user_id()
    if not user_id:
        print("[ERROR] Aborting post — no LinkedIn user ID.")
        return

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    if response.status_code == 201:
        print("[SUCCESS] Posted to LinkedIn!")
    else:
        print(f"[ERROR] LinkedIn post failed: {response.status_code} — {response.text}")

# ── Main ──────────────────────────────────────────
if not GEMINI_KEY or not LINKEDIN_TOKEN:
    print("[ERROR] Missing API keys. Check your GitHub Secrets.")
else:
    news_title, news_link = fetch_gst_news()
    if news_title:
        print(f"[AGENT LOG] Found news: {news_title}")
        draft = ask_gemini_to_draft(news_title, news_link)
        if "SKIP" not in draft:
            post_to_linkedin(draft)
        else:
            print("[AGENT LOG] News wasn't critical enough. Skipping.")
    else:
        print("[AGENT LOG] No news found.")
