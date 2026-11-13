"""Preserve observed post/comment text and links through analytics and saved results."""
from urllib.parse import urlparse

from .schemas import Post

ANALYSIS_VERSION = 9


def safe_url(value) -> str:
    if not isinstance(value, str):
        return ""
    try:
        parsed = urlparse(value)
        return value if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username else ""
    except ValueError:
        return ""


def build_evidence(posts: list[Post]) -> dict:
    collected, comments = [], []
    for post in posts:
        url = safe_url(post.url)
        collected.append({"id": post.id, "type": post.type, "posted_at": post.posted_at.isoformat(),
                          "caption": post.caption, "url": url,
                          "likes": post.likes, "comments": post.comments, "shares": post.shares,
                          "views": post.views, "saves": post.saves, "sales": post.sales,
                          "unavailable_metrics": post.unavailable_metrics, "metric_sources": post.metric_sources})
        samples = [c.model_dump() for c in post.comment_evidence] or [{"text": text} for text in post.comments_sample]
        for index, comment in enumerate(samples):
            if not comment.get("text"):
                continue
            direct = safe_url(comment.get("source_url"))
            kind = comment.get("source_kind") if direct else "post" if url else "none"
            comments.append({"id": f"{post.id}:{comment.get('id') or index}", "text": comment["text"],
                             "author": comment.get("author", ""), "post_id": post.id, "post_type": post.type,
                             "post_caption": post.caption, "posted_at": comment.get("posted_at") or post.posted_at.isoformat(),
                             "post_url": url, "source_url": direct or url, "source_kind": kind or "none"})
    return {"posts": collected, "comments": comments}


def restore_posts(raw_posts: list[dict], profile: dict) -> list[Post]:
    # Older saved rows kept post URLs only in profile.sources. Recover those exact URLs.
    urls = {str(s.get("title", "")).rsplit(" ", 1)[-1]: safe_url(s.get("url")) for s in profile.get("sources", [])}
    return [Post.model_validate({**raw, "url": safe_url(raw.get("url")) or urls.get(str(raw.get("id")), "")}) for raw in raw_posts]
