# Thin wrapper so code can import KPIs without reaching into scripts/
from scripts.evaluation.hover_kpi_report import compute_hover_kpis  # re-export

__all__ = ["compute_hover_kpis"]
