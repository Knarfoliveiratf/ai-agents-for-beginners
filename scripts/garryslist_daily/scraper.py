"""Daily Garry's List scraper, translator and emailer.

Fetches https://garryslist.org/posts, identifies posts that are new since the
last run, translates them to Portuguese (pt) using deep-translator, and emails
the digest via SMTP.

Configuration is read from environment variables (see .env.example).
"""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
import time
from dataclasses import asdict, dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

BASE_URL = "https://garryslist.org"
LIST_URL = f"{BASE_URL}/posts"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
STATE_FILE = Path(os.environ.get("GARRYSLIST_STATE_FILE", "state/seen.json"))
TARGET_LANG = os.environ.get("TARGET_LANG", "pt")
REQUEST_TIMEOUT = 30
MAX_TRANSLATE_CHARS = 4500


@dataclass
class Post:
    id: str
    title: str
    url: str
    summary: str
    posted_at: str

    def merge_text(self) -> str:
        return f"{self.title}\n\n{self.summary}".strip()


def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def parse_posts(html: str) -> list[Post]:
    """Parse posts from the listing page.

    Uses a defensive strategy: tries common containers (article, .post,
    .listing, li with link). Adjust selectors here if the site layout changes.
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates: list = []
    for selector in ("article", ".post", ".listing", "li.post", "div.post-item"):
        found = soup.select(selector)
        if found:
            candidates = found
            break

    if not candidates:
        candidates = [
            a.find_parent(["article", "li", "div"]) or a
            for a in soup.select("a[href*='/posts/']")
        ]

    posts: list[Post] = []
    seen_ids: set[str] = set()
    for node in candidates:
        link = node.find("a", href=True)
        if not link:
            continue
        href = link["href"]
        if not href or href.startswith("#"):
            continue
        url = urljoin(BASE_URL, href)
        title = (link.get_text(" ", strip=True) or node.get_text(" ", strip=True))[:300]
        if not title:
            continue

        summary_el = node.find(["p", "div"], class_=lambda c: c and "summary" in c.lower())
        if summary_el is None:
            paragraphs = [p.get_text(" ", strip=True) for p in node.find_all("p")]
            summary = " ".join(paragraphs)[:600]
        else:
            summary = summary_el.get_text(" ", strip=True)[:600]

        date_el = node.find(["time", "span"], class_=lambda c: c and "date" in c.lower())
        posted_at = ""
        if date_el is not None:
            posted_at = date_el.get("datetime") or date_el.get_text(" ", strip=True)

        post_id = href.rstrip("/").split("/")[-1] or url
        if post_id in seen_ids:
            continue
        seen_ids.add(post_id)
        posts.append(
            Post(id=post_id, title=title, url=url, summary=summary, posted_at=posted_at)
        )
    return posts


def load_seen() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("seen", []))
    except (OSError, json.JSONDecodeError):
        return set()


def save_seen(ids: Iterable[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"seen": sorted(ids)}, indent=2), encoding="utf-8"
    )


def translate(text: str, translator: GoogleTranslator) -> str:
    if not text.strip():
        return ""
    chunks = [
        text[i : i + MAX_TRANSLATE_CHARS]
        for i in range(0, len(text), MAX_TRANSLATE_CHARS)
    ]
    translated_parts: list[str] = []
    for chunk in chunks:
        for attempt in range(3):
            try:
                translated_parts.append(translator.translate(chunk))
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"  translation failed, keeping original: {exc}", file=sys.stderr)
                    translated_parts.append(chunk)
                else:
                    time.sleep(2 ** attempt)
    return "".join(translated_parts)


def translate_posts(posts: list[Post]) -> list[dict]:
    translator = GoogleTranslator(source="auto", target=TARGET_LANG)
    out: list[dict] = []
    for post in posts:
        out.append(
            {
                **asdict(post),
                "title_pt": translate(post.title, translator),
                "summary_pt": translate(post.summary, translator),
            }
        )
    return out


def render_email(translated: list[dict]) -> tuple[str, str]:
    plain_lines = [f"Garry's List — novas publicações ({len(translated)}):", ""]
    html_parts = [
        "<html><body style='font-family:Arial,sans-serif;'>",
        f"<h2>Garry's List — {len(translated)} nova(s) publicação(ões)</h2>",
    ]
    for item in translated:
        plain_lines.extend(
            [
                f"• {item['title_pt']}",
                f"  ({item['title']})",
                f"  {item['url']}",
                f"  {item['summary_pt']}",
                "",
            ]
        )
        html_parts.append(
            "<div style='margin-bottom:16px;padding:12px;border-left:3px solid #2b6cb0;'>"
            f"<h3 style='margin:0 0 4px 0;'><a href='{escape(item['url'])}'>{escape(item['title_pt'])}</a></h3>"
            f"<p style='margin:0;color:#666;font-size:12px;'>Original: {escape(item['title'])}</p>"
            f"<p style='margin:8px 0;'>{escape(item['summary_pt'])}</p>"
            f"<p style='margin:0;font-size:12px;color:#888;'>Original: {escape(item['summary'])}</p>"
            "</div>"
        )
    html_parts.append("</body></html>")
    return "\n".join(plain_lines), "".join(html_parts)


def send_email(subject: str, plain: str, html: str) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ.get("EMAIL_FROM", user)
    recipient = os.environ["EMAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(user, password)
        server.sendmail(sender, [recipient], msg.as_string())


def main() -> int:
    latest_only = os.environ.get("LATEST_ONLY", "").lower() in {"1", "true", "yes"}

    print(f"Fetching {LIST_URL} ...", file=sys.stderr)
    html = fetch_html(LIST_URL)
    posts = parse_posts(html)
    print(f"Parsed {len(posts)} posts", file=sys.stderr)

    if not posts:
        print("No posts found on page; nothing to send.", file=sys.stderr)
        return 0

    if latest_only:
        target_posts = posts[:1]
        print("LATEST_ONLY=1: sending only the most recent post.", file=sys.stderr)
    else:
        seen = load_seen()
        target_posts = [p for p in posts if p.id not in seen]
        print(f"{len(target_posts)} new posts since last run", file=sys.stderr)

    if not target_posts:
        save_seen(load_seen() | {p.id for p in posts})
        print("No new posts; skipping email.", file=sys.stderr)
        return 0

    translated = translate_posts(target_posts)
    plain, html_body = render_email(translated)
    if latest_only:
        subject = f"Garry's List — última publicação: {translated[0]['title_pt'][:80]}"
    else:
        subject = f"Garry's List — {len(target_posts)} nova(s) publicação(ões)"
    send_email(subject, plain, html_body)
    print(f"Email enviado para {os.environ.get('EMAIL_TO')}", file=sys.stderr)

    if not latest_only:
        save_seen(load_seen() | {p.id for p in posts})
    return 0


if __name__ == "__main__":
    sys.exit(main())
