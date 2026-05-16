import os
import requests
import xml.etree.ElementTree as ET

# 1. Load your secret keys safely
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINKEDIN_ID = os.environ.get("LINKEDIN_CLIENT_ID")

def fetch_gst_news():
    # Fetching a public Google News RSS feed for "GST India"
    url = "https://news.google.com/rss/search?q=GST+India&hl=en-IN&gl=IN&ceid=IN:en"
    response = requests.get(url)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        # Get the latest news title
        latest_item = root.find('.//item')
        if latest_item is not None:
            return latest_item.find('title').text, latest_item.find('link').text
    return None, None

def ask_gemini_to_draft(title, link):
    # Call Gemini API to write the post
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    prompt = f"Analyze this GST News: '{title}'. If it is an important update or amendment, draft an engaging LinkedIn post summarizing it. Include hashtags and the link: {link}. If it is not important news, reply exactly with the word 'SKIP'."
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    try:
        text_output = response.json()['candidates'][0]['content']['parts'][0]['text']
        return text_output.strip()
    except:
        return "SKIP"

def post_to_linkedin(content):
    # Placeholder: In a real environment, you use your LinkedIn ID/Token to POST here
    print(f"[AGENT LOG] Posting to LinkedIn:\n{content}")

# Execute Agent Logic
news_title, news_link = fetch_gst_news()
if news_title:
    draft = ask_gemini_to_draft(news_title, news_link)
    if "SKIP" not in draft:
        post_to_linkedin(draft)
    else:
        print("[AGENT LOG] News wasn't critical enough. Skipping.")
