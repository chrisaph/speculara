"""Build a complete, bounded JSON analysis context and verified source references."""
import json
import re

from .evidence import safe_url


def build_chat_context(analysis: dict) -> dict:
    if analysis.get("context_version") == 1:
        return analysis
    if "facts" not in analysis:
        analysis = {"facts": analysis}
    keys = ("profile", "post_count", "date_range", "metric_availability", "facts", "demand", "predict", "recommend", "charts", "correlation")
    context = {key: analysis[key] for key in keys if key in analysis}
    # Evidence already carries post text and metrics. Avoid repeating full post
    # records in every chart, comparison and overlapping historical window.
    if 'charts' in context:
        context['charts'] = {key: {k:v for k,v in value.items() if k != 'posts'} if isinstance(value,dict) else value for key,value in context['charts'].items()}
    if 'recommend' in context:
        rec = context['recommend']
        context['recommend'] = {**rec, 'comparisons': {pid: [{k:v for k,v in row.items() if k not in ('title','url')} for row in rows[:6]] for pid,rows in rec.get('comparisons',{}).items()}}
    if 'predict' in context:
        pred = context['predict']
        context['predict'] = {**pred, 'similar_windows': [{**w, 'post_ids': [p['id'] for p in w.get('posts',[])], 'posts': []} for w in pred.get('similar_windows',[])]}
    sentiment = analysis.get("sentiment") or {}
    context["sentiment"] = {key: value for key, value in sentiment.items() if key != "samples"}
    context["context_version"] = 1
    context["data_quality"] = (analysis.get("facts") or {}).get("data_quality", {})
    evidence = analysis.get("evidence") or {}
    posts, comments, sources = [], [], {}
    for index, raw in enumerate(evidence.get("posts", [])[:40], 1):
        post = {**raw, "caption": str(raw.get("caption", ""))[:1200], "source_id": f"P{index}"}
        post["url"] = safe_url(post.get("url"))
        posts.append(post)
        sources[post["source_id"]] = {"id": post["source_id"], "title": f"{post.get('type', 'Post')} source",
                                        "url": post["url"], "kind": "post"}
    for index, raw in enumerate(evidence.get("comments", [])[:320], 1):
        comment = {**raw, "text": str(raw.get("text", ""))[:1000], "post_caption": str(raw.get("post_caption", ""))[:200], "source_id": f"C{index}"}
        comment["source_url"] = safe_url(comment.get("source_url"))
        comments.append(comment)
        sources[comment["source_id"]] = {"id": comment["source_id"], "title": "Comment source",
                                           "url": comment["source_url"], "kind": comment.get("source_kind", "post")}
    context["evidence"] = {"posts": posts, "comments": comments}
    context["source_index"] = sources
    # Remove whole evidence records if needed. Never cut serialized JSON mid-object.
    while comments and len(json.dumps(context, ensure_ascii=False)) > 180000:
        removed = comments.pop()
        sources.pop(removed["source_id"], None)
    context["evidence_coverage"] = {"posts_in_context": len(posts), "comments_in_context": len(comments),
                                     "collected_posts": len(evidence.get("posts", [])),
                                     "collected_comment_samples": len(evidence.get("comments", []))}
    return context


def cited_sources(answer: str, context: dict) -> list[dict]:
    sources, seen = [], set()
    for reference in re.findall(r"\[([PCW]\d+)\]", answer):
        source = context.get("source_index", {}).get(reference)
        if source and safe_url(source.get("url")) and source["url"] not in seen:
            sources.append(source)
            seen.add(source["url"])
    return sources
