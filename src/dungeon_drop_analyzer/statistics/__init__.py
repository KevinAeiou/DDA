"""Funções puras de análise estatística (sem dependência de UI ou banco)."""

from .analysis import ItemAnalysis, analyze_items
from .effects import EffectSize, effect_size
from .homogeneity import TestResult, homogeneity_test, pairwise_tests
from .multiplicity import holm_adjust
from .proportions import (
    absent_upper_bound,
    insufficient_sample,
    runs_for_absent_limit,
    runs_for_margin,
    unseen_probability,
    wilson_half_width,
    wilson_interval,
    wilson_series,
)
from .trend import TrendResult, trend_test

__all__ = [
    "EffectSize",
    "ItemAnalysis",
    "TestResult",
    "TrendResult",
    "absent_upper_bound",
    "analyze_items",
    "effect_size",
    "holm_adjust",
    "homogeneity_test",
    "insufficient_sample",
    "pairwise_tests",
    "runs_for_absent_limit",
    "runs_for_margin",
    "trend_test",
    "unseen_probability",
    "wilson_half_width",
    "wilson_interval",
    "wilson_series",
]
