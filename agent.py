import os
import json
import random
import requests
import xml.etree.ElementTree as ET

# ── 1. Load secret keys ───────────────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")

# ── 2. History file (so we never repeat an already-posted/considered story) ──
HISTORY_FILE = "posted_history.json"
MAX_HISTORY  = 60   # keep the file small; we only need recent memory

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not read history file, starting fresh: {e}")
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-MAX_HISTORY:], f, indent=2)
    except Exception as e:
        print(f"[ERROR] Could not save history file: {e}")

# ── 3. Multiple GST query angles (shuffled each run) ─────────────────────────
GST_QUERIES = [
    "GST+council+meeting+India+when:3d",
    "GST+rate+change+India+when:3d",
    "GST+return+filing+GSTR+India+when:3d",
    "GST+e-invoicing+e-way+bill+India+when:3d",
    "GST+notification+CBIC+India+when:3d",
    "GST+amendment+India+when:3d",
    "GST+collection+revenue+India+when:3d",
]

# ── 4. Fetch GST News (diversified + deduplicated) ───────────────────────────
def fetch_gst_news(history):
    queries = GST_QUERIES.copy()
    random.shuffle(queries)

    seen_links  = {h["link"] for h in history}
    seen_titles = {h["title"] for h in history}

    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue
            root  = ET.fromstring(response.content)
            items = root.findall('.//item')
            random.shuffle(items)

            for item in items[:8]:
                title_el = item.find('title')
                link_el  = item.find('link')
                if title_el is None or link_el is None:
                    continue
                title, link = title_el.text, link_el.text
                if not title or not link:
                    continue
                if link in seen_links or title in seen_titles:
                    continue  # already posted/considered this one before
                print(f"[AGENT LOG] Candidate via query '{q}': {title}")
                return title, link
        except Exception as e:
            print(f"[WARNING] RSS fetch failed for query '{q}': {e}")

    print("[AGENT LOG] No fresh, unseen GST news found across all queries.")
    return None, None

# ── 5. Ask Groq to Draft LinkedIn Post ───────────────────────────────────────
def ask_groq_to_draft(title, link):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json"
    }
    prompt = (
        f"Analyze this GST News: '{title}'. "
        f"If it is an important update or amendment for Indian businesses, "
        f"draft an engaging LinkedIn post following this exact structure:\n\n"
        f"1. HOOK LINE — one powerful opening sentence to grab attention\n"
        f"2. SUMMARY — 2-3 sentences explaining what changed\n"
        f"3. IMPACT BULLETS — 3 to 5 bullet points starting with an emoji, "
        f"explaining the impact on businesses, taxpayers, or specific industries\n"
        f"4. CALL TO ACTION — one line encouraging readers to act or comment\n"
        f"5. HASHTAGS — end with 10 to 15 relevant hashtags chosen from this list "
        f"based on what the news is actually about:\n"
        f"   Always include: #GST #GSTIndia #Tax #IndiaFinance #TaxUpdate\n"
        f"   Add if about filing/returns: #GSTReturn #GSTR1 #GSTR3B #ITR #TaxFiling\n"
        f"   Add if about businesses: #SME #MSMEs #StartupIndia #IndianBusiness #Entrepreneurs\n"
        f"   Add if about e-invoicing/tech: #EInvoicing #DigitalIndia #TaxTech\n"
        f"   Add if about rates/slabs: #GSTRates #TaxSlab #IndirectTax\n"
        f"   Add if about council meeting: #GSTCouncil #FinanceMinistry #NirmalaSitharaman\n"
        f"   Add if about compliance: #TaxCompliance #CFO #Accounting #Finance\n"
        f"   Always end with: #IndianEconomy #BusinessIndia\n\n"
        f"Keep the total post under 300 words. "
        f"If the news is NOT important, reply exactly with the single word 'SKIP'."
    )
    payload = {
        model="openai/gpt-oss-120b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert GST tax consultant in India. "
                    "You write clear, professional, and engaging LinkedIn posts "
                    "for Indian businesses about GST updates. "
                    "Always follow the exact post structure given to you. "
                    "Always end every post with 10-15 relevant hashtags on the last line."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "max_tokens":  1000,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        result   = response.json()
        if 'choices' not in result:
            print(f"[ERROR] Groq unexpected response: {result}")
            return "SKIP"
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"[ERROR] Groq API failed: {e}")
        return "SKIP"

# ── 6. Get LinkedIn User ID ───────────────────────────────────────────────────
def get_linkedin_user_id():
    url      = "https://api.linkedin.com/v2/userinfo"
    headers  = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json().get("sub")
    print(f"[ERROR] Could not fetch LinkedIn user ID: {response.text}")
    return None

# ── 7. Post to LinkedIn (text only) ──────────────────────────────────────────
def post_to_linkedin(content):
    user_id = get_linkedin_user_id()
    if not user_id:
        print("[ERROR] Aborting post — no LinkedIn user ID.")
        return False

    url     = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type":  "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
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
        print("[SUCCESS] Posted to LinkedIn!")
        return True
    else:
        print(f"[ERROR] LinkedIn post failed: {response.status_code} — {response.text}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
if not GROQ_API_KEY or not LINKEDIN_TOKEN:
    print("[ERROR] Missing API keys. Check your GitHub Secrets.")
    print(f"  GROQ_API_KEY   : {'SET' if GROQ_API_KEY else 'MISSING'}")
    print(f"  LINKEDIN_TOKEN : {'SET' if LINKEDIN_TOKEN else 'MISSING'}")
else:
    history = load_history()
    news_title, news_link = fetch_gst_news(history)

    if news_title:
        draft = ask_groq_to_draft(news_title, news_link)
        if "SKIP" not in draft:
            success = post_to_linkedin(draft)
            history.append({"title": news_title, "link": news_link, "posted": success})
        else:
            print("[AGENT LOG] News wasn't critical enough. Skipping post, but remembering it.")
            history.append({"title": news_title, "link": news_link, "posted": False})
        save_history(history)
    else:
        print("[AGENT LOG] No new news found this run.")
