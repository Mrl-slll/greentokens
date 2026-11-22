"""Bounded, approved CPU training; no user-provided code executes here."""
from statistics import linear_regression, mean


def train_linear(data):
    slope, intercept = linear_regression(data["x"], data["y"])
    mse = mean((slope * x + intercept - y) ** 2 for x, y in zip(data["x"], data["y"]))
    return {"model_type": "linear_regression", "slope": slope, "intercept": intercept,
            "training_mse": mse, "samples": len(data["x"]),
            "prediction": "y = slope * x + intercept"}
