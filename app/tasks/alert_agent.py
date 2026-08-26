import os
import json
import uuid
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import asyncio
from app.services.agent_engine import tool_query_social_sentiment
from app.models.database import ingest_social_mentions
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SocialAlertAgent")

def scrape_pantip_mentions(keyword: str):
    """
    Scrape real mentions from Pantip.com based on a keyword.
    In a real production environment, this should handle pagination and avoid IP bans.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://pantip.com/search?q={requests.utils.quote(keyword)}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch Pantip: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # This selector depends on Pantip's current HTML structure
        # We look for topic titles in the tag page
        topics = soup.find_all('a', class_='gtm-topic-title')
        if not topics:
            # Fallback to general link search for demo purposes if class changes
            topics = [a for a in soup.find_all('a') if a.get('href') and '/topic/' in a['href'] and len(a.text.strip()) > 10]
            
        for t in topics[:5]: # Take top 5 recent posts
            title = t.text.strip()
            link = t['href']
            if not link.startswith('http'):
                link = f"https://pantip.com{link}"
                
            # We mock the sentiment for now or pass it to LLM for evaluation
            # For demonstration, we just ingest it as raw data
            results.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, link)),
                "title": title,
                "text": f"Found topic on Pantip: {title}",
                "url": link,
                "author": "Pantip User",
                "published_at": datetime.now().isoformat(),
                "sentiment": "Neutral", # Needs NLP pipeline for real sentiment
                "platform": "Pantip"
            })
            
        return results
    except Exception as e:
        logger.error(f"Error scraping Pantip: {e}")
        return []

async def proactive_social_listening_alert():
    """
    Phase 2.2: Proactive Social Listening Alert Agent.
    Now upgraded to scrape LIVE data from Pantip.
    """
    # Wait for web server to boot up
    await asyncio.sleep(5)
    while True:
        try:
            logger.info("🔍 [Social Alert Agent] Waking up to scan LIVE social media streams (Pantip)...")
            
            # 1. Scrape real data
            keywords = ["นิด้า", "NIDA", "สถาบันบัณฑิตพัฒนบริหารศาสตร์"]
            new_mentions = []
            for kw in keywords:
                logger.info(f"Scraping Pantip for: {kw}")
                mentions = await asyncio.to_thread(scrape_pantip_mentions, kw)
                new_mentions.extend(mentions)
                import random
                delay = random.uniform(4.0, 10.0)
                await asyncio.sleep(delay) # Polite random delay
                
            # 2. Ingest to Postgres Warehouse
            if new_mentions:
                inserted = ingest_social_mentions(new_mentions, platform_override="Pantip")
                logger.info(f"✅ Ingested {inserted} new live mentions into Database.")
            
            # 3. Analyze a known topic for complaints from our warehouse
            topics_to_monitor = ["ค่าเทอม", "ที่จอดรถ", "นิด้า"]
            
            for topic in topics_to_monitor:
                result = await asyncio.to_thread(tool_query_social_sentiment, topic)
                
                negative_count = result.get("sentiment_distribution", {}).get("negative", 0)
                
                if negative_count > 0:
                    logger.warning(f"🚨 [ALERT] Detected {negative_count} negative complaints about '{topic}'!")
                    # In a real production system, here we would call LINE Notify API or SendGrid
                    logger.warning(f"📱 (Simulated) Sending LINE Notify to NIDA Management...")
            
            # Sleep for 15 minutes before scraping again to avoid IP Ban
            logger.info("💤 [Social Alert Agent] Live scan complete. Sleeping for 15 minutes.")
        except Exception as e:
            logger.error(f"Error in Social Alert Agent: {e}")
            
        await asyncio.sleep(900)

def start_alert_agent_bg_task():
    """Fire and forget the asyncio task."""
    loop = asyncio.get_running_loop()
    loop.create_task(proactive_social_listening_alert())
