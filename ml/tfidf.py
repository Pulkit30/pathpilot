"""TF-IDF vectorizer written from scratch with NumPy.

TF  (term frequency)          how often a feature appears in this document
IDF (inverse doc frequency)   log((1 + N) / (1 + df)) + 1, so rare features weigh more than common ones
Each row is then L2-normalised, so documents of different lengths are comparable.
"""

import json
from collections import Counter

import numpy as np


class TfidfVectorizer:
    def __init__(self, min_df=1, sublinear_tf=True):
        self.min_df = min_df              # ignore features seen in fewer than min_df documents
        self.sublinear_tf = sublinear_tf  # use 1 + log(tf) so repeating a word has diminishing effect
        self.vocab = {}                   # feature -> column index
        self.idf = None

    def fit(self, docs):
        """docs: list of feature lists, e.g. [["python", "skill:python", "interest:ai"], ...]"""
        n_docs = len(docs)
        df = Counter()
        for doc in docs:
            df.update(set(doc))
        features = sorted(f for f, count in df.items() if count >= self.min_df)
        self.vocab = {f: i for i, f in enumerate(features)}
        counts = np.array([df[f] for f in features], dtype=np.float64)
        self.idf = np.log((1 + n_docs) / (1 + counts)) + 1.0
        return self

    def transform(self, docs):
        X = np.zeros((len(docs), len(self.vocab)), dtype=np.float64)
        for row, doc in enumerate(docs):
            for feature, count in Counter(doc).items():
                col = self.vocab.get(feature)
                if col is not None:  # features unseen during fit are ignored
                    X[row, col] = 1.0 + np.log(count) if self.sublinear_tf else count
        X *= self.idf
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        return X / np.where(norms == 0, 1.0, norms)  # all-zero rows stay zero

    def fit_transform(self, docs):
        return self.fit(docs).transform(docs)

    # ------------------------------------------------------------ persistence ----

    def save(self, npz_path, vocab_path):
        np.savez(npz_path, idf=self.idf, min_df=self.min_df, sublinear_tf=self.sublinear_tf)
        with open(vocab_path, "w", encoding="utf-8") as f:
            json.dump(sorted(self.vocab, key=self.vocab.get), f, indent=0, ensure_ascii=False)

    @classmethod
    def load(cls, npz_path, vocab_path):
        data = np.load(npz_path)
        vec = cls(min_df=int(data["min_df"]), sublinear_tf=bool(data["sublinear_tf"]))
        vec.idf = data["idf"]
        with open(vocab_path, encoding="utf-8") as f:
            vec.vocab = {feature: i for i, feature in enumerate(json.load(f))}
        return vec
