"""Join user-supplied counts to existing posts without replacing their evidence."""
import io
import zipfile
from urllib.parse import urlparse,parse_qsl,urlencode
import pandas as pd
from .evidence import restore_posts

METRICS = ('views', 'likes', 'comments', 'shares', 'saves', 'sales')


def canonical(value):
    if not isinstance(value, str) or not value.strip(): return ''
    try:
        u=urlparse(value.strip())
        if u.scheme not in ('http','https') or u.username or not u.hostname: return ''
        query=[(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith('utm_') and k.lower() not in {'utm','igsh','igshid','fbclid','mibextid','img_index'}]
        return u.hostname.lower().removeprefix('www.').removeprefix('m.')+u.path.rstrip('/')+('?' + urlencode(sorted(query)) if query else '')
    except ValueError: return ''


def merge_metrics(analysis, content, filename):
    posts=restore_posts(analysis.get('evidence',{}).get('posts',[]),analysis.get('profile') or {})
    if not posts: raise ValueError('Analyze a profile first.')
    # Restore exact comment evidence from the active result, not sentiment scores.
    from .schemas import CommentEvidence
    for post in posts:
        comments=[c for c in analysis.get('evidence',{}).get('comments',[]) if c.get('post_id')==post.id]
        post.comments_sample=[c['text'] for c in comments]
        post.comment_evidence=[CommentEvidence(id=c['id'].removeprefix(post.id+':'),text=c['text'],author=c.get('author',''),source_url=c.get('source_url',''),source_kind=c.get('source_kind','none'),posted_at=c.get('posted_at')) for c in comments]
    if filename.lower().endswith('.csv'):
        frame=pd.read_csv(io.BytesIO(content),dtype=str,keep_default_na=False)
    elif filename.lower().endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if sum(item.file_size for item in z.infolist())>50_000_000: raise ValueError('Expanded workbook is too large. Export a small CSV instead.')
        except zipfile.BadZipFile:
            raise ValueError('This is not a readable XLSX workbook. Export it again or use CSV.') from None
        frame=pd.read_excel(io.BytesIO(content),dtype=str,keep_default_na=False,engine='openpyxl')
    else: raise ValueError('Choose a CSV or XLSX metrics file.')
    frame.columns=[str(c).strip().lower().replace(' ','_') for c in frame.columns]
    frame=frame.rename(columns={'post_url':'url','post_id':'id','saved':'saves','plays':'views'})
    if frame.columns.duplicated().any(): raise ValueError('The file has duplicate column names.')
    if not any(c in frame.columns for c in ('id','url')): raise ValueError('Include an id or url column to match collected posts.')
    if not any(m in frame.columns for m in METRICS): raise ValueError('Include views, likes, comments, shares, saves or sales.')
    if len(frame)>5000: raise ValueError('Use at most 5,000 rows in a metrics file.')
    by_id={p.id:p for p in posts}; by_url={canonical(p.url):p for p in posts if canonical(p.url)}
    updated=set(); seen=set(); values=0
    for index,row in frame.iterrows():
        supplied={m:str(row[m]).strip() for m in METRICS if m in frame.columns and str(row[m]).strip()}
        if not supplied: continue
        row_id=str(row.get('id','')).strip(); row_url=canonical(row.get('url',''))
        id_post=by_id.get(row_id) if row_id else None; url_post=by_url.get(row_url) if row_url else None
        if row_id and row_url and (id_post is None or url_post is None or id_post.id!=url_post.id):
            raise ValueError(f'Row {index+2}: id and URL do not identify the same collected post.')
        post=id_post or url_post
        if not post: raise ValueError(f'Row {index+2}: this post is not part of the current analysis.')
        if post.id in seen: raise ValueError(f'Row {index+2}: duplicate post. Use one row per post.')
        seen.add(post.id)
        for metric,value in supplied.items():
            # Counts only. Reject fractions, shorthand, negative values and formulas.
            cleaned=value.replace(',','')
            if not cleaned.isascii() or not cleaned.isdigit() or int(cleaned)>10**15:
                raise ValueError(f'Row {index+2}: {metric} must be a non-negative whole-number count.')
            setattr(post,metric,int(cleaned)); post.unavailable_metrics=[m for m in post.unavailable_metrics if m!=metric]
            post.metric_sources[metric]='User-imported metrics'
            values+=1; updated.add(post.id)
    if not values: raise ValueError('No metric values were supplied. Blank cells leave existing values unchanged.')
    return posts, {'matched_posts':len(updated),'updated_values':values,'source':'User-imported metrics'}
