"""
tests/synthetic_failures/scenarios.py — Failure Scenario Definitions (Unit 12).

Defines the 9 synthetic failure test cases for live demonstration and automated validation:
  1. wrong_container_count -> MISMATCH (container_count)
  2. wrong_weight          -> MISMATCH (gross_weight_kg)
  3. wrong_shipment_id     -> MISMATCH (shipper)
  4. unit_mismatch         -> MISMATCH (port_of_discharge)
  5. different_field_names -> OK (synonym dictionary alignment, no false alarm)
  6. missing_bl            -> NEEDS_REVIEW (missing_attachment)
  7. unreadable_document   -> NEEDS_REVIEW (unreadable)
  8. wrong_doc_type        -> NEEDS_REVIEW (wrong_doc_type)
  9. missing_value         -> NEEDS_REVIEW (missing_value)
"""

from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass
class SyntheticScenario:
    scenario_id: str
    name: str
    category: str  # "Defect Discrepancy" | "Escalation" | "Semantic Alignment"
    description: str
    expected_status: Literal["OK", "MISMATCH", "NEEDS_REVIEW"]
    expected_review_reason: Optional[str]
    expected_defect_fields: list[str]
    email_subject: str
    email_body: str
    si_filename: str
    si_text: str
    bl_filename: Optional[str] = None
    bl_text: Optional[str] = None
    bl_bytes: Optional[bytes] = None


BASE_SI = """SHIPPING INSTRUCTION
==============================================
SHIPMENT REF: SI-SYNTH-2026-01
SHIPPER: PACIFIC GLOBAL LOGISTICS PTE LTD, SINGAPORE
CONSIGNEE: NORDIC IMPORT SERVICES APS, COPENHAGEN, DENMARK
NOTIFY PARTY: NORDIC IMPORT SERVICES APS, COPENHAGEN
PORT OF LOADING: SINGAPORE (SGSIN)
PORT OF DISCHARGE: ROTTERDAM (NLRTM)
CONTAINER COUNT: 4 x 40HC CONTAINERS
GROSS WEIGHT: 42,500.00 KGS
==============================================
"""

BASE_BL = """BILL OF LADING
==============================================
B/L NUMBER: BL-SYNTH-2026-01
SHIPPER: PACIFIC GLOBAL LOGISTICS PTE LTD, SINGAPORE
CONSIGNEE: NORDIC IMPORT SERVICES APS, COPENHAGEN, DENMARK
NOTIFY PARTY: NORDIC IMPORT SERVICES APS, COPENHAGEN
PORT OF LOADING: SINGAPORE (SGSIN)
PORT OF DISCHARGE: ROTTERDAM (NLRTM)
CONTAINER COUNT: 4 x 40HC CONTAINERS
GROSS WEIGHT: 42,500.00 KGS
==============================================
"""

SCENARIOS: dict[str, SyntheticScenario] = {
    "wrong_container_count": SyntheticScenario(
        scenario_id="wrong_container_count",
        name="Wrong Container Count Mismatch",
        category="Defect Discrepancy",
        description="SI specifies 4 containers (4 x 40HC) but BL manifests only 2 containers (2 x 40HC).",
        expected_status="MISMATCH",
        expected_review_reason=None,
        expected_defect_fields=["container_count"],
        email_subject="Document Check: SI vs BL Container Count — SI-SYNTH-2026-01",
        email_body="Please verify the attached Shipping Instruction and draft Bill of Lading for container discrepancy.",
        si_filename="attachments/email_synth_wrong_container_count_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_wrong_container_count_BL.txt",
        bl_text=BASE_BL.replace("CONTAINER COUNT: 4 x 40HC CONTAINERS", "CONTAINER COUNT: 2 x 40HC CONTAINERS"),
    ),
    "wrong_weight": SyntheticScenario(
        scenario_id="wrong_weight",
        name="Wrong Gross Weight Mismatch",
        category="Defect Discrepancy",
        description="SI specifies 42,500.00 KGS but BL lists 58,200.00 KGS (exceeding weight tolerance).",
        expected_status="MISMATCH",
        expected_review_reason=None,
        expected_defect_fields=["gross_weight_kg"],
        email_subject="Weight Discrepancy Alert: SI vs BL — SI-SYNTH-2026-02",
        email_body="Attached SI and draft BL for weight validation prior to container terminal cutoff.",
        si_filename="attachments/email_synth_wrong_weight_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_wrong_weight_BL.txt",
        bl_text=BASE_BL.replace("GROSS WEIGHT: 42,500.00 KGS", "GROSS WEIGHT: 58,200.00 KGS"),
    ),
    "wrong_shipment_id": SyntheticScenario(
        scenario_id="wrong_shipment_id",
        name="Shipper Entity Mismatch",
        category="Defect Discrepancy",
        description="SI shipper is Pacific Global Logistics Pte Ltd but BL declares Atlantic Freight Forwarders Corp.",
        expected_status="MISMATCH",
        expected_review_reason=None,
        expected_defect_fields=["shipper"],
        email_subject="Shipper Verification Discrepancy — SI-SYNTH-2026-03",
        email_body="Please compare the shipper party on both documents and confirm alignment.",
        si_filename="attachments/email_synth_wrong_shipment_id_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_wrong_shipment_id_BL.txt",
        bl_text=BASE_BL.replace(
            "SHIPPER: PACIFIC GLOBAL LOGISTICS PTE LTD, SINGAPORE",
            "SHIPPER: ATLANTIC FREIGHT FORWARDERS CORP, PANAMA CITY"
        ),
    ),
    "unit_mismatch": SyntheticScenario(
        scenario_id="unit_mismatch",
        name="Port of Discharge Mismatch",
        category="Defect Discrepancy",
        description="SI lists Port of Discharge as Rotterdam (NLRTM) while BL mistakenly states Hamburg (DEHAM).",
        expected_status="MISMATCH",
        expected_review_reason=None,
        expected_defect_fields=["port_of_discharge"],
        email_subject="Destination Port Discrepancy — SI-SYNTH-2026-04",
        email_body="Destination port differs between SI and draft BL. Review urgently.",
        si_filename="attachments/email_synth_unit_mismatch_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_unit_mismatch_BL.txt",
        bl_text=BASE_BL.replace("PORT OF DISCHARGE: ROTTERDAM (NLRTM)", "PORT OF DISCHARGE: HAMBURG (DEHAM)"),
    ),
    "different_field_names": SyntheticScenario(
        scenario_id="different_field_names",
        name="Semantic Synonym Alignment",
        category="Semantic Alignment",
        description="Diverse field labels (Shipper (principal or seller), To the order of, Load Port, Discharge Port, Total Gross Weight) correctly mapped via synonym dictionary without false alarm.",
        expected_status="OK",
        expected_review_reason=None,
        expected_defect_fields=[],
        email_subject="Custom Carrier Format SI vs BL — SI-SYNTH-2026-05",
        email_body="Carrier uses alternate maritime terminology on draft BL. Validating semantic alignment.",
        si_filename="attachments/email_synth_different_field_names_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_different_field_names_BL.txt",
        bl_text="""BILL OF LADING
==============================================
B/L NUMBER: BL-SYNTH-2026-05
SHIPPER (PRINCIPAL OR SELLER): PACIFIC GLOBAL LOGISTICS PTE LTD, SINGAPORE
TO THE ORDER OF: NORDIC IMPORT SERVICES APS, COPENHAGEN, DENMARK
NOTIFY: NORDIC IMPORT SERVICES APS, COPENHAGEN
LOAD PORT: SINGAPORE (SGSIN)
DISCHARGE PORT: ROTTERDAM (NLRTM)
CONTAINERS: 4 x 40HC CONTAINERS
TOTAL GROSS WEIGHT: 42,500.00 KGS
==============================================
""",
    ),
    "missing_bl": SyntheticScenario(
        scenario_id="missing_bl",
        name="Missing BL Attachment Escalation",
        category="Escalation",
        description="Email arrives with Shipping Instruction only; Draft Bill of Lading attachment is missing entirely.",
        expected_status="NEEDS_REVIEW",
        expected_review_reason="missing_attachment",
        expected_defect_fields=[],
        email_subject="Missing Draft BL: Pending Documentation — SI-SYNTH-2026-06",
        email_body="Please find attached our Shipping Instruction. The carrier draft BL has not been received yet.",
        si_filename="attachments/email_synth_missing_bl_SI.txt",
        si_text=BASE_SI,
        bl_filename=None,
        bl_text=None,
    ),
    "unreadable_document": SyntheticScenario(
        scenario_id="unreadable_document",
        name="Unreadable / Corrupted Document Escalation",
        category="Escalation",
        description="Draft BL attachment is a 0-byte corrupt file. Pipeline flags unreadable without crashing.",
        expected_status="NEEDS_REVIEW",
        expected_review_reason="unreadable",
        expected_defect_fields=[],
        email_subject="Transmission Error Corrupt File — SI-SYNTH-2026-07",
        email_body="Forwarding documents received from agent. Note BL file transfer might be corrupted.",
        si_filename="attachments/email_synth_unreadable_document_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_unreadable_document_BL.txt",
        bl_text="",
        bl_bytes=b"",  # 0-byte unreadable file
    ),
    "wrong_doc_type": SyntheticScenario(
        scenario_id="wrong_doc_type",
        name="Wrong Document Type Escalation",
        category="Escalation",
        description="Commercial Invoice attached instead of a Bill of Lading. Escalates with wrong_doc_type reason.",
        expected_status="NEEDS_REVIEW",
        expected_review_reason="wrong_doc_type",
        expected_defect_fields=[],
        email_subject="Erroneous Attachment: Commercial Invoice Attached — SI-SYNTH-2026-08",
        email_body="Shipping Instruction attached alongside vendor Commercial Invoice by mistake.",
        si_filename="attachments/email_synth_wrong_doc_type_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_wrong_doc_type_BL.txt",
        bl_text="""COMMERCIAL INVOICE
==============================================
INVOICE NUMBER: INV-2026-9901
INVOICE DATE: 2026-09-15
SELLER / EXPORTER: PACIFIC GLOBAL LOGISTICS PTE LTD
BUYER / IMPORTER: NORDIC IMPORT SERVICES APS
TERMS OF DELIVERY: CIF ROTTERDAM
TOTAL INVOICE VALUE: USD 184,500.00
PACKING: 4 x 40HC CONTAINERS
==============================================
""",
    ),
    "missing_value": SyntheticScenario(
        scenario_id="missing_value",
        name="Missing Canonical Value Escalation",
        category="Escalation",
        description="Draft BL has placeholder '???' for gross weight. Escalates for missing value rather than fabricating mismatch.",
        expected_status="NEEDS_REVIEW",
        expected_review_reason="missing_value",
        expected_defect_fields=[],
        email_subject="Draft BL with Incomplete Weight — SI-SYNTH-2026-09",
        email_body="Please note carrier draft BL has pending tare/gross weight marked as ???.",
        si_filename="attachments/email_synth_missing_value_SI.txt",
        si_text=BASE_SI,
        bl_filename="attachments/email_synth_missing_value_BL.txt",
        bl_text=BASE_BL.replace("GROSS WEIGHT: 42,500.00 KGS", "GROSS WEIGHT: ???"),
    ),
}
