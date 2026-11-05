"""The academic risk estimate: a Random Forest over marks only, explained by its real SHAP values.

The model learns from made-up students at startup, not from this school's records. It has no fee
input of any kind, because paying late says nothing about a student's ability. Fee follow-up is a
separate flag (`fee_ledger.fee_follow_ups`).

There are two forests, with and without a trend. Most students have no midterm and final from the
same year, and a neutral value filled in for them would be invented data going into the model.
"""
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import RandomForestClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    RandomForestClassifier = None

try:
    import shap
except Exception as e:
    logger.warning(f"SHAP could not be loaded ({e}). Reasons will state the student's record instead.")
    shap = None

MODEL_NOTE = "Trained on synthetic data. Not validated on real students. A teacher should review before acting."

CATEGORY_HIGH = "High"
CATEGORY_MEDIUM = "Medium"
CATEGORY_LOW = "Low"
NOT_ENOUGH_DATA = "Not enough data"

HIGH_ABOVE_SCORE = 70
MEDIUM_FROM_SCORE = 40
# A model trained on made-up students has no grounds for certainty in either direction.
MIN_SCORE = 5
MAX_SCORE = 95

METHOD_SHAP = "shap"
METHOD_RECORD = "record"
_MAX_REASONS = 3

_BASE_FEATURES = ("avg_marks_pct", "failing_subjects")
_TREND_FEATURE = "grade_trend"
_TRAINING_ROWS = 600
_TRAINING_SEED = 42
_SUBJECT_COUNT = 6


def _score(probability: float) -> int:
    return min(MAX_SCORE, max(MIN_SCORE, int(round(probability * 100))))


def _category(score: int) -> str:
    if score > HIGH_ABOVE_SCORE:
        return CATEGORY_HIGH
    return CATEGORY_MEDIUM if score >= MEDIUM_FROM_SCORE else CATEGORY_LOW


def _synthetic_students(with_trend: bool) -> Tuple[np.ndarray, np.ndarray]:
    """Made-up students, labelled by a hand-written rule with some chance in it.

    This teaches the model the rule's general shape, nothing more. It is why every page says the
    model has not been validated.
    """
    random = np.random.RandomState(_TRAINING_SEED)
    rows, labels = [], []
    for _ in range(_TRAINING_ROWS):
        average = random.uniform(25, 98)
        failing = random.binomial(_SUBJECT_COUNT, float(np.clip((55 - average) / 45, 0.02, 0.8)))
        trend = random.uniform(-30, 20)

        points = 45 if average < 50 else (20 if average < 65 else 0)
        points += failing * 18
        if with_trend:
            points += 20 if trend < -10 else (8 if trend < 0 else 0)

        chance_at_risk = 1 / (1 + np.exp(-(points - 35) / 8))
        labels.append(int(random.random_sample() < chance_at_risk))
        rows.append([average, failing, trend] if with_trend else [average, failing])
    return np.array(rows), np.array(labels)


class TrainedModel:
    def __init__(self, with_trend: bool):
        self.features: Tuple[str, ...] = _BASE_FEATURES + ((_TREND_FEATURE,) if with_trend else ())
        rows, labels = _synthetic_students(with_trend)
        self.forest = RandomForestClassifier(
            n_estimators=120, max_depth=5, min_samples_leaf=5, random_state=_TRAINING_SEED
        ).fit(rows, labels)
        self.explainer: Any = None
        self.base_value: float = 0.0
        if shap is not None:
            try:
                self.explainer = shap.TreeExplainer(self.forest)
                self.base_value = float(np.ravel(self.explainer.expected_value)[-1])
            except Exception as error:
                logger.warning(f"SHAP explainer unavailable: {error}")
                self.explainer = None

    def contributions(self, row: np.ndarray) -> np.ndarray:
        """How much each input moved this student's probability of being at risk, away from the base value."""
        values = self.explainer.shap_values(row.reshape(1, -1))
        if isinstance(values, list):
            return np.asarray(values[1][0])
        values = np.asarray(values)
        return values[0, :, 1] if values.ndim == 3 else values[0]


def _row_for(model: TrainedModel, features: Dict[str, Any]) -> np.ndarray:
    return np.array([float(features[name]) for name in model.features])


def _has_trend(features: Dict[str, Any]) -> bool:
    return features.get(_TREND_FEATURE) is not None


def _fact(feature: str, features: Dict[str, Any]) -> str:
    """A plain statement from the student's record, for a feature the model used."""
    if feature == "avg_marks_pct":
        return f"Average of {float(features['avg_marks_pct']):.1f}% in the latest exam"
    if feature == "failing_subjects":
        count = int(features["failing_subjects"])
        return "No failed subjects" if count == 0 else f"Failed {count} subject{'s' if count > 1 else ''}"
    change = float(features[_TREND_FEATURE])
    if change == 0:
        return "Average unchanged from Midterm to Final Term"
    word = "fell" if change < 0 else "rose"
    return f"Average {word} {abs(change):.1f} points from Midterm to Final Term"


def _metrics(features: Dict[str, Any]) -> Dict[str, Any]:
    average = features.get("avg_marks_pct")
    trend = features.get(_TREND_FEATURE)
    return {
        "avg_marks_pct": round(float(average), 1) if average is not None else None,
        "failing_subjects": int(features.get("failing_subjects") or 0),
        "grade_trend": round(float(trend), 1) if trend is not None else None,
        "subjects_counted": features.get("subjects_counted"),
    }


def _assessment(
    features: Dict[str, Any],
    score: Optional[int],
    factors: Sequence[Dict[str, Any]] = (),
    reasons: Sequence[str] = (),
    method: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "risk_score": score,
        "risk_category": _category(score) if score is not None else NOT_ENOUGH_DATA,
        "factors": list(factors),
        "top_reasons": list(reasons),
        "explanation_method": method,
        "metrics": _metrics(features),
    }


class AtRiskModelService:
    def __init__(self):
        self.models: Dict[bool, TrainedModel] = {}
        if ML_AVAILABLE:
            self.models = {False: TrainedModel(with_trend=False), True: TrainedModel(with_trend=True)}

    def _can_score(self, features: Dict[str, Any]) -> bool:
        return bool(self.models) and features.get("has_enough_marks", True)

    def predict_student_risk(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """One student's estimate with its explanation."""
        if not self._can_score(features):
            return _assessment(features, None)
        model = self.models[_has_trend(features)]
        row = _row_for(model, features)
        score = _score(float(model.forest.predict_proba(row.reshape(1, -1))[0][1]))

        factors = self._shap_factors(model, row, features)
        if factors:
            reasons = [f"{factor['text']}: {factor['direction']} concern" for factor in factors[:_MAX_REASONS]]
            return _assessment(features, score, factors, reasons, METHOD_SHAP)
        reasons = [_fact(name, features) for name in model.features]
        return _assessment(features, score, (), reasons, METHOD_RECORD)

    def predict_many(self, all_features: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scores for a list, in the same order, without explanations, which are only worth their cost one at a time."""
        results: List[Dict[str, Any]] = [_assessment(features, None) for features in all_features]
        for with_trend, model in self.models.items():
            indexes = [
                index for index, features in enumerate(all_features)
                if self._can_score(features) and _has_trend(features) == with_trend
            ]
            if not indexes:
                continue
            rows = np.array([_row_for(model, all_features[index]) for index in indexes])
            for index, probability in zip(indexes, model.forest.predict_proba(rows)[:, 1]):
                results[index] = _assessment(all_features[index], _score(float(probability)))
        return results

    @staticmethod
    def _shap_factors(model: TrainedModel, row: np.ndarray, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """The model's own reasons, largest first. Empty if SHAP is unavailable or cannot explain this row."""
        if model.explainer is None:
            return []
        try:
            values = model.contributions(row)
        except Exception as error:
            logger.warning(f"Error computing SHAP values: {error}")
            return []
        factors = []
        for name, value in zip(model.features, values):
            impact = round(float(value) * 100)
            if impact != 0:
                factors.append({
                    "feature": name,
                    "text": _fact(name, features),
                    "impact": impact,
                    "direction": "raises" if value > 0 else "lowers",
                })
        return sorted(factors, key=lambda factor: abs(factor["impact"]), reverse=True)


# Global AI Service instance
ai_service = AtRiskModelService()
