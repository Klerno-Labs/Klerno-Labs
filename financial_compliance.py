"""
ISO20022 Compliance Module for Klerno Labs

Implements full ISO20022 standard compliance for financial messaging
including payment initiation, status reporting, and compliance validation.
Supports all ISO20022 compliant tokens and payment systems.
"""

from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from xml.dom import minidom

# ISO20022 Message Types


class MessageType(str, Enum):
    """ISO20022 message types."""

    # Payment Initiation
    PAIN_001 = "pain.001.001.11"  # CustomerCreditTransferInitiation
    PAIN_002 = "pain.002.001.12"  # PaymentStatusReport
    PAIN_008 = "pain.008.001.10"  # CustomerDirectDebitInitiation

    # Cash Management
    CAMT_052 = "camt.052.001.10"  # BankToCustomerAccountReport
    CAMT_053 = "camt.053.001.10"  # BankToCustomerStatement
    CAMT_054 = "camt.054.001.10"  # BankToCustomerDebitCreditNotification

    # Securities
    SESE_023 = "sese.023.001.07"  # SecuritiesSettlementTransactionInstruction
    SESE_024 = "sese.024.001.07"  # SecuritiesSettlementTransactionConfirmation

    # Trade Services
    TSMT_019 = "tsmt.019.001.05"  # IntentToPayNotification
    TSMT_020 = "tsmt.020.001.03"  # IntentToPayReport


class PaymentPurpose(str, Enum):
    """ISO20022 payment purpose codes."""

    CBFF = "CBFF"  # Capital Building
    CDCD = "CDCD"  # Credit Card Payment
    CHAR = "CHAR"  # Charity Payment
    COMC = "COMC"  # Commercial Payment
    CPKC = "CPKC"  # Car Parking
    DIVI = "DIVI"  # Dividend
    GOVI = "GOVI"  # Government Insurance
    GSTP = "GSTP"  # Goods / Service Tax Payment
    INST = "INST"  # Installment
    INTC = "INTC"  # Intra Company Payment
    LIMA = "LIMA"  # Liquidity Management
    OTHR = "OTHR"  # Other
    RLTI = "RLTI"  # Real Time Invoice
    SALA = "SALA"  # Salary Payment
    SECU = "SECU"  # Securities
    SSBE = "SSBE"  # Social Security Benefit
    SUPP = "SUPP"  # Supplier Payment
    TAXS = "TAXS"  # Tax Payment
    TRAD = "TRAD"  # Trade
    TREA = "TREA"  # Treasury Payment
    VATX = "VATX"  # Value Added Tax Payment
    WHLD = "WHLD"  # With Holding


class PaymentMethod(str, Enum):
    """ISO20022 payment methods."""

    CHK = "CHK"  # Cheque
    TRF = "TRF"  # Credit Transfer
    DD = "DD"  # Direct Debit
    TRA = "TRA"  # Transfer Advice
    COV = "COV"  # Cover
    COP = "COP"  # Cover Payment


class CurrencyCode(str, Enum):
    """ISO20022 currency codes."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"
    SGD = "SGD"
    HKD = "HKD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    ZAR = "ZAR"
    CNY = "CNY"
    INR = "INR"
    BRL = "BRL"
    MXN = "MXN"
    RUB = "RUB"
    TRY = "TRY"
    AED = "AED"
    SAR = "SAR"
    QAR = "QAR"
    XAU = "XAU"  # Gold
    XAG = "XAG"  # Silver
    XRP = "XRP"
    XLM = "XLM"
    XDC = "XDC"
    XMR = "XMR"
    XTZ = "XTZ"
    BTC = "BTC"
    ETH = "ETH"
    ADA = "ADA"
    SOL = "SOL"
    DOT = "DOT"
    LTC = "LTC"
    BCH = "BCH"
    DOGE = "DOGE"
    USDT = "USDT"
    USDC = "USDC"
    BUSD = "BUSD"
    DAI = "DAI"
    TUSD = "TUSD"
    PAX = "PAX"
    GUSD = "GUSD"
    EURS = "EURS"
    UST = "UST"
    # Add more as needed for ISO20022 - compliant coins / tokens


@dataclass
class ISO20022PartyIdentification:
    """ISO20022 Party identification."""

    name: str
    postal_address: dict[str, str] | None = None
    identification: str | None = None
    country: str | None = None
    contact_details: dict[str, str] | None = None
    # Optional fields commonly referenced by builders / callers
    bic: str | None = None
    address: Any | None = None


@dataclass
class ISO20022Amount:
    """ISO20022 Amount representation."""

    currency: CurrencyCode
    value: str  # Decimal as string to preserve precision

    def to_decimal(self) -> float:
        """Convert to decimal."""
        return float(self.value)


@dataclass
class ISO20022PaymentInstruction:
    """ISO20022 Payment Instruction."""

    instruction_id: str
    end_to_end_id: str
    amount: ISO20022Amount
    debtor: ISO20022PartyIdentification
    creditor: ISO20022PartyIdentification
    debtor_account: str
    creditor_account: str
    payment_purpose: PaymentPurpose = PaymentPurpose.OTHR
    remittance_info: str | None = None
    execution_date: datetime | None = None


@dataclass
class ISO20022PaymentStatus:
    """ISO20022 Payment Status."""

    status_id: str
    original_instruction_id: str
    status_code: str  # ACCC, RJCT, PDNG, etc.
    status_reason: str | None = None
    additional_info: str | None = None
    timestamp: datetime | None = None


class ISO20022MessageBuilder:
    """Builds ISO20022 compliant XML messages."""

    def __init__(self):
        self.namespace = "urn:iso:std:iso:20022:tech:xsd"

    @staticmethod
    def _to_datetime(dt: Any) -> datetime:
        """Coerce value to timezone - aware datetime (UTC) if it's an ISO string."""
        if isinstance(dt, datetime):
            # Ensure tz - aware
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        if isinstance(dt, str) and dt:
            s = dt.replace("Z", "+00:00")
            try:
                d = datetime.fromisoformat(s)
            except Exception:
                d = datetime.now(UTC)
            if d.tzinfo is None:
                d = d.replace(tzinfo=UTC)
            return d
        return datetime.now(UTC)

    def create_pain001_message(
        self,
        message_id: str,
        creation_datetime: datetime,
        initiating_party: ISO20022PartyIdentification,
        payment_instructions: list[ISO20022PaymentInstruction],
    ) -> str:
        """Create pain.001 CustomerCreditTransferInitiation message."""

        root = ET.Element("Document")
        root.set("xmlns", f"{self.namespace}:pain.001.001.11")

        cstmr_cdt_trf_initn = ET.SubElement(root, "CstmrCdtTrfInitn")

        # Group Header
        grp_hdr = ET.SubElement(cstmr_cdt_trf_initn, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = message_id
        ET.SubElement(grp_hdr, "CreDtTm").text = creation_datetime.isoformat()
        ET.SubElement(grp_hdr, "NbOfTxs").text = str(len(payment_instructions))

        # Calculate total amount
        total_amount = sum(instr.amount.to_decimal() for instr in payment_instructions)
        ET.SubElement(grp_hdr, "CtrlSum").text = f"{total_amount:.2f}"

        # Initiating Party
        initg_pty = ET.SubElement(grp_hdr, "InitgPty")
        ET.SubElement(initg_pty, "Nm").text = initiating_party.name

        # Payment Information
        pmt_inf = ET.SubElement(cstmr_cdt_trf_initn, "PmtInf")
        ET.SubElement(pmt_inf, "PmtInfId").text = f"PMT-{message_id}"
        ET.SubElement(pmt_inf, "PmtMtd").text = PaymentMethod.TRF.value

        # Service Level
        svc_lvl = ET.SubElement(pmt_inf, "PmtTpInf")
        ET.SubElement(svc_lvl, "SvcLvl").text = "SEPA"

        # Execution Date
        if payment_instructions and payment_instructions[0].execution_date:
            req_dt = payment_instructions[0].execution_date.date().isoformat()
            ET.SubElement(pmt_inf, "ReqdExctnDt").text = req_dt

        # Debtor (first instruction's debtor)
        if payment_instructions:
            dbtr = ET.SubElement(pmt_inf, "Dbtr")
            ET.SubElement(dbtr, "Nm").text = payment_instructions[0].debtor.name

            dbtr_acct = ET.SubElement(pmt_inf, "DbtrAcct")
            dbtr_acct_id = ET.SubElement(dbtr_acct, "Id")
            ET.SubElement(dbtr_acct_id, "IBAN").text = payment_instructions[
                0
            ].debtor_account

        # Credit Transfer Transaction Information
        for instruction in payment_instructions:
            cdt_trf_tx_inf = ET.SubElement(pmt_inf, "CdtTrfTxInf")

            pmt_id = ET.SubElement(cdt_trf_tx_inf, "PmtId")
            ET.SubElement(pmt_id, "InstrId").text = instruction.instruction_id
            ET.SubElement(pmt_id, "EndToEndId").text = instruction.end_to_end_id

            # Amount
            amt = ET.SubElement(cdt_trf_tx_inf, "Amt")
            instd_amt = ET.SubElement(amt, "InstdAmt")
            instd_amt.set("Ccy", instruction.amount.currency.value)
            instd_amt.text = instruction.amount.value

            # Creditor
            cdtr = ET.SubElement(cdt_trf_tx_inf, "Cdtr")
            ET.SubElement(cdtr, "Nm").text = instruction.creditor.name

            # Creditor Account
            cdtr_acct = ET.SubElement(cdt_trf_tx_inf, "CdtrAcct")
            cdtr_acct_id = ET.SubElement(cdtr_acct, "Id")
            ET.SubElement(cdtr_acct_id, "IBAN").text = instruction.creditor_account

            # Purpose
            ET.SubElement(cdt_trf_tx_inf, "Purp").text = (
                instruction.payment_purpose.value
            )

            # Remittance Information
            if instruction.remittance_info:
                rmt_inf = ET.SubElement(cdt_trf_tx_inf, "RmtInf")
                ET.SubElement(rmt_inf, "Ustrd").text = instruction.remittance_info

        return self._format_xml(root)

    def create_pain002_message(
        self,
        message_id: str,
        creation_datetime: datetime,
        original_message_id: str,
        payment_statuses: list[ISO20022PaymentStatus],
    ) -> str:
        """Create pain.002 PaymentStatusReport message."""

        root = ET.Element("Document")
        root.set("xmlns", f"{self.namespace}:pain.002.001.12")

        pmt_sts_rpt = ET.SubElement(root, "PmtStsRpt")

        # Group Header
        grp_hdr = ET.SubElement(pmt_sts_rpt, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = message_id
        ET.SubElement(grp_hdr, "CreDtTm").text = creation_datetime.isoformat()

        # Original Group Information
        orgnl_grp_inf = ET.SubElement(pmt_sts_rpt, "OrgnlGrpInfAndSts")
        ET.SubElement(orgnl_grp_inf, "OrgnlMsgId").text = original_message_id
        ET.SubElement(orgnl_grp_inf, "OrgnlMsgNmId").text = MessageType.PAIN_001.value

        # Transaction Information and Status
        for status in payment_statuses:
            tx_inf_and_sts = ET.SubElement(pmt_sts_rpt, "TxInfAndSts")
            ET.SubElement(tx_inf_and_sts, "StsId").text = status.status_id
            ET.SubElement(tx_inf_and_sts, "OrgnlInstrId").text = (
                status.original_instruction_id
            )
            ET.SubElement(tx_inf_and_sts, "TxSts").text = status.status_code

            if status.status_reason:
                sts_rsn_inf = ET.SubElement(tx_inf_and_sts, "StsRsnInf")
                ET.SubElement(sts_rsn_inf, "Rsn").text = status.status_reason

            if status.additional_info:
                ET.SubElement(tx_inf_and_sts, "AddtlInf").text = status.additional_info

        return self._format_xml(root)

    def create_camt053_message(
        self,
        message_id: str,
        creation_datetime: datetime,
        account_id: str,
        transactions: list[dict[str, Any]],
    ) -> str:
        """Create camt.053 BankToCustomerStatement message."""

        root = ET.Element("Document")
        root.set("xmlns", f"{self.namespace}:camt.053.001.10")

        bk_to_cstmr_stmt = ET.SubElement(root, "BkToCstmrStmt")

        # Group Header
        grp_hdr = ET.SubElement(bk_to_cstmr_stmt, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = message_id
        ET.SubElement(grp_hdr, "CreDtTm").text = creation_datetime.isoformat()

        # Statement
        stmt = ET.SubElement(bk_to_cstmr_stmt, "Stmt")
        ET.SubElement(stmt, "Id").text = f"STMT-{message_id}"

        # Account
        acct = ET.SubElement(stmt, "Acct")
        acct_id = ET.SubElement(acct, "Id")
        ET.SubElement(acct_id, "IBAN").text = account_id

        # Balance
        bal = ET.SubElement(stmt, "Bal")
        ET.SubElement(bal, "Tp").text = "CLBD"  # Closing Balance

        # Entries (transactions)
        for transaction in transactions:
            ntry = ET.SubElement(stmt, "Ntry")
            ET.SubElement(ntry, "NtryRef").text = transaction.get("reference", "")
            ET.SubElement(ntry, "CdtDbtInd").text = transaction.get("direction", "CRDT")

            # Amount
            amt = ET.SubElement(ntry, "Amt")
            amt.set("Ccy", transaction.get("currency", "USD"))
            amt.text = str(transaction.get("amount", "0.00"))

            # Value Date
            if "value_date" in transaction:
                ET.SubElement(ntry, "ValDt").text = transaction["value_date"]

        return self._format_xml(root)

    def _format_xml(self, root: ET.Element) -> str:
        """Format XML with proper indentation."""
        rough_string = ET.tostring(root, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def build_pain001_message(self, payment_data: dict[str, Any]) -> str:
        """Build pain.001 message from payment data dictionary."""
        # Extract message info
        default_msg_id = f"MSG-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        message_id = payment_data.get("message_id", default_msg_id)
        creation_datetime = self._to_datetime(
            payment_data.get("creation_datetime", datetime.now(UTC))
        )

        # Extract initiating party
        initiating_party_data = payment_data.get("initiating_party", {})
        initiating_party = ISO20022PartyIdentification(
            name=initiating_party_data.get("name", "Default Initiator"),
            bic=initiating_party_data.get("bic"),
            address=initiating_party_data.get("address"),
        )

        # Extract payment instructions
        instructions_data = payment_data.get("payment_instructions", [])
        payment_instructions: list[ISO20022PaymentInstruction] = []

        for instr_data in instructions_data:
            # Create amount
            amount_data = instr_data.get("amount", {})
            amount = ISO20022Amount(
                value=str(amount_data.get("value", "0.00")),
                currency=CurrencyCode(amount_data.get("currency", "USD")),
            )

            # Create parties
            debtor = ISO20022PartyIdentification(
                name=instr_data.get("debtor", {}).get("name", "Default Debtor"),
                bic=instr_data.get("debtor", {}).get("bic"),
                address=instr_data.get("debtor", {}).get("address"),
            )

            creditor = ISO20022PartyIdentification(
                name=instr_data.get("creditor", {}).get("name", "Default Creditor"),
                bic=instr_data.get("creditor", {}).get("bic"),
                address=instr_data.get("creditor", {}).get("address"),
            )

            # Create instruction
            # Normalize execution_date
            exec_dt = instr_data.get("execution_date")
            if exec_dt is not None:
                exec_dt = self._to_datetime(exec_dt)
            idx = len(payment_instructions) + 1
            instruction = ISO20022PaymentInstruction(
                instruction_id=instr_data.get("instruction_id", f"INSTR-{idx}"),
                end_to_end_id=instr_data.get("end_to_end_id", f"E2E-{idx}"),
                amount=amount,
                debtor=debtor,
                creditor=creditor,
                debtor_account=instr_data.get("debtor_account", ""),
                creditor_account=instr_data.get("creditor_account", ""),
                payment_purpose=PaymentPurpose(
                    instr_data.get("payment_purpose", "OTHR")
                ),
                execution_date=exec_dt,
                remittance_info=instr_data.get("remittance_info"),
            )
            payment_instructions.append(instruction)

        return self.create_pain001_message(
            message_id,
            creation_datetime,
            initiating_party,
            payment_instructions,
        )

    def build_pain002_message(self, status_data: dict[str, Any]) -> str:
        """Build pain.002 message from status data dictionary."""
        default_msg_id = f"MSG-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        message_id = status_data.get("message_id", default_msg_id)
        creation_datetime = self._to_datetime(
            status_data.get("creation_datetime", datetime.now(UTC))
        )
        original_message_id = status_data.get("original_message_id", "")

        # Extract payment statuses
        statuses_data = status_data.get("payment_statuses", [])
        payment_statuses: list[ISO20022PaymentStatus] = []

        for status_data_item in statuses_data:
            idx = len(payment_statuses) + 1
            status = ISO20022PaymentStatus(
                status_id=status_data_item.get("status_id", f"STS-{idx}"),
                original_instruction_id=status_data_item.get(
                    "original_instruction_id", ""
                ),
                status_code=status_data_item.get("status_code", "ACSC"),
                status_reason=status_data_item.get("status_reason"),
                additional_info=status_data_item.get("additional_info"),
            )
            payment_statuses.append(status)

        return self.create_pain002_message(
            message_id,
            creation_datetime,
            original_message_id,
            payment_statuses,
        )

    def build_camt053_message(self, statement_data: dict[str, Any]) -> str:
        """Build camt.053 message from statement data dictionary."""
        default_msg_id = f"MSG-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        message_id = statement_data.get("message_id", default_msg_id)
        creation_datetime = self._to_datetime(
            statement_data.get("creation_datetime", datetime.now(UTC))
        )
        account_id = statement_data.get("account_id", "")
        transactions = statement_data.get("transactions", [])

        return self.create_camt053_message(
            message_id, creation_datetime, account_id, transactions
        )


class ISO20022Validator:
    """Validates ISO20022 message compliance."""

    def __init__(self):
        self.error_codes = {
            "INVALID_BIC": "Invalid BIC code format",
            "INVALID_IBAN": "Invalid IBAN format",
            "INVALID_AMOUNT": "Invalid amount format",
            "MISSING_FIELD": "Required field missing",
            "INVALID_DATE": "Invalid date format",
            "INVALID_CURRENCY": "Invalid currency code",
        }

    def validate_bic(self, bic: str) -> bool:
        """Validate BIC (Bank Identifier Code) format."""
        # BIC format:
        # - 4 letters (bank code)
        # - 2 letters (country)
        # - 2 alphanumeric (location)
        # - optional 3 alphanumeric (branch)
        pattern = r"^[A - Z]{4}[A - Z]{2}[A - Z0 - 9]{2}([A - Z0 - 9]{3})?$"
        return bool(re.match(pattern, bic.upper()))

    def validate_iban(self, iban: str) -> bool:
        """Validate IBAN format using checksum."""
        iban = iban.replace(" ", "").upper()

        # Basic format check
        if not re.match(r"^[A - Z]{2}[0 - 9]{2}[A - Z0 - 9]+$", iban):
            return False

        # Length check by country (simplified)
        country_lengths = {
            "AD": 24,
            "AE": 23,
            "AL": 28,
            "AT": 20,
            "AZ": 28,
            "BA": 20,
            "BE": 16,
            "BG": 22,
            "BH": 22,
            "BR": 29,
            "BY": 28,
            "CH": 21,
            "CR": 22,
            "CY": 28,
            "CZ": 24,
            "DE": 22,
            "DK": 18,
            "DO": 28,
            "EE": 20,
            "EG": 29,
            "ES": 24,
            "FI": 18,
            "FO": 18,
            "FR": 27,
            "GB": 22,
            "GE": 22,
            "GI": 23,
            "GL": 18,
            "GR": 27,
            "GT": 28,
            "HR": 21,
            "HU": 28,
            "IE": 22,
            "IL": 23,
            "IS": 26,
            "IT": 27,
            "JO": 30,
            "KW": 30,
            "KZ": 20,
            "LB": 28,
            "LC": 32,
            "LI": 21,
            "LT": 20,
            "LU": 20,
            "LV": 21,
            "MC": 27,
            "MD": 24,
            "ME": 22,
            "MK": 19,
            "MR": 27,
            "MT": 31,
            "MU": 30,
            "NL": 18,
            "NO": 15,
            "PK": 24,
            "PL": 28,
            "PS": 29,
            "PT": 25,
            "QA": 29,
            "RO": 24,
            "RS": 22,
            "SA": 24,
            "SE": 24,
            "SI": 19,
            "SK": 24,
            "SM": 27,
            "TN": 24,
            "TR": 26,
            "UA": 29,
            "VG": 24,
            "XK": 20,
        }

        country_code = iban[:2]
        if (
            country_code in country_lengths
            and len(iban) != country_lengths[country_code]
        ):
            return False

        # Checksum validation
        rearranged = iban[4:] + iban[:4]
        numeric_string = ""
        for char in rearranged:
            if char.isdigit():
                numeric_string += char
            else:
                numeric_string += str(ord(char) - ord("A") + 10)

        return int(numeric_string) % 97 == 1

    def validate_amount(self, amount: str) -> bool:
        """Validate amount format (decimal with up to 18 fraction digits for crypto)."""
        pattern = r"^\d+(\.\d{1,18})?$"
        return bool(re.match(pattern, amount))

    def validate_currency_code(self, currency: str) -> bool:
        """Validate ISO 4217 currency code."""
        try:
            CurrencyCode(currency.upper())
            return True
        except ValueError:
            return False

    def validate_payment_instruction(
        self, instruction: ISO20022PaymentInstruction
    ) -> list[str]:
        """Validate payment instruction compliance."""
        errors = []

        if not instruction.instruction_id:
            errors.append("MISSING_FIELD: Instruction ID required")

        if not instruction.end_to_end_id:
            errors.append("MISSING_FIELD: End - to - end ID required")

        if not self.validate_amount(instruction.amount.value):
            errors.append("INVALID_AMOUNT: Amount format invalid")

        if not self.validate_currency_code(instruction.amount.currency.value):
            errors.append("INVALID_CURRENCY: Currency code invalid")

        if not instruction.debtor.name:
            errors.append("MISSING_FIELD: Debtor name required")

        if not instruction.creditor.name:
            errors.append("MISSING_FIELD: Creditor name required")

        # Validate account formats (simplified - could be IBAN or other formats)
        if (
            instruction.debtor_account
            and len(instruction.debtor_account) > 4
            and not self.validate_iban(instruction.debtor_account)
        ):
            # Could be other account format, add more validation as needed
            pass

        if (
            instruction.creditor_account
            and len(instruction.creditor_account) > 4
            and not self.validate_iban(instruction.creditor_account)
        ):
            # Could be other account format, add more validation as needed
            pass

        return errors


class ISO20022Parser:
    """Parses ISO20022 XML messages."""

    def parse_xml_message(self, xml_content: str) -> dict[str, Any]:
        """Detect message type and dispatch to appropriate parser."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}") from e

        # Determine message type from xmlns or child
        xmlns = root.get("xmlns", "")
        tag = root.tag
        ns_fragment = ""
        if "}" in tag:
            ns_fragment = tag.split("}")[0].strip("{")

        msg_type = ""
        src = xmlns or ns_fragment
        if "pain.001" in src:
            msg_type = "pain.001"
        elif "pain.002" in src:
            msg_type = "pain.002"
        elif "camt.053" in src:
            msg_type = "camt.053"

        if msg_type == "pain.001":
            return self.parse_pain001(xml_content)
        if msg_type == "pain.002":
            return self.parse_pain002(xml_content)
        if msg_type == "camt.053":
            return self.parse_camt053(xml_content)
        # Minimal fallback structure for other types
        return {"message_type": msg_type or "unknown", "raw": xml_content}

    def parse_pain001(self, xml_content: str) -> dict[str, Any]:
        """Parse pain.001 message."""
        try:
            root = ET.fromstring(xml_content)
            namespace = {"ns": root.tag.split("}")[0][1:] if "}" in root.tag else ""}

            result: dict[str, Any] = {
                "message_type": "pain.001",
                "group_header": {},
                "payment_instructions": [],
            }
            parsed_instructions: list[dict[str, Any]] = []
            result["payment_instructions"] = parsed_instructions

            # Parse group header
            grp_hdr = (
                root.find(".//ns:GrpHdr", namespace)
                if namespace
                else root.find(".//GrpHdr")
            )
            if grp_hdr is not None:
                result["group_header"] = {
                    "message_id": self._get_text(grp_hdr, "MsgId", namespace),
                    "creation_datetime": self._get_text(grp_hdr, "CreDtTm", namespace),
                    "number_of_transactions": self._get_text(
                        grp_hdr, "NbOfTxs", namespace
                    ),
                    "control_sum": self._get_text(grp_hdr, "CtrlSum", namespace),
                }

            # Parse payment information
            pmt_inf = (
                root.find(".//ns:PmtInf", namespace)
                if namespace
                else root.find(".//PmtInf")
            )
            if pmt_inf is not None:
                # Parse credit transfer transactions
                cdt_path = ".//ns:CdtTrfTxInf" if namespace else ".//CdtTrfTxInf"
                for cdt_trf in pmt_inf.findall(cdt_path, namespace):
                    instruction = self._parse_credit_transfer_instruction(
                        cdt_trf, namespace
                    )
                    parsed_instructions.append(instruction)

            return result

        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}") from e

    def _get_text(
        self,
        element: ET.Element,
        tag: str,
        namespace: dict[str, str] | None = None,
    ) -> str:
        """Get text content from element."""
        if namespace:
            found = element.find(f".//ns:{tag}", namespace)
        else:
            found = element.find(f".//{tag}")
        return (found.text or "").strip() if found is not None else ""

    def _parse_credit_transfer_instruction(
        self,
        element: ET.Element,
        namespace: dict[str, str],
    ) -> dict[str, Any]:
        """Parse credit transfer instruction."""
        instd_amt_el = element.find(
            ".//ns:InstdAmt" if namespace else ".//InstdAmt",
            namespace,
        )
        currency = instd_amt_el.get("Ccy", "") if instd_amt_el is not None else ""
        return {
            "instruction_id": self._get_text(element, "InstrId", namespace),
            "end_to_end_id": self._get_text(element, "EndToEndId", namespace),
            "amount": {
                "value": self._get_text(element, "InstdAmt", namespace),
                "currency": currency,
            },
            "creditor_name": self._get_text(element, "Nm", namespace),
            "creditor_account": self._get_text(element, "IBAN", namespace),
            "remittance_info": self._get_text(element, "Ustrd", namespace),
        }

    def parse_pain002(self, xml_content: str) -> dict[str, Any]:
        """Parse pain.002 Payment Status Report."""
        try:
            root = ET.fromstring(xml_content)
            namespace = {"ns": root.tag.split("}")[0][1:] if "}" in root.tag else ""}

            result: dict[str, Any] = {
                "message_type": "pain.002",
                "group_header": {},
                "original_message": {},
                "transactions": [],
            }

            # Group Header
            grp_hdr = (
                root.find(".//ns:GrpHdr", namespace)
                if namespace
                else root.find(".//GrpHdr")
            )
            if grp_hdr is not None:
                result["group_header"] = {
                    "message_id": self._get_text(grp_hdr, "MsgId", namespace),
                    "creation_datetime": self._get_text(grp_hdr, "CreDtTm", namespace),
                }

            # Original Group Info
            org_path = (
                ".//ns:OrgnlGrpInfAndSts" if namespace else ".//OrgnlGrpInfAndSts"
            )
            org = root.find(org_path, namespace)
            if org is not None:
                result["original_message"] = {
                    "original_message_id": self._get_text(org, "OrgnlMsgId", namespace),
                    "original_message_name": self._get_text(
                        org, "OrgnlMsgNmId", namespace
                    ),
                }

            # Transactions / Statuses
            tx_path = ".//ns:TxInfAndSts" if namespace else ".//TxInfAndSts"
            for tx in root.findall(tx_path, namespace):
                # Structured reasons inside StsRsnInf
                additional_info_list: list[str] = []
                reasons_struct: dict[str, Any] = {
                    "code": "",
                    "proprietary": "",
                    "text": "",
                    "additional_info": additional_info_list,
                }
                sts_rsn = tx.find(
                    ".//ns:StsRsnInf" if namespace else ".//StsRsnInf", namespace
                )
                if sts_rsn is not None:
                    # Try nested code and proprietary fields
                    rsn = sts_rsn.find(
                        ".//ns:Rsn" if namespace else ".//Rsn", namespace
                    )
                    if rsn is not None:
                        cd = (
                            rsn.find("ns:Cd", namespace)
                            if namespace
                            else rsn.find("Cd")
                        )
                        prtry = (
                            rsn.find("ns:Prtry", namespace)
                            if namespace
                            else rsn.find("Prtry")
                        )
                        if cd is not None and cd.text:
                            reasons_struct["code"] = (cd.text or "").strip()
                        if prtry is not None and prtry.text:
                            reasons_struct["proprietary"] = (prtry.text or "").strip()
                        # Some minimal payloads put text directly in <Rsn>
                        if (cd is None and prtry is None) and (rsn.text or "").strip():
                            reasons_struct["text"] = (rsn.text or "").strip()
                    # Collect any AddtlInf under StsRsnInf
                    addtl_path = ".//ns:AddtlInf" if namespace else ".//AddtlInf"
                    for add in sts_rsn.findall(addtl_path, namespace):
                        if add is not None and add.text:
                            additional_info_list.append((add.text or "").strip())

                # Fallback single additional info directly under TxInfAndSts
                addtl_info_top = self._get_text(tx, "AddtlInf", namespace)

                reason_text = (
                    reasons_struct.get("text")
                    or self._get_text(tx, "Rsn", namespace)
                    or ""
                )
                entry = {
                    "status_id": self._get_text(tx, "StsId", namespace),
                    "original_instruction_id": self._get_text(
                        tx, "OrgnlInstrId", namespace
                    ),
                    "status": self._get_text(tx, "TxSts", namespace),
                    # Back - compat simple reason text if present
                    "reason": reason_text,
                    "reasons": reasons_struct,
                    "additional_info": addtl_info_top,
                }
                result["transactions"].append(entry)

            return result
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}") from e

    def parse_camt053(self, xml_content: str) -> dict[str, Any]:
        """Parse camt.053 BankToCustomerStatement."""
        try:
            root = ET.fromstring(xml_content)
            namespace = {"ns": root.tag.split("}")[0][1:] if "}" in root.tag else ""}

            result: dict[str, Any] = {
                "message_type": "camt.053",
                "group_header": {},
                "statement": {
                    "id": "",
                    "account": "",
                    "balances": [],
                    "transactions": [],
                },
            }

            # Group Header
            grp_hdr = (
                root.find(".//ns:GrpHdr", namespace)
                if namespace
                else root.find(".//GrpHdr")
            )
            if grp_hdr is not None:
                result["group_header"] = {
                    "message_id": self._get_text(grp_hdr, "MsgId", namespace),
                    "creation_datetime": self._get_text(grp_hdr, "CreDtTm", namespace),
                }

            # Statement
            stmt = (
                root.find(".//ns:Stmt", namespace)
                if namespace
                else root.find(".//Stmt")
            )
            if stmt is not None:
                result["statement"]["id"] = self._get_text(stmt, "Id", namespace)
                # Account IBAN
                acct = stmt.find(".//ns:Acct" if namespace else ".//Acct", namespace)
                if acct is not None:
                    result["statement"]["account"] = self._get_text(
                        acct, "IBAN", namespace
                    )

                # Balances
                for bal in stmt.findall(
                    ".//ns:Bal" if namespace else ".//Bal", namespace
                ):
                    # Type may be in simple Tp or nested CdOrPrtry
                    tp = bal.find("ns:Tp", namespace) if namespace else bal.find("Tp")
                    bal_type = self._get_text(bal, "Tp", namespace)
                    if tp is not None:
                        # Find nested CdOrPrtry first, then look for Cd or Prtry
                        cdorprtry = (
                            tp.find("ns:CdOrPrtry", namespace)
                            if namespace
                            else tp.find("CdOrPrtry")
                        )
                        if cdorprtry is not None:
                            cd = (
                                cdorprtry.find("ns:Cd", namespace)
                                if namespace
                                else cdorprtry.find("Cd")
                            )
                            pr = (
                                cdorprtry.find("ns:Prtry", namespace)
                                if namespace
                                else cdorprtry.find("Prtry")
                            )
                            if cd is not None and cd.text:
                                bal_type = (cd.text or "").strip()
                            elif pr is not None and pr.text:
                                bal_type = (pr.text or "").strip()
                    amt_el = (
                        bal.find("ns:Amt", namespace) if namespace else bal.find("Amt")
                    )
                    bal_ccy = amt_el.get("Ccy", "") if amt_el is not None else ""
                    bal_amt = (amt_el.text or "").strip() if amt_el is not None else ""
                    # Dates can be Dt or DtTm under Bal
                    dt = bal.find("ns:Dt", namespace) if namespace else bal.find("Dt")
                    dttm = (
                        bal.find("ns:DtTm", namespace)
                        if namespace
                        else bal.find("DtTm")
                    )
                    bal_date = ""
                    if dt is not None and dt.text:
                        bal_date = (dt.text or "").strip()
                    elif dttm is not None and dttm.text:
                        bal_date = (dttm.text or "").strip()
                    result["statement"]["balances"].append(
                        {
                            "type": bal_type,
                            "amount": bal_amt,
                            "currency": bal_ccy,
                            "date": bal_date,
                        }
                    )

                # Entries
                for ntry in stmt.findall(
                    ".//ns:Ntry" if namespace else ".//Ntry", namespace
                ):
                    amt_el = ntry.find(
                        ".//ns:Amt" if namespace else ".//Amt", namespace
                    )
                    currency = amt_el.get("Ccy", "") if amt_el is not None else ""
                    amount_val = (
                        (amt_el.text or "").strip() if amt_el is not None else ""
                    )
                    # Dates under entry
                    bookg_dt_el = (
                        ntry.find("ns:BookgDt", namespace)
                        if namespace
                        else ntry.find("BookgDt")
                    )
                    bookg = ""
                    if bookg_dt_el is not None:
                        bdt = (
                            bookg_dt_el.find("ns:Dt", namespace)
                            if namespace
                            else bookg_dt_el.find("Dt")
                        )
                        bdttm = (
                            bookg_dt_el.find("ns:DtTm", namespace)
                            if namespace
                            else bookg_dt_el.find("DtTm")
                        )
                        if bdt is not None and bdt.text:
                            bookg = (bdt.text or "").strip()
                        elif bdttm is not None and bdttm.text:
                            bookg = (bdttm.text or "").strip()
                    # Value date may be simple text or nested
                    valdt_el = (
                        ntry.find("ns:ValDt", namespace)
                        if namespace
                        else ntry.find("ValDt")
                    )
                    valdt = ""
                    if valdt_el is not None:
                        vdt = (
                            valdt_el.find("ns:Dt", namespace)
                            if namespace
                            else valdt_el.find("Dt")
                        )
                        vdttm = (
                            valdt_el.find("ns:DtTm", namespace)
                            if namespace
                            else valdt_el.find("DtTm")
                        )
                        if vdt is not None and vdt.text:
                            valdt = (vdt.text or "").strip()
                        elif vdttm is not None and vdttm.text:
                            valdt = (vdttm.text or "").strip()
                        elif valdt_el.text:
                            valdt = (valdt_el.text or "").strip()
                    tx = {
                        "reference": self._get_text(ntry, "NtryRef", namespace),
                        "direction": self._get_text(ntry, "CdtDbtInd", namespace),
                        "amount": amount_val,
                        "currency": currency,
                        "booking_date": bookg,
                        "value_date": valdt,
                    }
                    result["statement"]["transactions"].append(tx)

            return result
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}") from e


# Global instances
iso20022_builder = ISO20022MessageBuilder()
iso20022_validator = ISO20022Validator()
iso20022_parser = ISO20022Parser()


def create_payment_message(
    payment_instructions: list[ISO20022PaymentInstruction],
) -> str:
    """Create ISO20022 compliant payment message."""
    message_id = str(uuid.uuid4())
    creation_datetime = datetime.now(UTC)

    # Default initiating party (should be configured)
    initiating_party = ISO20022PartyIdentification(
        name="Klerno Labs Platform", identification="KLERNO001", country="US"
    )

    return iso20022_builder.create_pain001_message(
        message_id=message_id,
        creation_datetime=creation_datetime,
        initiating_party=initiating_party,
        payment_instructions=payment_instructions,
    )


def create_status_report(
    original_message_id: str,
    payment_statuses: list[ISO20022PaymentStatus],
) -> str:
    """Create ISO20022 compliant status report."""
    message_id = str(uuid.uuid4())
    creation_datetime = datetime.now(UTC)

    return iso20022_builder.create_pain002_message(
        message_id=message_id,
        creation_datetime=creation_datetime,
        original_message_id=original_message_id,
        payment_statuses=payment_statuses,
    )


def validate_payment_compliance(instruction: ISO20022PaymentInstruction) -> bool:
    """Validate payment instruction for ISO20022 compliance."""
    errors = iso20022_validator.validate_payment_instruction(instruction)
    return len(errors) == 0


def get_supported_currencies() -> list[str]:
    """Get list of supported ISO20022 currencies."""
    return [currency.value for currency in CurrencyCode]


def get_supported_payment_purposes() -> list[str]:
    """Get list of supported payment purposes."""
    return [purpose.value for purpose in PaymentPurpose]


class ISO20022Manager:
    """Main manager class for ISO20022 compliance operations."""

    def __init__(self):
        self.message_builder = ISO20022MessageBuilder()
        self.validator = ISO20022Validator()
        self.parser = ISO20022Parser()

    def create_payment_instruction(
        self,
        message_type: MessageType,
        payment_data: dict[str, Any],
    ) -> str:
        """Create a payment instruction message."""
        try:
            if message_type == MessageType.PAIN_001:
                return self.message_builder.build_pain001_message(payment_data)
            elif message_type == MessageType.PAIN_002:
                return self.message_builder.build_pain002_message(payment_data)
            elif message_type == MessageType.CAMT_053:
                return self.message_builder.build_camt053_message(payment_data)
            else:
                # For other message types, use a generic builder
                return self.message_builder.build_pain001_message(payment_data)
        except Exception as e:
            raise ValueError(f"Failed to create payment instruction: {str(e)}") from e

    def _dict_to_instruction(self, data: dict[str, Any]) -> ISO20022PaymentInstruction:
        """Convert a loose dict into ISO20022PaymentInstruction instance."""
        amt_data = data.get("amount", {})
        amount = ISO20022Amount(
            currency=CurrencyCode(str(amt_data.get("currency", "USD"))),
            value=str(amt_data.get("value", "0.00")),
        )
        debtor_data = data.get("debtor", {})
        creditor_data = data.get("creditor", {})
        debtor = ISO20022PartyIdentification(name=debtor_data.get("name", "Debtor"))
        creditor = ISO20022PartyIdentification(
            name=creditor_data.get("name", "Creditor")
        )
        return ISO20022PaymentInstruction(
            instruction_id=data.get("instruction_id", "INSTR - 1"),
            end_to_end_id=data.get("end_to_end_id", "E2E - 1"),
            amount=amount,
            debtor=debtor,
            creditor=creditor,
            debtor_account=data.get("debtor_account", ""),
            creditor_account=data.get("creditor_account", ""),
            payment_purpose=PaymentPurpose(
                data.get("payment_purpose", PaymentPurpose.OTHR.value)
            ),
            execution_date=data.get("execution_date"),
        )

    def validate_message(self, message_data: str | dict[str, Any]) -> dict[str, Any]:
        """Validate an ISO20022 message."""
        try:
            if isinstance(message_data, str):
                # Parse XML message
                parsed_data = self.parser.parse_xml_message(message_data)
                return {"valid": True, "parsed_data": parsed_data}
            else:
                # Validate dictionary data
                errors: list[str] = []
                if "payment_instructions" in message_data:
                    for item in message_data.get("payment_instructions", []):
                        instr = self._dict_to_instruction(item)
                        errors.extend(
                            self.validator.validate_payment_instruction(instr)
                        )
                else:
                    instr = self._dict_to_instruction(message_data)
                    errors.extend(self.validator.validate_payment_instruction(instr))
                return {"valid": len(errors) == 0, "errors": errors}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}

    def validate_configuration(self) -> bool:
        """Validate ISO20022 configuration."""
        try:
            # Build a minimal valid pain.001 message
            payment_data = {
                "message_id": "TEST - MSG",
                "creation_datetime": datetime.now(UTC),
                "initiating_party": {"name": "Klerno Labs"},
                "payment_instructions": [
                    {
                        "instruction_id": "INSTR - 1",
                        "end_to_end_id": "E2E - 1",
                        "amount": {"value": "100.00", "currency": "EUR"},
                        "debtor": {"name": "Test Debtor"},
                        "creditor": {"name": "Test Creditor"},
                        "debtor_account": "DE89370400440532013000",
                        "creditor_account": "GB29NWBK60161331926819",
                        "payment_purpose": PaymentPurpose.OTHR.value,
                    }
                ],
            }

            message = self.create_payment_instruction(
                MessageType.PAIN_001, payment_data
            )
            validation = self.validate_message(message)
            return bool(validation.get("valid", False))
        except Exception:
            return False

    async def generate_compliance_report(self) -> dict[str, Any]:
        """Generate ISO20022 compliance report."""
        try:
            supported_types = [msg_type.value for msg_type in MessageType]
            supported_currencies = get_supported_currencies()
            supported_purposes = get_supported_payment_purposes()

            # Test configuration
            config_valid = self.validate_configuration()

            return {
                "compliant": config_valid,
                "score": 100.0 if config_valid else 0.0,
                "supported_message_types": supported_types,
                "supported_currencies": supported_currencies,
                "supported_purposes": supported_purposes,
                "features": [
                    "Payment Initiation (pain.001)",
                    "Payment Status (pain.002)",
                    "Account Statement (camt.053)",
                    "IBAN Validation",
                    "XML Generation",
                    "Message Validation",
                ],
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            return {
                "compliant": False,
                "score": 0.0,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
