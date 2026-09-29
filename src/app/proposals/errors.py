class ProposalGenerationError(RuntimeError):
    """Proposal content or output could not be generated safely."""

    code = "proposal_generation_failed"


class PricingIntegrityError(ProposalGenerationError):
    """Pricing values do not reconcile with authoritative line items."""

    code = "pricing_integrity_failed"


class PDFConversionError(ProposalGenerationError):
    """DOCX to PDF conversion failed or produced an invalid PDF."""

    code = "pdf_conversion_failed"
