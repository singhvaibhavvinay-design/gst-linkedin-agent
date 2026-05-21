import os
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import time

# ── 1. Load secret keys ───────────────────────────────────────────────────────
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY")
LINKEDIN_TOKEN   = os.environ.get("LINKEDIN_ACCESS_TOKEN")

# ── 2. Fetch GST News ─────────────────────────────────────────────────────────
def fetch_gst_news():
    url = "https://news.google.com/rss/search?q=GST+India+tax+amendment+council&hl=en-IN&gl=IN&ceid=IN:en"
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

# ── 3. Ask Groq to Draft LinkedIn Post ───────────────────────────────────────
def ask_groq_to_draft(title, link):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Analyze this GST News: '{title}'. "
        f"If it is an important update or amendment for Indian businesses, "
        f"draft an engaging LinkedIn post summarizing it. "
        f"Include relevant hashtags like #GST #Tax #India #Business and the link: {link}. "
        f"Keep it under 300 words with bullet points. "
        f"If it is NOT important, reply exactly with the single word 'SKIP'."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert GST tax consultant in India. "
                    "You write clear, professional, and engaging LinkedIn posts "
                    "for Indian businesses about GST updates."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        result = response.json()
        if 'choices' not in result:
            print(f"[ERROR] Groq unexpected response: {result}")
            return "SKIP"
        text_output = result['choices'][0]['message']['content']
        return text_output.strip()
    except Exception as e:
        print(f"[ERROR] Groq API failed: {e}")
        return "SKIP"

# ── 4. Generate Image using Pollinations (FREE, no API key needed) ────────────
def generate_post_image(news_title):
    try:
        # Build a clean prompt for a professional GST infographic
        image_prompt = (
            f"Professional infographic about GST tax update India, "
            f"{news_title}, modern business design, blue and white colors, "
            f"clean layout, no people"
        )
        encoded_prompt = urllib.parse.quote(image_prompt)
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=1200&height=628&nologo=true&seed=42"
        )

        print(f"[AGENT LOG] Generating image from Pollinations...")

        # Pollinations can be slow — wait up to 40 seconds
        response = requests.get(image_url, timeout=40)

        if response.status_code == 200:
            image_path = "post_image.jpg"
            with open(image_path, "wb") as f:
                f.write(response.content)
            print("[AGENT LOG] Image generated successfully.")
            return image_path
        else:
            print(f"[WARNING] Image generation failed (status {response.status_code}). Will post without image.")
            return None
    except Exception as e:
        print(f"[WARNING] Image generation error: {e}. Will post without image.")
        return None

# ── 5. Upload Image to LinkedIn ───────────────────────────────────────────────
def upload_image_to_linkedin(user_id, image_path):
    # Step 5a: Register the image upload
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": f"urn:li:person:{user_id}",
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }
    try:
        reg_response = requests.post(register_url, headers=headers, json=register_payload, timeout=15)
        if reg_response.status_code != 200:
            print(f"[WARNING] Image register failed: {reg_response.text}")
            return None

        reg_data = reg_response.json()
        upload_url = reg_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn  = reg_data['value']['asset']

        # Step 5b: Upload the image bytes
        with open(image_path, "rb") as img_file:
            upload_response = requests.put(
                upload_url,
                data=img_file,
                headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"},
                timeout=30
            )
        if upload_response.status_code in (200, 201):
            print("[AGENT LOG] Image uploaded to LinkedIn.")
            return asset_urn
        else:
            print(f"[WARNING] Image upload failed: {upload_response.status_code}")
            return None
    except Exception as e:
        print(f"[WARNING] Image upload error: {e}")
        return None

# ── 6. Get LinkedIn User ID ───────────────────────────────────────────────────
def get_linkedin_user_id():
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json().get("sub")
    else:
        print(f"[ERROR] Could not fetch LinkedIn user ID: {response.text}")
        return None

# ── 7. Post to LinkedIn (with or without image) ───────────────────────────────
def post_to_linkedin(content, image_path=None):
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

    # Try to attach image if available
    asset_urn = None
    if image_path:
        asset_urn = upload_image_to_linkedin(user_id, image_path)

    if asset_urn:
        # Post WITH image
        payload = {
            "author": f"urn:li:person:{user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status": "READY",
                        "description": {"text": "GST Update"},
                        "media": asset_urn,
                        "title": {"text": "GST News Update"}
                    }]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    else:
        # Post WITHOUT image (fallback)
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
        print("[SUCCESS] Posted to LinkedIn!" + (" (with image)" if asset_urn else " (text only)"))
    else:
        print(f"[ERROR] LinkedIn post failed: {response.status_code} — {response.text}")

# ── Main ──────────────────────────────────────────────────────────────────────
if not GROQ_API_KEY or not LINKEDIN_TOKEN:
    print("[ERROR] Missing API keys. Check your GitHub Secrets.")
    print(f"  GROQ_API_KEY     : {'SET' if GROQ_API_KEY else 'MISSING'}")
    print(f"  LINKEDIN_TOKEN   : {'SET' if LINKEDIN_TOKEN else 'MISSING'}")
else:
    news_title, news_link = fetch_gst_news()

    if news_title:
        print(f"[AGENT LOG] Found news: {news_title}")

        draft = ask_groq_to_draft(news_title, news_link)

        if "SKIP" not in draft:
            image_path = generate_post_image(news_title)
            post_to_linkedin(draft, image_path)
        else:
            print("[AGENT LOG] News wasn't critical enough. Skipping.")
    else:
        print("[AGENT LOG] No news found.")
