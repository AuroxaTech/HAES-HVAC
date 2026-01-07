"""
HAES HVAC - CORE Brain Approval Rules

Deterministic approval thresholds from RDD Section 3.
"""

from dataclasses import dataclass
from enum import Enum

from src.brains.core.schema import ApprovalDecision, ApprovalType


@dataclass
class ApprovalThreshold:
    """Approval threshold definition."""
    type: ApprovalType
    min_amount: float
    max_amount: float | None  # None = unlimited
    approver: str             # Role/name of approver
    rule_id: str              # Identifier for audit


# Approval thresholds from RDD Section 3
# Quote approvals
QUOTE_APPROVALS = [
    ApprovalThreshold(
        type=ApprovalType.QUOTE,
        min_amount=0,
        max_amount=20000,
        approver="auto",
        rule_id="quote_auto",
    ),
    ApprovalThreshold(
        type=ApprovalType.QUOTE,
        min_amount=20000,
        max_amount=1000000,
        approver="Linda",
        rule_id="quote_linda",
    ),
    ApprovalThreshold(
        type=ApprovalType.QUOTE,
        min_amount=1000000,
        max_amount=None,
        approver="Junior",
        rule_id="quote_junior",
    ),
]

# PO approvals
PO_APPROVALS = [
    ApprovalThreshold(
        type=ApprovalType.PURCHASE_ORDER,
        min_amount=0,
        max_amount=99,
        approver="auto",
        rule_id="po_auto",
    ),
    ApprovalThreshold(
        type=ApprovalType.PURCHASE_ORDER,
        min_amount=100,
        max_amount=500,
        approver="Linda",
        rule_id="po_linda",
    ),
    ApprovalThreshold(
        type=ApprovalType.PURCHASE_ORDER,
        min_amount=501,
        max_amount=None,
        approver="Junior",
        rule_id="po_junior",
    ),
]

# Capital equipment threshold (special rule)
CAPITAL_EQUIPMENT_THRESHOLD = 350
CAPITAL_EQUIPMENT_APPROVER = "Junior"

# Refund/Credit approvals
REFUND_APPROVALS = [
    ApprovalThreshold(
        type=ApprovalType.REFUND,
        min_amount=0,
        max_amount=0,
        approver="Technician/CSR",
        rule_id="refund_tech",
    ),
    ApprovalThreshold(
        type=ApprovalType.REFUND,
        min_amount=1,
        max_amount=99,
        approver="Anna",
        rule_id="refund_anna",
    ),
    ApprovalThreshold(
        type=ApprovalType.REFUND,
        min_amount=100,
        max_amount=None,
        approver="Linda",
        rule_id="refund_linda",
    ),
]

# Discount approvals (percentage-based)
DISCOUNT_APPROVALS = [
    ApprovalThreshold(
        type=ApprovalType.DISCOUNT,
        min_amount=0,
        max_amount=5,
        approver="auto",
        rule_id="discount_auto",
    ),
    ApprovalThreshold(
        type=ApprovalType.DISCOUNT,
        min_amount=6,
        max_amount=10,
        approver="Linda",
        rule_id="discount_linda",
    ),
    ApprovalThreshold(
        type=ApprovalType.DISCOUNT,
        min_amount=10.1,
        max_amount=None,
        approver="Junior",
        rule_id="discount_junior",
    ),
]


def get_approval_decision(
    approval_type: ApprovalType,
    amount: float,
    is_capital_equipment: bool = False,
) -> ApprovalDecision:
    """
    Determine approval requirement for an amount.
    
    Args:
        approval_type: Type of approval needed
        amount: Dollar amount (or percentage for discounts)
        is_capital_equipment: Whether this is capital equipment (PO only)
        
    Returns:
        ApprovalDecision with approver and rule info
    """
    # Select threshold list
    if approval_type == ApprovalType.QUOTE:
        thresholds = QUOTE_APPROVALS
    elif approval_type == ApprovalType.PURCHASE_ORDER:
        thresholds = PO_APPROVALS
        # Check capital equipment override
        if is_capital_equipment and amount > CAPITAL_EQUIPMENT_THRESHOLD:
            return ApprovalDecision(
                approval_required=True,
                approver=CAPITAL_EQUIPMENT_APPROVER,
                threshold_rule_id="po_capital_equipment",
                reason=f"Capital equipment over ${CAPITAL_EQUIPMENT_THRESHOLD}",
                amount=amount,
            )
    elif approval_type == ApprovalType.REFUND:
        thresholds = REFUND_APPROVALS
    elif approval_type == ApprovalType.DISCOUNT:
        thresholds = DISCOUNT_APPROVALS
    else:
        return ApprovalDecision(
            approval_required=True,
            approver="Junior",
            threshold_rule_id="unknown_type",
            reason="Unknown approval type - requires owner approval",
            amount=amount,
        )
    
    # Find matching threshold
    for threshold in thresholds:
        min_match = amount >= threshold.min_amount
        max_match = threshold.max_amount is None or amount <= threshold.max_amount
        
        if min_match and max_match:
            return ApprovalDecision(
                approval_required=threshold.approver != "auto",
                approver=threshold.approver if threshold.approver != "auto" else None,
                threshold_rule_id=threshold.rule_id,
                reason=f"Amount ${amount:.2f} falls in {threshold.rule_id} range",
                amount=amount,
            )
    
    # Default to owner approval if no threshold matched
    return ApprovalDecision(
        approval_required=True,
        approver="Junior",
        threshold_rule_id="default_owner",
        reason="No matching threshold - defaults to owner approval",
        amount=amount,
    )

