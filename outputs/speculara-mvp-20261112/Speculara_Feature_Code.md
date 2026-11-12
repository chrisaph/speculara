# Important feature code

Exact excerpts from the accompanying staging implementation. See the documentation/reviewer for explanation.

## Metric coverage

backend/app/insights.py:13

```python
def known(df, metric):
    return df[~df.unavailable_metrics.map(lambda missing: metric in missing)]


def availability(df):
    return {m: {'known_posts': len(known(df, m)), 'total_posts': len(df),
                'imported_posts':int(known(df,m).metric_sources.map(lambda sources: m in sources).sum()) if 'metric_sources' in df else 0,
                'total': int(known(df, m)[m].sum()) if len(known(df, m)) else None,
                'complete': len(known(df, m)) == len(df)} for m in METRICS}

```

## Forecast validation

backend/app/insights.py:79

```python
        wape=100*absolute_error/denom if denom else None
        accuracy = round(max(0,100-wape)) if wape is not None else None
        error = float(np.sqrt(np.mean((test-validation)**2)))
        result['accuracy'] = accuracy
        result['validation'].update(test_weeks=ntest, train_weeks=len(y)-ntest,
                                    start=weekly.index[-ntest].strftime('%Y-%m-%d'), end=weekly.index[-1].strftime('%Y-%m-%d'),
                                    weighted_error_pct=round(wape,1) if wape is not None else None,
                                    absolute_error=round(absolute_error,1),actual_total=int(denom),
                                    observations=[{'date':weekly.index[-ntest+i].strftime('%Y-%m-%d'),'actual':int(v),'predicted':round(float(validation[i]))} for i,v in enumerate(test)])
        result['model']={'last':'Last observed week','mean':'Recent four-week average','damped':'Damped exponential smoothing'}[method]
```

## Post similarity

backend/app/insights.py:189

```python
            score=.5*captions[i,j]+.3*comments[i,j]+.2*patterns[i,j]
            ranked.append({'id':other.id,'title':other.caption or f'{other.type} {other.id}','url':other.url,'type':other.type,
                           'score':round(100*float(score),1),'caption_similarity':round(float(captions[i,j]),3),
                           'comment_similarity':round(float(comments[i,j]),3),'metric_similarity':round(float(patterns[i,j]),3)})
        comparisons[str(row.id)]=sorted(ranked,key=lambda r:-r['score'])
    # The score describes similarity, not a success probability or sales relationship.
```

## Spearman correlation

backend/app/insights.py:142

```python
        rows=known(known(df,a),b)
        valid=len(rows)>=3 and rows[a].nunique()>1 and rows[b].nunique()>1
        value=round(float(stats.spearmanr(rows[a],rows[b]).statistic),3) if valid else None
        matrix[a][b]=matrix[b][a]=value
        if value is not None and np.isfinite(value):
            pairs.append({'a':a.capitalize(),'b':b.capitalize(),'v':value,'n':len(rows)})
            scatter[f'{a}|{b}']=[{'x':int(r[a]),'y':int(r[b]),'id':r['id'],'title':r['caption'] or r['type'],'url':r['url']} for _,r in rows.iterrows()]
        sample_sizes[f'{a}|{b}']=len(rows)
```

## Demand signals

backend/app/analytics.py:128

```python
        q = sum(1 for text in comments if QUESTION_RE.search(text))
        ask = sum(1 for text in comments if REQUEST_RE.search(text))
        demand_comments = sum(1 for text in comments if QUESTION_RE.search(text) or REQUEST_RE.search(text))
        sampled += len(comments)
        inquiries += demand_comments
        caption = (r["caption"] or r["type"]).strip().replace("\n", " ")
        rows.append({"p": caption[:80] + ("?" if len(caption) > 80 else ""), "q": q, "ask": ask,
```

## Filipino scoring

backend/app/text_sentiment.py:15

```python
def score_text(text):
    normalized=text.lower()
    normalized=re.sub(r'\bmahal kita\b','love you',normalized)
    normalized=re.sub(r'\b(?:hindi|di|hinde) lang\b','also',normalized)
    normalized=re.sub(r"(?<!\w)(?:hindi|hinde|'?di|walang)(?!\w)",'not',normalized)
    normalized=re.sub(r'\b(?:sobrang|sobra|napaka)\b','very',normalized)
    normalized=re.sub(r'([a-z])\1{2,}',r'\1',normalized)
    return _analyzer.polarity_scores(normalized)['compound']

METHOD='VADER with Filipino lexicon and negation rules'
```

## Gemma bounded request

backend/app/llm.py:113

```python
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemma_model}:generateContent"
    try:
        async with asyncio.timeout(180 if research else 130):
            async with httpx.AsyncClient(verify=ssl.create_default_context()) as client:
                for attempt in range(2):
                    request_body=body
                    if attempt and not research:
                        # Hosted Gemma can intermittently reject the system-instruction
                        # envelope. Keep the same instructions in its documented text form.
                        request_body={k:v for k,v in body.items() if k!='systemInstruction'}
                        request_body['contents']=[{'role':'user','parts':[{'text':f'Instructions:\n{instructions}\nEnd instructions.\n\n{prompt}'}]}]
                    try:
                        response = await client.post(endpoint, headers={"x-goog-api-key": s.gemma_api_key}, json=request_body,
                            timeout=180 if research else httpx.Timeout(60,connect=10))
                    except httpx.RequestError:
                        if not attempt:
                            await asyncio.sleep(5);continue
                        raise
                    if attempt==0 and response.status_code in (500,502,503,504):
                        await asyncio.sleep(5);continue
                    break
    except (httpx.TimeoutException,TimeoutError):
        raise LLMUnavailable('Gemma took too long to respond. Try again shortly; your analysis is still available.') from None
    except httpx.RequestError:
        raise LLMUnavailable("Cannot reach the Gemma API. Check the server connection and try again.") from None
    if response.status_code in (401, 403):
        raise LLMUnavailable("Google rejected the Gemma API key or project access. Check the backend key and API restrictions.")
    if response.status_code == 429:
```

## Post-count contract

backend/app/schemas.py:37

```python
class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=3, max_length=500)
    refresh: bool = False
    post_limit: int = Field(default=20, ge=5, le=50, strict=True)

```
