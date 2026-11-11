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
from .evidence import build_evidence, ANALYSIS_VERSION

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
    # Many platforms hide view counts on image posts; fall back to a likes-based estimate only when all are missing.
    if df["views"].sum() == 0 and not any("views" in p.unavailable_metrics for p in posts):
        df["views"] = (df["likes"] + df["comments"] * 3 + df["saves"] * 2 + df["shares"] * 3) * 10
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
        out.append(Post(
            id=str(row.get("id", i)), type=str(row["type"]) if "type" in raw.columns and pd.notna(row["type"]) else "Photo",
            posted_at=pd.to_datetime(row["posted_at"]).to_pydatetime(), caption=str(row["caption"]) if "caption" in raw.columns and pd.notna(row["caption"]) else "",
            likes=num("likes"), comments=num("comments"), shares=num("shares"), saves=num("saves"), views=num("views"), sales=num("sales"), comments_sample=cs,
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


# ---------------- Predict + trend longevity ----------------
def predict(df: pd.DataFrame, horizon_weeks: int = 8) -> dict:
    weekly = df.set_index("posted_at")[["views", "engagement"]].resample("W").sum()
    y = weekly["views"].values.astype(float) + 1
    dates = [d.strftime("%Y-%m-%d") for d in weekly.index]
    history = [{"date": d, "value": int(v - 1)} for d, v in zip(dates, y)]
    if len(y) < 4:
        return {"history": history, "forecast": [], "accuracy": 0, "phase": "Peaking", "weeks_left": 2, "similar": 0, "growth": 0}

    model = ExponentialSmoothing(y, trend="add", damped_trend=True).fit()
    fc = np.asarray(model.forecast(horizon_weeks))
    resid = y - np.asarray(model.fittedvalues)
    sd = float(np.std(resid)) or 1.0
    last_date = weekly.index[-1]
    forecast = []
    for i, v in enumerate(fc, start=1):
        band = 1.64 * sd * np.sqrt(i)
        forecast.append({"date": (last_date + pd.Timedelta(weeks=i)).strftime("%Y-%m-%d"), "value": max(0, round(float(v))),
                         "low": max(0, round(float(v - band))), "high": round(float(v + band))})
    mape = float(np.mean(np.abs(resid) / y))
    accuracy = int(np.clip(round(100 * (1 - mape)), 40, 97))

    recent, prior = y[-3:].mean(), y[-6:-3].mean() if len(y) >= 6 else y[:-3].mean()
    ratio = recent / max(prior, 1)
    phase = "Rising" if ratio > 1.12 else "Declining" if ratio < 0.88 else "Peaking"

    weeks_left, similar = _longevity(y)
    return {"history": history, "forecast": forecast, "accuracy": accuracy, "phase": phase,
            "weeks_left": weeks_left, "similar": similar, "growth": _weekly_growth(y)}


def _longevity(y: np.ndarray, win: int = 4) -> tuple[int, int]:
    """Find past windows shaped like the current one (cosine similarity) and see how long they kept going."""
    if len(y) < win * 2 + 2:
        return 4, 0
    norm = lambda a: a / max(a.mean(), 1)  # noqa: E731
    cur = norm(y[-win:])
    cands, lengths = [], []
    for s in range(0, len(y) - win - 1):
        w = norm(y[s:s + win])
        sim = float(cosine_similarity(cur.reshape(1, -1), w.reshape(1, -1))[0, 0])
        if sim > 0.97:
            peak = y[s:s + win].max()
            k = 0
            for v in y[s + win:]:
                if v < 0.8 * peak:
                    break
                k += 1
            cands.append(s)
            lengths.append(k)
    if not lengths:
        return 4, 0
    return int(np.clip(round(float(np.median(lengths))) + 1, 1, 12)), len(lengths)


# ---------------- Correlation ----------------
def correlation(df: pd.DataFrame) -> dict:
    cols = [c for c in METRICS + ["sales"] if df[c].sum() > 0 and df[c].nunique() > 1]
    pairs, matrix = [], {}
    for i, a in enumerate(cols):
        matrix[a] = {}
        for b in cols:
            r = 1.0 if a == b else float(stats.spearmanr(df[a], df[b])[0])
            matrix[a][b] = round(0.0 if np.isnan(r) else r, 3)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            pairs.append({"a": a.capitalize(), "b": b.capitalize(), "v": round(abs(matrix[a][b]), 2)})
    pairs.sort(key=lambda p: -p["v"])
    scatter = {f"{a}|{b}": df[[a, b]].values.tolist() for a, b in [("views", "likes"), ("likes", "saves")] if a in cols and b in cols}
    return {"pairs": pairs, "matrix": matrix, "scatter": scatter}


# ---------------- Charts ----------------
def charts(df: pd.DataFrame) -> dict:
    out = {}
    for m in METRICS + ["sales"]:
        by_m = df.groupby(df["posted_at"].dt.to_period("M"))[m].sum()
        by_w = df.groupby(df["posted_at"].dt.to_period("W"))[m].sum()
        out[m] = {"month": [{"label": str(k), "value": int(v)} for k, v in by_m.items()],
                  "week": [{"label": str(k.start_time.date()), "value": int(v)} for k, v in by_w.items()]}
    out["post_type_share"] = [{"type": k, "pct": round(100 * v / len(df))} for k, v in df["type"].value_counts().items()]
    return out


# ---------------- Recommend ----------------
def recommend(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["rate"] = df["engagement"] / df["views"].clip(lower=1)
    best_type = df.groupby("type")["rate"].mean().sort_values(ascending=False)
    best_day = df.groupby(df["posted_at"].dt.day_name())["rate"].mean().sort_values(ascending=False)
    best_hour = df.groupby(df["posted_at"].dt.hour)["rate"].mean().sort_values(ascending=False)

    # content similarity: which top posts look alike (TF-IDF cosine) -> repeat that theme
    from sklearn.feature_extraction.text import TfidfVectorizer
    caps = df["caption"].replace("", "post")
    top_theme = None
    if caps.str.len().sum() > 20:
        tf = TfidfVectorizer(stop_words="english", max_features=300).fit(caps)
        top_idx = df["rate"].nlargest(1).index[0]
        sims = cosine_similarity(tf.transform([caps[top_idx]]), tf.transform(caps))[0]
        sims[top_idx] = -1
        j = int(np.argmax(sims))
        top_theme = {"best_post": caps[top_idx][:80], "most_similar": caps[j][:80], "similarity": round(float(sims[j]), 2)}

    actions = []
    t0 = best_type.index[0]
    actions.append({"rank": 1, "action": f"Post more {t0} content", "why": f"{t0} posts earn {best_type.iloc[0]*100:.1f}% engagement per view, the highest of your formats."})
    if len(best_day):
        actions.append({"rank": 2, "action": f"Publish on {best_day.index[0]} around {int(best_hour.index[0]):02d}:00", "why": "Highest engagement per view in your history."})
    dm = demand(df)
    if dm["ranking"] and (dm["ranking"][0]["q"] + dm["ranking"][0]["ask"]) > 0:
        actions.append({"rank": 3, "action": "Answer top audience questions in a follow-up post", "why": f"\"{dm['ranking'][0]['p']}\" drew the most questions and requests."})
    actions.append({"rank": len(actions) + 1, "action": "Reply to comments within the first hour", "why": "Early replies lift reach on every major platform."})
    return {"actions": actions, "best_type": {k: round(float(v), 4) for k, v in best_type.items()}, "theme": top_theme}


# ---------------- Orchestrator ----------------
def analyze(posts: list[Post]) -> dict:
    if len(posts) < MIN_POSTS:
        raise ValueError(f"Only {len(posts)} public posts with metrics were found; at least {MIN_POSTS} are needed.")
    df = to_frame(posts)
    evidence = build_evidence(posts)
    s, d, p, c = sentiment(df, evidence), demand(df), predict(df), correlation(df)
    counts = {"Likes": int(df.likes.sum()), "Dislikes": 0, "Comments": int(df.comments.sum()), "Saves": int(df.saves.sum()),
              "Sales": int(df.sales.sum()), "Views": int(df.views.sum())}
    # Dislikes are rarely public; use negative comments as the proxy.
    counts["Dislikes"] = sum(1 for r in df["comments_sample"] for t in r if _vader.polarity_scores(t)["compound"] <= -0.05)
    facts = {
        "weeks": p["weeks_left"], "phase": p["phase"], "acc": p["accuracy"],
        "pos": s["pos"], "neg": s["neg"], "neu": s["neu"],
        "keywords": s["keywords"], "posts": d["ranking"][:5], "pairs": c["pairs"][:6],
        "growth": p["growth"], "similar": p["similar"], "counts": counts,
    }
    return {"analysis_version": ANALYSIS_VERSION, "evidence": evidence, "facts": facts, "predict": p, "recommend": recommend(df), "charts": charts(df), "correlation": c,
            "sentiment": s, "demand": d, "post_count": len(df),
            "date_range": [df.posted_at.min().strftime("%Y-%m-%d"), df.posted_at.max().strftime("%Y-%m-%d")]}
