"""Funções puras de análise estatística (sem dependência de UI ou banco)."""

from .analysis import ItemAnalysis, analyze_items
from .effects import EffectSize, effect_size
from .homogeneity import TestResult, homogeneity_test, pairwise_tests
from .multiplicity import holm_adjust
from .proportions import insufficient_sample, wilson_interval
from .trend import TrendResult, trend_test

__all__ = [
    "EffectSize",
    "ItemAnalysis",
    "TestResult",
    "TrendResult",
    "analyze_items",
    "effect_size",
    "holm_adjust",
    "homogeneity_test",
    "insufficient_sample",
    "pairwise_tests",
    "trend_test",
    "wilson_interval",
]
