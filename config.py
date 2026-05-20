"""
Configuration settings for the Anomaly Detector
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Anomaly Detection Thresholds
Z_SCORE_THRESHOLD = 2.5  # Values beyond 2.5 std deviations are anomalies
NULL_RATE_THRESHOLD = 0.1  # Alert if null rate exceeds 10%
ROW_COUNT_DROP_THRESHOLD = 0.3  # Alert if row count drops by 30%

# UI Settings
LOOKBACK_DAYS = 30  # Default days to show in charts
