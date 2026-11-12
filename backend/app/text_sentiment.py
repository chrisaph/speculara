"""English/Filipino rule-based sentiment; retain negation rather than matching substrings."""
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer=SentimentIntensityAnalyzer()
_analyzer.lexicon.update({
    'ganda':2.7,'maganda':2.7,'gandang':2.7,'napakaganda':3.2,'kaganda':2.7,
    'galing':2.5,'magaling':2.5,'anghusay':2.6,'husay':2.6,'sulit':2.4,'ayos':1.8,
    'astig':2.5,'bongga':2.5,'panalo':2.3,'salamat':1.8,'gusto':1.8,'bet':1.6,
    'pangit':-2.7,'panget':-2.7,'bulok':-2.8,'sira':-2.3,'palpak':-2.7,
    'nakakainis':-2.5,'nakakadismaya':-2.5,'sayang':-1.5,'mabagal':-1.8,
})


def score_text(text):
    normalized=text.lower()
    normalized=re.sub(r'\bmahal kita\b','love you',normalized)
    normalized=re.sub(r'\b(?:hindi|di|hinde) lang\b','also',normalized)
    normalized=re.sub(r"(?<!\w)(?:hindi|hinde|'?di|walang)(?!\w)",'not',normalized)
    normalized=re.sub(r'\b(?:sobrang|sobra|napaka)\b','very',normalized)
    normalized=re.sub(r'([a-z])\1{2,}',r'\1',normalized)
    return _analyzer.polarity_scores(normalized)['compound']

METHOD='VADER with Filipino lexicon and negation rules'
