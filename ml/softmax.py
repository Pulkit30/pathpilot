"""Softmax (multinomial logistic regression) classifier written from scratch with NumPy.

Forward:   logits = X @ W + b                  (n, k)
           P      = softmax(logits)            probabilities per career, rows sum to 1
Loss:      L = -mean(log P[i, y_i]) + (l2 / 2) * ||W||^2      (cross-entropy + L2 regularisation)
Gradient:  dL/dlogits = (P - Y) / n            (Y = one-hot labels)
           dW = X.T @ dlogits + l2 * W
           db = sum(dlogits, axis=0)
Training:  mini-batch gradient descent with momentum.
"""

import numpy as np


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)  # subtracting the row max avoids overflow in exp
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def one_hot(y, n_classes):
    Y = np.zeros((len(y), n_classes))
    Y[np.arange(len(y)), y] = 1.0
    return Y


class SoftmaxClassifier:
    def __init__(self, lr=0.5, l2=1e-5, epochs=100, batch_size=64, momentum=0.9, seed=0):
        self.lr = lr
        self.l2 = l2
        self.epochs = epochs
        self.batch_size = batch_size
        self.momentum = momentum
        self.seed = seed
        self.W = None
        self.b = None

    # ---------------------------------------------------------------- maths ----

    def predict_proba(self, X):
        return softmax(X @ self.W + self.b)

    def predict(self, X):
        return self.predict_proba(X).argmax(axis=1)

    def loss(self, X, y, regularized=True):
        """Cross-entropy; with regularized=True also the L2 penalty (the quantity being minimised)."""
        P = self.predict_proba(X)
        nll = -np.log(P[np.arange(len(y)), y] + 1e-12).mean()
        return nll + 0.5 * self.l2 * np.sum(self.W ** 2) if regularized else nll

    def gradients(self, X, y):
        n = len(y)
        dlogits = (self.predict_proba(X) - one_hot(y, self.W.shape[1])) / n
        dW = X.T @ dlogits + self.l2 * self.W
        db = dlogits.sum(axis=0)
        return dW, db

    # ------------------------------------------------------------- training ----

    def fit(self, X, y, n_classes, X_val=None, y_val=None, verbose=True):
        rng = np.random.default_rng(self.seed)
        n, d = X.shape
        self.W = np.zeros((d, n_classes))  # the loss is convex, so zero init is fine
        self.b = np.zeros(n_classes)
        vW, vb = np.zeros_like(self.W), np.zeros_like(self.b)
        history = []

        for epoch in range(1, self.epochs + 1):
            order = rng.permutation(n)  # shuffle each epoch
            for start in range(0, n, self.batch_size):
                idx = order[start:start + self.batch_size]
                dW, db = self.gradients(X[idx], y[idx])
                vW = self.momentum * vW - self.lr * dW
                vb = self.momentum * vb - self.lr * db
                self.W += vW
                self.b += vb

            record = {"epoch": epoch, "train_loss": self.loss(X, y, regularized=False),
                      "train_acc": float((self.predict(X) == y).mean())}
            if X_val is not None:
                record["val_loss"] = self.loss(X_val, y_val, regularized=False)
                record["val_acc"] = float((self.predict(X_val) == y_val).mean())
            history.append(record)
            if verbose and (epoch == 1 or epoch % 10 == 0 or epoch == self.epochs):
                line = f"  epoch {epoch:>3}  loss {record['train_loss']:.4f}  train acc {record['train_acc']:.3f}"
                if X_val is not None:
                    line += f"  val loss {record['val_loss']:.4f}  val acc {record['val_acc']:.3f}"
                print(line)
        return history

    # ---------------------------------------------------------- persistence ----

    def save(self, path):
        np.savez(path, W=self.W, b=self.b)

    @classmethod
    def load(cls, path):
        data = np.load(path)
        clf = cls()
        clf.W, clf.b = data["W"], data["b"]
        return clf
