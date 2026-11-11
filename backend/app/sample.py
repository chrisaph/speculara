"""Deterministic demo dataset, used by /api/sample and the tests."""
from datetime import datetime, timedelta

import numpy as np

from .schemas import Post

POS = ["love it so much!", "amazing quality", "worth it, great drop", "obsessed with this", "best one yet"]
NEG = ["price is too high", "shipping took forever", "this looks like a scam", "not impressed"]
ASK = ["where to buy?", "please restock!", "can you make a tutorial?", "how much is it?", "more of this please"]
TYPES = ["Video", "Photo", "Carousel", "Reel"]
CAPS = ["Behind-the-scenes reel", "Product drop carousel", "Founder story video", "Live Q&A replay", "Giveaway photo post"]


def sample_posts(n: int = 40, seed: int = 7) -> list[Post]:
    r = np.random.default_rng(seed)
    start = datetime(2025, 1, 6, 12)
    posts = []
    for i in range(n):
        wk = i / 3
        base = 4000 + 900 * wk + 2500 * np.sin(wk / 2)
        views = int(base * r.uniform(0.7, 1.4))
        likes = int(views * r.uniform(0.05, 0.1)); comments = int(likes * r.uniform(0.04, 0.1))
        pool = POS * 2 + NEG + ASK
        posts.append(Post(
            id=str(i), type=TYPES[i % 4], posted_at=start + timedelta(days=i * 2.3, hours=int(r.integers(0, 8))),
            caption=f"{CAPS[i % 5]} #{i}", likes=likes, comments=comments, shares=int(likes * r.uniform(0.05, 0.2)),
            saves=int(likes * r.uniform(0.1, 0.4)), views=views, sales=int(likes * r.uniform(0.005, 0.02)),
            comments_sample=[pool[int(k)] for k in r.integers(0, len(pool), 8)],
        ))
    return posts
