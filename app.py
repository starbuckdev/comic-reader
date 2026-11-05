#!/usr/bin/env python3
"""
RSS Comic Strip Reader - A feed reader for comic strips.
"""

import re
import time
import feedparser
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# Only real RSS feed URLs work here. xkcd is reliable.
# comicsrss.com publishes RSS feeds for many syndicated strips.
RSS_FEEDS = [
    "https://xkcd.com/rss.xml",
    "https://www.comicsrss.com/rss/peanuts.rss",
    "https://www.comicsrss.com/rss/dilbert.rss",
    "https://www.comicsrss.com/rss/pearlsbeforeswine.rss",
]

FEED_DISPLAY_NAMES = {
    "https://xkcd.com/rss.xml": "xkcd",
    "https://www.comicsrss.com/rss/peanuts.rss": "Peanuts",
    "https://www.comicsrss.com/rss/dilbert.rss": "Dilbert",
    "https://www.comicsrss.com/rss/pearlsbeforeswine.rss": "Pearls Before Swine",
}

PER_PAGE = 5
CACHE_TTL = 600  # seconds

_cache = {"comics": None, "fetched_at": 0}


def extract_image(entry):
    """Pull the best image URL out of a feed entry."""
    # 1. Media RSS: <media:content url="...">
    for media in entry.get("media_content", []) or []:
        if media.get("url"):
            return media["url"]

    # 2. Enclosures
    for enc in entry.get("enclosures", []) or []:
        href = enc.get("href") or enc.get("url")
        if href and "image" in (enc.get("type") or ""):
            return href

    # 3. First <img src="..."> in the summary/description
    html = entry.get("summary", "") or entry.get("description", "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
    if m:
        return m.group(1)

    return None


def fetch_all_comics():
    comics = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        for entry in feed.entries:
            image = extract_image(entry)
            if not image:
                continue

            pp = entry.get("published_parsed") or entry.get("updated_parsed")
            ts = time.mktime(pp) if pp else 0

            comics.append({
                "title": entry.get("title", "Untitled"),
                "link": entry.get("link", ""),
                "published": entry.get("published", "") or entry.get("updated", ""),
                "image": image,
                "feed": FEED_DISPLAY_NAMES.get(url, ""),
                "_ts": ts,
            })

    comics.sort(key=lambda c: c["_ts"], reverse=True)
    for c in comics:
        c.pop("_ts", None)
    return comics


def get_comics():
    now = time.time()
    if _cache["comics"] is None or now - _cache["fetched_at"] > CACHE_TTL:
        _cache["comics"] = fetch_all_comics()
        _cache["fetched_at"] = now
    return _cache["comics"]


HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Comic Strip Feed</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
  body { background: #f5f5f5; color: #333; line-height: 1.6; }
  .container { max-width: 800px; margin: 0 auto; padding: 20px; }
  header { text-align: center; margin-bottom: 30px; padding: 20px;
           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
           color: white; border-radius: 12px;
           box-shadow: 0 4px 15px rgba(102,126,234,0.3); }
  h1 { font-size: 2.5rem; margin-bottom: 10px; }
  .subtitle { font-size: 1.1rem; opacity: 0.9; }
  .feed { display: flex; flex-direction: column; gap: 20px; }
  .comic-item { background: white; border-radius: 12px; overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                transition: transform .2s ease, box-shadow .2s ease;
                animation: fadeIn .5s ease; }
  .comic-item:hover { transform: translateY(-5px);
                      box-shadow: 0 8px 20px rgba(0,0,0,0.15); }
  .comic-header { padding: 15px 20px; background: #f8f9fa;
                  border-bottom: 1px solid #e9ecef; display: flex;
                  justify-content: space-between; align-items: center; }
  .comic-title { font-weight: 600; font-size: 1.1rem; color: #495057; }
  .comic-date { font-size: .85rem; color: #6c757d; white-space: nowrap; }
  .comic-body { padding: 20px; text-align: center; }
  .comic-image { max-width: 100%; height: auto; border-radius: 8px;
                 margin-bottom: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
  .comic-link { display: inline-block; padding: 8px 16px; background: #667eea;
                color: white; text-decoration: none; border-radius: 20px;
                font-size: .9rem; font-weight: 500; margin-top: 10px;
                transition: background .3s ease; }
  .comic-link:hover { background: #5a67d8; }
  .loading, .no-data { text-align: center; padding: 20px;
                       color: #6c757d; font-style: italic; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); }
                      to   { opacity: 1; transform: translateY(0); } }
  .spinner { display: inline-block; width: 20px; height: 20px;
             border: 3px solid #f3f3f3; border-top: 3px solid #667eea;
             border-radius: 50%; animation: spin 1s linear infinite;
             margin-right: 8px; vertical-align: middle; }
  @keyframes spin { 0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); } }
  @media (max-width: 600px) {
    .container { padding: 10px; }
    h1 { font-size: 2rem; }
    .comic-header { flex-direction: column; gap: 8px; }
    .comic-title { font-size: 1rem; }
    .comic-body { padding: 15px; }
  }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Comic Strip Feed</h1>
    <p class="subtitle">Scroll down to see the latest comics. Newest first.</p>
  </header>
  <div class="feed" id="comicFeed"></div>
  <div class="loading" id="loadingIndicator" style="display:none">
    <span class="spinner"></span>Loading more comics...
  </div>
  <div class="no-data" id="noData" style="display:none">
    No comics found. Try adding more RSS feeds.
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
  const feedContainer = document.getElementById('comicFeed');
  const loadingIndicator = document.getElementById('loadingIndicator');
  const noData = document.getElementById('noData');
  let page = 1, hasMore = true, isLoading = false;

  loadComics();

  window.addEventListener('scroll', () => {
    if (isLoading || !hasMore) return;
    const nearBottom = window.pageYOffset + window.innerHeight
                       >= document.documentElement.scrollHeight - 500;
    if (nearBottom) loadComics();
  });

  async function loadComics() {
    if (isLoading || !hasMore) return;
    isLoading = true;
    loadingIndicator.style.display = 'block';

    try {
      const res = await fetch(`/api/comics?page=${page}`);
      const data = await res.json();

      if (data.comics.length === 0) {
        hasMore = false;
        if (page === 1) noData.style.display = 'block';
      } else {
        data.comics.forEach(comic => {
          const item = document.createElement('div');
          item.className = 'comic-item';

          const header = document.createElement('div');
          header.className = 'comic-header';

          const title = document.createElement('div');
          title.className = 'comic-title';
          title.textContent = comic.title;

          const date = document.createElement('div');
          date.className = 'comic-date';
          date.textContent = comic.published
            ? new Date(comic.published).toLocaleString()
            : '';

          header.append(title, date);

          const body = document.createElement('div');
          body.className = 'comic-body';

          const img = document.createElement('img');
          img.className = 'comic-image';
          img.src = comic.image;
          img.alt = comic.title;
          img.loading = 'lazy';

          body.append(img);
          item.append(header, body);
          feedContainer.appendChild(item);
        });

        page++;
        hasMore = data.has_more;
      }
    } catch (err) {
      console.error('Error loading comics:', err);
    } finally {
      isLoading = false;
      loadingIndicator.style.display = 'none';
    }
  }
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/comics")
def api_comics():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    comics = get_comics()
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE

    return jsonify({
        "comics": comics[start:end],
        "page": page,
        "has_more": end < len(comics),
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)