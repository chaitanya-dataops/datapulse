"""
PII Detection Module for DataPulse
Detects personally identifiable information using regex patterns
100% local processing - no data sent externally
"""

import re
import pandas as pd
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class PIIMatch:
    """Represents a PII detection match"""
    column: str
    pii_type: str
    confidence: str  # high, medium, low
    sample_count: int
    total_values: int
    percentage: float
    risk_level: str  # critical, high, medium, low


# PII Detection Patterns (all processed locally)
PII_PATTERNS = {
    "ssn": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "description": "Social Security Number",
        "risk": "critical",
        "examples": ["123-45-6789"]
    },
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "description": "Email Address",
        "risk": "high",
        "examples": ["user@example.com"]
    },
    "phone_us": {
        "pattern": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "description": "US Phone Number",
        "risk": "high",
        "examples": ["(555) 123-4567", "+1-555-123-4567"]
    },
    "credit_card": {
        "pattern": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
        "description": "Credit Card Number",
        "risk": "critical",
        "examples": ["4111111111111111"]
    },
    "ip_address": {
        "pattern": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "description": "IP Address",
        "risk": "medium",
        "examples": ["192.168.1.1"]
    },
    "date_of_birth": {
        "pattern": r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b",
        "description": "Date of Birth (MM/DD/YYYY)",
        "risk": "high",
        "examples": ["01/15/1990"]
    },
    "passport": {
        "pattern": r"\b[A-Z]{1,2}[0-9]{6,9}\b",
        "description": "Passport Number",
        "risk": "critical",
        "examples": ["AB1234567"]
    },
    "drivers_license": {
        "pattern": r"\b[A-Z]{1,2}\d{5,8}\b",
        "description": "Driver's License",
        "risk": "high",
        "examples": ["D12345678"]
    },
    "bank_account": {
        "pattern": r"\b\d{8,17}\b",
        "description": "Bank Account Number",
        "risk": "high",
        "examples": ["12345678901234"]
    },
    "zip_code": {
        "pattern": r"\b\d{5}(?:-\d{4})?\b",
        "description": "ZIP Code",
        "risk": "low",
        "examples": ["12345", "12345-6789"]
    },
    "street_address": {
        "pattern": r"\b\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\b",
        "description": "Street Address",
        "risk": "medium",
        "examples": ["123 Main Street"]
    }
}

# Column name patterns that suggest PII
PII_COLUMN_HINTS = {
    "ssn": ["ssn", "social_security", "social_sec", "ss_number"],
    "email": ["email", "e_mail", "email_address", "mail"],
    "phone": ["phone", "telephone", "mobile", "cell", "contact_number"],
    "credit_card": ["credit_card", "cc_number", "card_number", "payment_card"],
    "name": ["first_name", "last_name", "full_name", "name", "customer_name"],
    "address": ["address", "street", "city", "state", "zip", "postal"],
    "dob": ["dob", "date_of_birth", "birth_date", "birthday"],
    "ip": ["ip_address", "ip", "client_ip", "user_ip"]
}


def detect_pii_in_column(series: pd.Series, column_name: str) -> List[PIIMatch]:
    """
    Detect PII patterns in a single column
    
    Args:
        series: Pandas Series to scan
        column_name: Name of the column
        
    Returns:
        List of PIIMatch objects for detected PII
    """
    matches = []
    
    # Skip non-string columns
    if series.dtype not in ['object', 'string']:
        return matches
    
    # Convert to string and drop nulls
    str_series = series.dropna().astype(str)
    total_values = len(str_series)
    
    if total_values == 0:
        return matches
    
    # Check column name hints first
    col_lower = column_name.lower()
    for pii_type, hints in PII_COLUMN_HINTS.items():
        if any(hint in col_lower for hint in hints):
            # Column name suggests PII
            matches.append(PIIMatch(
                column=column_name,
                pii_type=f"{pii_type}_column_name",
                confidence="medium",
                sample_count=total_values,
                total_values=total_values,
                percentage=100.0,
                risk_level="medium"
            ))
    
    # Scan content with regex patterns
    for pii_type, config in PII_PATTERNS.items():
        pattern = re.compile(config["pattern"], re.IGNORECASE)
        
        # Count matches
        match_count = str_series.str.contains(pattern, na=False).sum()
        
        if match_count > 0:
            percentage = (match_count / total_values) * 100
            
            # Determine confidence based on match percentage
            if percentage >= 80:
                confidence = "high"
            elif percentage >= 30:
                confidence = "medium"
            else:
                confidence = "low"
            
            matches.append(PIIMatch(
                column=column_name,
                pii_type=config["description"],
                confidence=confidence,
                sample_count=match_count,
                total_values=total_values,
                percentage=round(percentage, 2),
                risk_level=config["risk"]
            ))
    
    return matches


def scan_dataframe_for_pii(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Scan entire DataFrame for PII
    
    Args:
        df: DataFrame to scan
        
    Returns:
        Dictionary with scan results
    """
    all_matches = []
    columns_scanned = 0
    columns_with_pii = set()
    
    for column in df.columns:
        columns_scanned += 1
        matches = detect_pii_in_column(df[column], column)
        
        if matches:
            columns_with_pii.add(column)
            all_matches.extend(matches)
    
    # Calculate risk summary
    risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for match in all_matches:
        risk_counts[match.risk_level] += 1
    
    # Calculate overall risk score
    risk_score = (
        risk_counts["critical"] * 100 +
        risk_counts["high"] * 50 +
        risk_counts["medium"] * 20 +
        risk_counts["low"] * 5
    )
    risk_score = min(100, risk_score)  # Cap at 100
    
    return {
        "total_columns": len(df.columns),
        "columns_scanned": columns_scanned,
        "columns_with_pii": len(columns_with_pii),
        "pii_columns_list": list(columns_with_pii),
        "total_findings": len(all_matches),
        "findings": all_matches,
        "risk_counts": risk_counts,
        "risk_score": risk_score,
        "risk_level": (
            "Critical" if risk_counts["critical"] > 0 else
            "High" if risk_counts["high"] > 0 else
            "Medium" if risk_counts["medium"] > 0 else
            "Low" if risk_counts["low"] > 0 else
            "None"
        )
    }


def generate_pii_report(scan_results: Dict[str, Any]) -> str:
    """Generate a text report of PII findings"""
    report = []
    report.append("=" * 60)
    report.append("PII DETECTION REPORT")
    report.append("=" * 60)
    report.append(f"\nOverall Risk Level: {scan_results['risk_level']}")
    report.append(f"Risk Score: {scan_results['risk_score']}/100")
    report.append(f"\nColumns Scanned: {scan_results['columns_scanned']}")
    report.append(f"Columns with PII: {scan_results['columns_with_pii']}")
    report.append(f"Total Findings: {scan_results['total_findings']}")
    
    report.append("\n" + "-" * 40)
    report.append("RISK BREAKDOWN:")
    for level, count in scan_results['risk_counts'].items():
        if count > 0:
            report.append(f"  {level.upper()}: {count}")
    
    if scan_results['findings']:
        report.append("\n" + "-" * 40)
        report.append("DETAILED FINDINGS:\n")
        
        for finding in scan_results['findings']:
            report.append(f"Column: {finding.column}")
            report.append(f"  Type: {finding.pii_type}")
            report.append(f"  Risk: {finding.risk_level.upper()}")
            report.append(f"  Confidence: {finding.confidence}")
            report.append(f"  Matches: {finding.sample_count}/{finding.total_values} ({finding.percentage}%)")
            report.append("")
    
    return "\n".join(report)


def get_masking_recommendation(pii_type: str) -> str:
    """Get recommendation for masking PII type"""
    recommendations = {
        "Social Security Number": "Replace with XXX-XX-XXXX or hash",
        "Email Address": "Hash or replace domain: user@***.com",
        "Credit Card Number": "Show last 4 digits only: ****-****-****-1234",
        "US Phone Number": "Replace with (XXX) XXX-XXXX",
        "IP Address": "Truncate last octet: 192.168.1.XXX",
        "Date of Birth": "Keep only year or age range",
        "Passport Number": "Full redaction: ********",
        "Driver's License": "Full redaction: ********",
        "Bank Account Number": "Show last 4 digits: ****1234",
        "Street Address": "Keep only city/state",
        "ZIP Code": "Keep only first 3 digits: 123**"
    }
    return recommendations.get(pii_type, "Consider masking or encryption")
