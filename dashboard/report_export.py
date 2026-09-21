"""
dashboard/report_export.py — Convenient top-level re-export for PDF report generation.
"""

from dashboard.backend.report_export import generate_shipment_report_pdf

__all__ = ["generate_shipment_report_pdf"]
