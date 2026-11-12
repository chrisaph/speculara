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
    for index, raw in enumerate(evidence.get("posts", [])[:50], 1):
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
    references=[ref for group in re.findall(r'\[([^\]]{1,160})\]',answer) for ref in re.findall(r'\b[PCW]\d+\b',group)]
    for reference in references:
        source = context.get("source_index", {}).get(reference)
        if source and safe_url(source.get("url")) and source["url"] not in seen:
            sources.append(source)
            seen.add(source["url"])
    return sources


def model_context(analysis: dict, budget: int = 16000, question: str = '') -> dict:
    """Keep statistics and evidence IDs, remove repeated data before a model call."""
    if analysis.get('model_context_version')==1:return analysis
    c=json.loads(json.dumps(build_chat_context(analysis),ensure_ascii=False))
    c.pop('charts',None)  # The same metric values are already in per-post evidence.
    c.get('correlation',{}).pop('scatter',None)
    for key in ('matrix','sample_sizes'):c.get('correlation',{}).pop(key,None)
    if 'profile' in c:c['profile']={k:v for k,v in c['profile'].items() if k in ('platform','handle','followers','notes')}
    if 'facts' in c:
        c['facts']={k:v for k,v in c['facts'].items() if k in {'counts','phase','weeks','acc','growth','similar','pos','neg','neu','data_quality'}}
    if 'recommend' in c:c['recommend'].pop('comparisons',None)
    pred=c.get('predict',{})
    for key in ('history','forecast','similar_windows'):pred.pop(key,None)
    for key in ('validation','model','reason','coverage','partial_weeks','accuracy'):pred.pop(key,None)
    requested={m for m in ('views','likes','comments','shares','saves','sales') if m in question.lower()}
    if not requested:requested={pred.get('trend_metric','views')}
    for metric,item in pred.get('metrics',{}).items():
        item.pop('history',None)
        if metric not in requested:
            item.pop('forecast',None);item.pop('validation',None)
    for keyword in c.get('sentiment',{}).get('keywords',[]):keyword.pop('sample_ids',None)
    evidence=c.get('evidence',{})
    groups={}
    for comment in evidence.get('comments',[]):groups.setdefault(comment.get('post_id',''),[]).append(comment)
    evidence['comments']=[rows[i] for i in range(max((len(v) for v in groups.values()),default=0)) for rows in groups.values() if i<len(rows)]
    c['source_index']={key:value for key,value in c.get('source_index',{}).items() if value.get('url')}
    parents={p.get('id'):p.get('source_id') for p in evidence.get('posts',[])}
    for index,post in enumerate(evidence.get('posts',[])):
        post['caption']=post.get('caption','')[:160 if index<20 else 60];post.pop('url',None)
        if not post.get('metric_sources'):post.pop('metric_sources',None)
    for comment in evidence.get('comments',[]):
        if comment.get('source_kind')!='comment' and parents.get(comment.get('post_id')):
            c['source_index'].pop(comment['source_id'],None)
            comment['source_id']=parents[comment['post_id']]
        comment['text']=comment.get('text','')[:500]
        for key in ('id','author','post_caption','post_url','source_url','post_type','posted_at'):comment.pop(key,None)
    size=lambda:len(json.dumps(c,ensure_ascii=False,separators=(',',':')))
    for kind in ('comments','posts'):
        rows=evidence.get(kind,[])
        floor=min(12,len(rows)) if kind=='comments' else 0
        while len(rows)>floor and size()>budget-600:
            removed=rows.pop()
            if removed['source_id'].startswith('C'):c.get('source_index',{}).pop(removed['source_id'],None)
    used={r['source_id'] for kind in ('posts','comments') for r in evidence.get(kind,[])}
    c['source_index']={key:value for key,value in c.get('source_index',{}).items() if key in used}
    c['evidence_coverage']={**c.get('evidence_coverage',{}),'posts_in_context':len(evidence.get('posts',[])),
                            'comments_in_context':len(evidence.get('comments',[]))}
    c['context_note']='Summaries use the full collected dataset. Quoted evidence is bounded; coverage reports how many records are included.'
    c['model_context_version']=1
    return c
