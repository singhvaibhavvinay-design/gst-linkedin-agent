import os
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import random

# ── 1. Load secret keys ───────────────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")

# ── 2. News Sources for Each Topic ────────────────────────────────────────────
NEWS_SOURCES = {
    "AI & Technology": [
        "https://news.google.com/rss/search?q=artificial+intelligence+India+2026&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=AI+technology+India+latest&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=generative+AI+India+business&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "Cyber Law": [
        "https://news.google.com/rss/search?q=cyber+law+India+2026&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=cybercrime+India+IT+act&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=cyber+security+India+policy&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "DPDPA": [
        "https://news.google.com/rss/search?q=DPDPA+India+data+protection&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Digital+Personal+Data+Protection+Act+India&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=data+privacy+India+2026&hl=en-IN&gl=IN&ceid=IN:en",
    ]
}

# ── 3. Hashtag Bank per Topic ─────────────────────────────────────────────────
HASHTAG_BANK = {
    "AI & Technology": {
        "always":    "#AI #ArtificialIntelligence #TechIndia #IndianTech #DigitalIndia",
        "optional": {
            "generative": "#GenAI #ChatGPT #LLM #GenerativeAI",
            "startup":    "#AIStartup #StartupIndia #TechStartup",
            "business":   "#AIBusiness #FutureOfWork #Automation",
            "policy":     "#AIPolicy #TechRegulation #IndiaAI",
            "always_end": "#Innovation #TechNews #India2026"
        }
    },
    "Cyber Law": {
        "always":    "#CyberLaw #CyberSecurity #ITAct #IndiaLaw #DigitalIndia",
        "optional": {
            "crime":      "#Cybercrime #CyberFraud #OnlineSafety",
            "policy":     "#CyberPolicy #CERT #DataSecurity",
            "business":   "#CyberCompliance #InfoSec #CISOs",
            "privacy":    "#DataPrivacy #CyberAwareness #DigitalSafety",
            "always_end": "#LegalUpdate #IndiaLegal #TechLaw"
        }
    },
    "DPDPA": {
        "always":    "#DPDPA #DataProtection #DataPrivacy #IndiaPrivacy #DigitalIndia",
        "optional": {
            "compliance": "#DPDPACompliance #PrivacyLaw #DataGovernance",
            "business":   "#CISO #DPO #DataOfficer #PrivacyByDesign",
            "penalty":    "#DPDPAPenalty #DataBreach #Compliance",
            "rights":     "#DataRights #ConsentManagement #DigitalRights",
            "always_end": "#IndiaLegal #PrivacyFirst #India2026"
        }
    }
}

# ── 4. Fetch News ─────────────────────────────────────────────────────────────
def fetch_news(topic):
    """Try all RSS sources for a topic, return first valid news item."""
    urls = NEWS_SOURCES[topic]
    random.shuffle(urls)  # rotate sources to get variety

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                root  = ET.fromstring(response.content)
                items = root.findall('.//item')
                if items:
                    # Pick a random item from top 5 for variety
                    item = random.choice(items[:5])
                    title = item.find('title').text
                    link  = item.find('link').text
                    if title and link:
                        print(f"[AGENT LOG] [{topic}] Found: {title}")
                        return title, link
        except Exception as e:
            print(f"[WARNING] RSS fetch failed for {topic}: {e}")

    print(f"[AGENT LOG] [{topic}] No news found.")
    return None, None

# ── 5. Draft LinkedIn Post with Groq ─────────────────────────────────────────
def draft_post_with_groq(topic, title, link):
    """Use Groq + Llama to write a LinkedIn post for the given topic."""

    hashtags = HASHTAG_BANK[topic]

    topic_context = {
        "AI & Technology": (
            "You are an AI and technology expert in India. "
            "You write insightful LinkedIn posts about AI trends, tools, and their impact on Indian businesses."
        ),
        "Cyber Law": (
            "You are a cyber law expert and digital security consultant in India. "
            "You write clear LinkedIn posts about cyber laws, IT Act updates, and cybersecurity for Indian companies."
        ),
        "DPDPA": (
            "You are India's leading expert on the Digital Personal Data Protection Act (DPDPA). "
            "You write precise, actionable LinkedIn posts helping Indian businesses understand and comply with DPDPA."
        )
    }

    prompt = (
        f"Analyze this {topic} news: '{title}'.\n\n"
        f"If it is important and relevant for Indian professionals or businesses, "
        f"draft an engaging LinkedIn post with this EXACT structure:\n\n"
        f"1. HOOK — One powerful opening sentence (use an emoji)\n"
        f"2. SUMMARY — 2-3 sentences explaining what happened and why it matters\n"
        f"3. IMPACT BULLETS — 3 to 5 bullet points with emojis showing real impact "
        f"on businesses, professionals, or individuals in India\n"
        f"4. CALL TO ACTION — One line asking readers to comment, share, or act\n"
        f"5. LINK — {link}\n"
        f"6. HASHTAGS — End with 10-15 hashtags.\n"
        f"   Always include: {hashtags['always']}\n"
        f"   Choose relevant optional hashtags from: {hashtags['optional']}\n\n"
        f"Keep it under 300 words. Professional but conversational tone.\n"
        f"If the news is NOT important or relevant, reply with exactly: SKIP"
    )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": topic_context[topic]},
            {"role": "user",   "content": prompt}
        ],
        "max_tokens":  1000,
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        result   = response.json()
        if 'choices' not in result:
            print(f"[ERROR] Groq error for {topic}: {result}")
            return "SKIP"
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"[ERROR] Groq API failed for {topic}: {e}")
        return "SKIP"

# ── 6. Generate Image (Pollinations - Free) ───────────────────────────────────
def generate_image(topic, news_title):
    """Generate a professional LinkedIn image for the topic."""

    style_map = {
        "AI & Technology": "futuristic AI technology India digital neural network blue purple modern",
        "Cyber Law":       "cyber security India digital shield lock professional dark blue",
        "DPDPA":           "data privacy India protection digital shield green white professional"
    }

    image_prompt = (
        f"Professional LinkedIn infographic, {style_map[topic]}, "
        f"{news_title[:60]}, clean modern design, no people, 2026"
    )
    encoded = urllib.parse.quote(image_prompt)
    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1200&height=628&nologo=true&seed={random.randint(1, 999)}"
    )

    try:
        print(f"[AGENT LOG] [{topic}] Generating image...")
        response = requests.get(image_url, timeout=40)
        if response.status_code == 200:
            path = f"post_image_{topic.replace(' ', '_').replace('&','and')}.jpg"
            with open(path, "wb") as f:
                f.write(response.content)
            print(f"[AGENT LOG] [{topic}] Image generated.")
            return path
        else:
            print(f"[WARNING] [{topic}] Image failed (status {response.status_code}).")
            return None
    except Exception as e:
        print(f"[WARNING] [{topic}] Image error: {e}")
        return None

# ── 7. Upload Image to LinkedIn ───────────────────────────────────────────────
def upload_image_to_linkedin(user_id, image_path):
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type":  "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner":   f"urn:li:person:{user_id}",
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier":       "urn:li:userGeneratedContent"
            }]
        }
    }
    try:
        reg  = requests.post(register_url, headers=headers, json=register_payload, timeout=15)
        if reg.status_code != 200:
            print(f"[WARNING] Image register failed: {reg.text}")
            return None
        data       = reg.json()
        upload_url = data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn  = data['value']['asset']

        with open(image_path, "rb") as img:
            up = requests.put(
                upload_url, data=img,
                headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"},
                timeout=30
            )
        if up.status_code in (200, 201):
            print("[AGENT LOG] Image uploaded to LinkedIn.")
            return asset_urn
        else:
            print(f"[WARNING] Image upload failed: {up.status_code}")
            return None
    except Exception as e:
        print(f"[WARNING] Image upload error: {e}")
        return None

# ── 8. Get LinkedIn User ID ───────────────────────────────────────────────────
def get_linkedin_user_id():
    url      = "https://api.linkedin.com/v2/userinfo"
    headers  = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json().get("sub")
    print(f"[ERROR] Could not fetch LinkedIn user ID: {response.text}")
    return None

# ── 9. Post to LinkedIn ───────────────────────────────────────────────────────
def post_to_linkedin(topic, content, image_path=None):
    user_id = get_linkedin_user_id()
    if not user_id:
        print("[ERROR] Aborting — no LinkedIn user ID.")
        return

    url     = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type":  "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    asset_urn = upload_image_to_linkedin(user_id, image_path) if image_path else None

    if asset_urn:
        payload = {
            "author":         f"urn:li:person:{user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary":    {"text": content},
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status":      "READY",
                        "description": {"text": f"{topic} Update"},
                        "media":        asset_urn,
                        "title":       {"text": f"{topic} News"}
                    }]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
    else:
        payload = {
            "author":         f"urn:li:person:{user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary":    {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    if response.status_code == 201:
        print(f"[SUCCESS] [{topic}] Posted to LinkedIn!" + (" (with image)" if asset_urn else " (text only)"))
    else:
        print(f"[ERROR] [{topic}] LinkedIn post failed: {response.status_code} — {response.text}")

# ── Main ──────────────────────────────────────────────────────────────────────
if not GROQ_API_KEY or not LINKEDIN_TOKEN:
    print("[ERROR] Missing API keys. Check your GitHub Secrets.")
    print(f"  GROQ_API_KEY     : {'SET' if GROQ_API_KEY else 'MISSING'}")
    print(f"  LINKEDIN_TOKEN   : {'SET' if LINKEDIN_TOKEN else 'MISSING'}")
else:
    posted = 0

    for topic in ["AI & Technology", "Cyber Law", "DPDPA"]:
        print(f"\n{'='*50}")
        print(f"[AGENT LOG] Processing topic: {topic}")
        print(f"{'='*50}")

        title, link = fetch_news(topic)

        if not title:
            print(f"[AGENT LOG] [{topic}] Skipping — no news found.")
            continue

        draft = draft_post_with_groq(topic, title, link)

        if "SKIP" in draft:
            print(f"[AGENT LOG] [{topic}] News not critical enough. Skipping.")
            continue

        image_path = generate_image(topic, title)
        post_to_linkedin(topic, draft, image_path)
        posted += 1

    print(f"\n[AGENT LOG] Done. Posted {posted}/3 topics today.")
