import os
import requests
import xml.etree.ElementTree as ET

# ── 1. Load secret keys ───────────────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")

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
        "model": "llama-3.3-70b-versatile",
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

# ── 4. Get LinkedIn User ID ───────────────────────────────────────────────────
def get_linkedin_user_id():
    url      = "https://api.linkedin.com/v2/userinfo"
    headers  = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json().get("sub")
    print(f"[ERROR] Could not fetch LinkedIn user ID: {response.text}")
    return None

# ── 5. Post to LinkedIn (text only) ──────────────────────────────────────────
def post_to_linkedin(content):
    user_id = get_linkedin_user_id()
    if not user_id:
        print("[ERROR] Aborting post — no LinkedIn user ID.")
        return

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
    else:
        print(f"[ERROR] LinkedIn post failed: {response.status_code} — {response.text}")

# ── Main ──────────────────────────────────────────────────────────────────────
if not GROQ_API_KEY or not LINKEDIN_TOKEN:
    print("[ERROR] Missing API keys. Check your GitHub Secrets.")
    print(f"  GROQ_API_KEY   : {'SET' if GROQ_API_KEY else 'MISSING'}")
    print(f"  LINKEDIN_TOKEN : {'SET' if LINKEDIN_TOKEN else 'MISSING'}")
else:
    news_title, news_link = fetch_gst_news()

    if news_title:
        print(f"[AGENT LOG] Found news: {news_title}")
        draft = ask_groq_to_draft(news_title, news_link)
        if "SKIP" not in draft:
            post_to_linkedin(draft)
        else:
            print("[AGENT LOG] News wasn't critical enough. Skipping.")
    else:
        print("[AGENT LOG] No news found.")
