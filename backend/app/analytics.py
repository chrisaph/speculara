"""Pure-Python analytics for the six Speculara modules.

Input: a list of Post objects (collected by SocialMonitor or parsed from CSV/Excel).
Output: JSON-serialisable dict. Rendering happens in React.
"""
from __future__ import annotations

import io
import re
import warnings
from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics.pairwise import cosine_similarity
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .schemas import Post
from .evidence import build_evidence, ANALYSIS_VERSION, safe_url

warnings.filterwarnings("ignore")
_vader = SentimentIntensityAnalyzer()

MIN_POSTS = 5
METRICS = ["likes", "comments", "shares", "saves", "views"]
STOP = set(
    "a an and are as at be but by for from had has have he her his i if in into is it its just me my of on or our so than that the their them then there these they this to too us was we were what when where which who will with you your im ive dont cant it's i'm you're really very much yet even also get got can would could should about all any been do does how more most not now one out up very".split()
)
REQUEST_RE = re.compile(r"\b(please|pls|more|restock|tutorial|part 2|part two|link|drop|make a|do a|can you|could you|need)\b", re.I)
QUESTION_RE = re.compile(r"\?|\b(where|how much|price|how do|what is|when|which|does it|do you|is it)\b", re.I)


def _label(c: float) -> str:
    return "pos" if c >= 0.05 else "neg" if c <= -0.05 else "neu"


def to_frame(posts: list[Post]) -> pd.DataFrame:
    df = pd.DataFrame([p.model_dump() for p in posts])
    df["posted_at"] = pd.to_datetime(df["posted_at"], utc=True).dt.tz_localize(None)
    df = df.sort_values("posted_at").reset_index(drop=True)
    df["engagement"] = df["likes"] + df["comments"] + df["shares"] + df["saves"]
    return df


def posts_from_file(content: bytes, filename: str) -> list[Post]:
    """Parse an uploaded CSV/Excel entirely in memory (io.BytesIO); nothing touches disk."""
    buf = io.BytesIO(content)
    name = filename.lower()
    if name.endswith(".csv"):
        raw = pd.read_csv(buf)
    elif name.endswith((".xlsx", ".xlsm")):
        raw = pd.read_excel(buf, engine="openpyxl")
    elif name.endswith(".xls"):
        raw = pd.read_excel(buf, engine="xlrd")
    else:
        raise ValueError("Upload a .csv, .xlsx or .xls file.")
    raw.columns = [str(c).strip().lower().replace(" ", "_") for c in raw.columns]
    alias = {"date": "posted_at", "timestamp": "posted_at", "text": "caption", "type": "type"}
    raw = raw.rename(columns={k: v for k, v in alias.items() if k in raw.columns and v not in raw.columns})
    if "posted_at" not in raw.columns:
        raise ValueError("The file needs a date column (posted_at, date or timestamp).")
    out: list[Post] = []
    for i, row in raw.iterrows():
        if pd.isna(row["posted_at"]):
            continue
        num = lambda k: int(row[k]) if k in raw.columns and pd.notna(row[k]) else 0  # noqa: E731
        cs = str(row["comments_sample"]).split("|") if "comments_sample" in raw.columns and pd.notna(row["comments_sample"]) else []
        missing = [m for m in ['likes', 'comments', 'shares', 'saves', 'views', 'sales'] if m not in raw.columns or pd.isna(row[m])]
        out.append(Post(
            id=str(row.get("id", i)), type=str(row["type"]) if "type" in raw.columns and pd.notna(row["type"]) else "Photo",
            posted_at=pd.to_datetime(row["posted_at"]).to_pydatetime(), caption=str(row["caption"]) if "caption" in raw.columns and pd.notna(row["caption"]) else "",
            likes=num("likes"), comments=num("comments"), shares=num("shares"), saves=num("saves"), views=num("views"), sales=num("sales"), comments_sample=cs,
            unavailable_metrics=missing, url=safe_url(row.get('url', row.get('post_url', ''))),
            metric_sources={m:'Uploaded file' for m in ['likes','comments','shares','saves','views','sales'] if m not in missing},
        ))
    return out


# ---------------- Sentiment ----------------
def sentiment(df: pd.DataFrame, evidence: dict) -> dict:
    samples = [dict(c, kind="comment") for c in evidence["comments"]]
    basis = "comments" if samples else "captions"
    if not samples:
        samples = [{"id": f"caption:{p['id']}", "text": p["caption"], "kind": "caption", "post_id": p["id"],
                    "post_type": p["type"], "posted_at": p["posted_at"], "post_url": p["url"],
                    "source_url": p["url"], "source_kind": "post" if p["url"] else "none"}
                   for p in evidence["posts"] if p["caption"].strip()]
    if not samples:
        basis = "none"
    for sample in samples:
        score = _vader.polarity_scores(sample["text"])["compound"]
        sample.update(score=round(score, 4), tone=_label(score))
    counts = Counter(c["tone"] for c in samples)
    n = len(samples)
    pos = round(100 * counts["pos"] / n) if n else 0
    neg = round(100 * counts["neg"] / n) if n else 0
    words, tones, references = Counter(), {}, {}
    for sample in samples:
        for word in {w for w in re.findall(r"[a-z']{3,}", sample["text"].lower()) if w not in STOP}:
            words[word] += 1
            tones.setdefault(word, []).append(sample["score"])
            references.setdefault(word, []).append(sample["id"])
    keywords = [{"w": word, "n": count, "s": _label(float(np.mean(tones[word]))), "sample_ids": references[word]}
                for word, count in words.most_common(15)]
    by_type = []
    for ty in sorted({c["post_type"] for c in samples}):
        group = [c for c in samples if c["post_type"] == ty]
        labels = Counter(c["tone"] for c in group)
        positive = round(100 * labels["pos"] / len(group))
        negative = round(100 * labels["neg"] / len(group))
        by_type.append({"type": ty, "posts": len({c["post_id"] for c in group}), "scored": len(group),
                        "pos": positive, "neg": negative, "neu": 100 - positive - negative,
                        "sentiment": round(float(np.mean([c["score"] for c in group])), 3)})
    return {"pos": pos, "neg": neg, "neu": 100 - pos - neg if n else 0,
            "keywords": keywords, "by_post_type": by_type, "scored": n, "basis": basis, "samples": samples,
            "comment_sample_count": len(evidence["comments"])}


# ---------------- Demand ----------------
def demand(df: pd.DataFrame) -> dict:
    rows, periods = [], []
    sampled, inquiries = 0, 0
    for _, r in df.iterrows():
        comments = r["comments_sample"]
        q = sum(1 for text in comments if QUESTION_RE.search(text))
        ask = sum(1 for text in comments if REQUEST_RE.search(text))
        demand_comments = sum(1 for text in comments if QUESTION_RE.search(text) or REQUEST_RE.search(text))
        sampled += len(comments)
        inquiries += demand_comments
        caption = (r["caption"] or r["type"]).strip().replace("\n", " ")
        rows.append({"p": caption[:80] + ("?" if len(caption) > 80 else ""), "q": q, "ask": ask,
                     "post_id": r["id"], "type": r["type"], "url": r["url"], "sampled_comments": len(comments)})
        periods.append({"date": r["posted_at"], "questions": q, "requests": ask})
    ranking = sorted(rows, key=lambda x: -(x["q"] + x["ask"]))[:6]
    weekly = pd.DataFrame(periods).set_index("date")[["questions", "requests"]].resample("W").sum()
    totals = weekly.sum(axis=1)
    series = totals.values.astype(float)
    forecast = []
    if len(series) >= 6 and series.sum() > 0:
        try:
            model = ExponentialSmoothing(series, trend="add", damped_trend=True).fit()
            forecast = [max(0, round(float(x))) for x in model.forecast(4)]
        except Exception:
            forecast = [round(float(series[-4:].mean()))] * 4
    monthly = totals.groupby(totals.index.month).sum()
    summary = {"questions": sum(r["q"] for r in rows), "requests": sum(r["ask"] for r in rows),
               "sampled_comments": sampled, "demand_comments": inquiries,
               "request_rate_pct": round(100 * inquiries / sampled, 1) if sampled else None}
    return {"ranking": ranking, "summary": summary, "basis": "sampled_comments" if sampled else "none",
            "weekly": [{"date": date.strftime("%Y-%m-%d"), "questions": int(row.questions), "requests": int(row.requests)}
                       for date, row in weekly.iterrows()],
            "weekly_growth_pct": _weekly_growth(series), "demand_forecast": forecast,
            "peak_month": int(monthly.idxmax()) if len(monthly) and monthly.sum() > 0 else None}


def _weekly_growth(series: np.ndarray) -> int:
    if len(series) < 2:
        return 0
    last = series[-4:]
    g = np.diff(last) / np.maximum(last[:-1], 1)
    return int(round(float(np.mean(g)) * 100))


from .insights import predict, correlation, charts, recommend, availability


# ---------------- Orchestrator ----------------
def analyze(posts: list[Post]) -> dict:
    if len(posts) < MIN_POSTS:
        raise ValueError(f"Only {len(posts)} public posts with metrics were found; at least {MIN_POSTS} are needed.")
    df = to_frame(posts)
    evidence = build_evidence(posts)
    s, d, p, c = sentiment(df, evidence), demand(df), predict(df), correlation(df)
    coverage = availability(df)
    counts = {m.capitalize(): c['total'] for m,c in coverage.items()}
    counts['Dislikes'] = None  # Negative comments are not measured dislikes.
    facts = {
        "weeks": p["weeks_left"], "phase": p["phase"], "acc": p["accuracy"],
        "pos": s["pos"], "neg": s["neg"], "neu": s["neu"],
        "keywords": s["keywords"], "posts": d["ranking"][:5], "pairs": c["pairs"][:6],
        "growth": p["growth"], "similar": p["similar"], "counts": counts,
    }
    return {"analysis_version": ANALYSIS_VERSION, "metric_availability": coverage, "evidence": evidence, "facts": facts, "predict": p, "recommend": recommend(df), "charts": charts(df), "correlation": c,
            "sentiment": s, "demand": d, "post_count": len(df),
            "date_range": [df.posted_at.min().strftime("%Y-%m-%d"), df.posted_at.max().strftime("%Y-%m-%d")]}
