"""
Predictive Monitoring Module for DataPulse
Early failure detection, trend analysis, and proactive alerting
Aligned with Brightspeed Requirements Section 14
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from scipy import stats


class PredictionConfidence(Enum):
    """Confidence levels for predictions"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertType(Enum):
    """Types of predictive alerts"""
    EARLY_WARNING = "early_warning"      # Trend indicates future issue
    ANOMALY_PREDICTED = "anomaly_predicted"  # Model predicts anomaly
    THRESHOLD_BREACH = "threshold_breach"    # Will breach threshold soon
    PATTERN_BREAK = "pattern_break"          # Historical pattern changing


@dataclass
class Prediction:
    """A single prediction result"""
    metric_name: str
    current_value: float
    predicted_value: float
    prediction_time: str
    horizon_hours: int
    confidence: PredictionConfidence
    confidence_interval: Tuple[float, float]
    trend_direction: str  # up, down, stable
    alert_type: Optional[AlertType]
    alert_message: Optional[str]


@dataclass
class TrendAnalysis:
    """Result of trend analysis"""
    metric_name: str
    analysis_time: str
    time_series_length: int
    
    # Trend characteristics
    trend_direction: str
    trend_strength: float  # 0-1
    slope: float
    intercept: float
    r_squared: float
    
    # Seasonality
    has_seasonality: bool
    seasonal_period: Optional[int]
    seasonal_strength: Optional[float]
    
    # Change points
    change_points: List[Dict]
    
    # Forecast
    forecast_values: List[float]
    forecast_dates: List[str]
    
    # Risk assessment
    risk_level: str
    risk_factors: List[str]


class PredictiveMonitor:
    """Predictive monitoring and early failure detection"""
    
    def __init__(self):
        self.thresholds: Dict[str, Dict] = {}
        self.historical_data: Dict[str, pd.DataFrame] = {}
        self.predictions: List[Prediction] = []
    
    def register_threshold(
        self,
        metric_name: str,
        warning_threshold: float,
        critical_threshold: float,
        direction: str = "upper"  # upper, lower, both
    ):
        """Register thresholds for a metric"""
        self.thresholds[metric_name] = {
            "warning": warning_threshold,
            "critical": critical_threshold,
            "direction": direction
        }
    
    def simple_forecast(
        self,
        values: List[float],
        horizon: int = 24
    ) -> Dict[str, Any]:
        """Simple linear regression forecast"""
        
        if len(values) < 10:
            return {"error": "Insufficient data for forecasting"}
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Forecast
        future_x = np.arange(len(values), len(values) + horizon)
        forecast = slope * future_x + intercept
        
        # Confidence interval (simplified)
        residuals = y - (slope * x + intercept)
        std_resid = np.std(residuals)
        ci_lower = forecast - 1.96 * std_resid
        ci_upper = forecast + 1.96 * std_resid
        
        return {
            "forecast": forecast.tolist(),
            "ci_lower": ci_lower.tolist(),
            "ci_upper": ci_upper.tolist(),
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_value ** 2,
            "trend": "up" if slope > 0.01 else ("down" if slope < -0.01 else "stable")
        }
    
    def exponential_smoothing_forecast(
        self,
        values: List[float],
        alpha: float = 0.3,
        horizon: int = 24
    ) -> Dict[str, Any]:
        """Exponential smoothing forecast"""
        
        if len(values) < 5:
            return {"error": "Insufficient data for forecasting"}
        
        # Simple exponential smoothing
        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
        
        # Calculate trend
        recent_trend = (smoothed[-1] - smoothed[-min(10, len(smoothed))]) / min(10, len(smoothed))
        
        # Forecast with trend
        forecast = []
        last_value = smoothed[-1]
        for i in range(horizon):
            next_val = last_value + recent_trend
            forecast.append(next_val)
            last_value = next_val
        
        # Simple confidence interval
        std_dev = np.std(values[-min(30, len(values)):])
        ci_lower = [f - 1.96 * std_dev for f in forecast]
        ci_upper = [f + 1.96 * std_dev for f in forecast]
        
        return {
            "forecast": forecast,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "smoothed": smoothed,
            "trend": "up" if recent_trend > 0.01 else ("down" if recent_trend < -0.01 else "stable")
        }
    
    def detect_change_points(
        self,
        values: List[float],
        window: int = 10,
        threshold: float = 2.0
    ) -> List[Dict]:
        """Detect sudden changes in the time series"""
        
        if len(values) < window * 2:
            return []
        
        change_points = []
        
        for i in range(window, len(values) - window):
            before = values[i - window:i]
            after = values[i:i + window]
            
            before_mean = np.mean(before)
            after_mean = np.mean(after)
            combined_std = np.std(values[i - window:i + window])
            
            if combined_std > 0:
                z_score = abs(after_mean - before_mean) / combined_std
                
                if z_score > threshold:
                    change_points.append({
                        "index": i,
                        "before_mean": round(before_mean, 3),
                        "after_mean": round(after_mean, 3),
                        "change_magnitude": round(after_mean - before_mean, 3),
                        "z_score": round(z_score, 2),
                        "direction": "increase" if after_mean > before_mean else "decrease"
                    })
        
        return change_points
    
    def analyze_trend(
        self,
        metric_name: str,
        values: List[float],
        timestamps: List[datetime]
    ) -> TrendAnalysis:
        """Comprehensive trend analysis"""
        
        if len(values) < 10:
            raise ValueError("Need at least 10 data points for trend analysis")
        
        # Linear regression for overall trend
        x = np.arange(len(values))
        slope, intercept, r_value, _, _ = stats.linregress(x, values)
        
        # Determine trend direction and strength
        r_squared = r_value ** 2
        if abs(slope) < 0.01:
            trend_direction = "stable"
            trend_strength = 0.0
        else:
            trend_direction = "increasing" if slope > 0 else "decreasing"
            trend_strength = min(abs(slope) * 10, 1.0)  # Normalized
        
        # Detect seasonality (simplified)
        has_seasonality = False
        seasonal_period = None
        seasonal_strength = None
        
        if len(values) >= 48:  # At least 2 days of hourly data
            # Check for 24-hour periodicity
            hourly_avg = []
            for h in range(24):
                hour_vals = [values[i] for i in range(h, len(values), 24)]
                hourly_avg.append(np.mean(hour_vals) if hour_vals else 0)
            
            if np.std(hourly_avg) > np.std(values) * 0.3:
                has_seasonality = True
                seasonal_period = 24
                seasonal_strength = np.std(hourly_avg) / (np.std(values) + 0.001)
        
        # Detect change points
        change_points = self.detect_change_points(values)
        
        # Forecast next 24 hours
        forecast_result = self.exponential_smoothing_forecast(values, horizon=24)
        forecast_values = forecast_result.get("forecast", [])
        forecast_dates = [(datetime.now() + timedelta(hours=i)).isoformat() 
                         for i in range(1, 25)]
        
        # Risk assessment
        risk_factors = []
        risk_level = "low"
        
        if trend_direction == "increasing" and metric_name in self.thresholds:
            thresh = self.thresholds[metric_name]
            if thresh["direction"] in ["upper", "both"]:
                if forecast_values and forecast_values[-1] > thresh["warning"]:
                    risk_factors.append("Forecast exceeds warning threshold")
                    risk_level = "medium"
                if forecast_values and forecast_values[-1] > thresh["critical"]:
                    risk_factors.append("Forecast exceeds critical threshold")
                    risk_level = "high"
        
        if len(change_points) > 3:
            risk_factors.append("Multiple change points detected")
            risk_level = "medium" if risk_level == "low" else risk_level
        
        if trend_strength > 0.7:
            risk_factors.append("Strong trend detected")
        
        return TrendAnalysis(
            metric_name=metric_name,
            analysis_time=datetime.now().isoformat(),
            time_series_length=len(values),
            trend_direction=trend_direction,
            trend_strength=round(trend_strength, 3),
            slope=round(slope, 6),
            intercept=round(intercept, 3),
            r_squared=round(r_squared, 3),
            has_seasonality=has_seasonality,
            seasonal_period=seasonal_period,
            seasonal_strength=round(seasonal_strength, 3) if seasonal_strength else None,
            change_points=change_points,
            forecast_values=forecast_values,
            forecast_dates=forecast_dates,
            risk_level=risk_level,
            risk_factors=risk_factors
        )
    
    def predict_threshold_breach(
        self,
        metric_name: str,
        current_value: float,
        historical_values: List[float],
        horizon_hours: int = 24
    ) -> Optional[Prediction]:
        """Predict if/when a threshold will be breached"""
        
        if metric_name not in self.thresholds:
            return None
        
        thresh = self.thresholds[metric_name]
        forecast = self.exponential_smoothing_forecast(
            historical_values + [current_value], 
            horizon=horizon_hours
        )
        
        if "error" in forecast:
            return None
        
        forecast_values = forecast["forecast"]
        
        # Check for threshold breach
        breach_hour = None
        breach_value = None
        
        for i, val in enumerate(forecast_values):
            if thresh["direction"] in ["upper", "both"] and val > thresh["critical"]:
                breach_hour = i + 1
                breach_value = val
                break
            elif thresh["direction"] in ["lower", "both"] and val < thresh["critical"]:
                breach_hour = i + 1
                breach_value = val
                break
        
        if breach_hour:
            confidence = PredictionConfidence.HIGH if breach_hour <= 6 else (
                PredictionConfidence.MEDIUM if breach_hour <= 12 else 
                PredictionConfidence.LOW
            )
            
            return Prediction(
                metric_name=metric_name,
                current_value=current_value,
                predicted_value=breach_value,
                prediction_time=datetime.now().isoformat(),
                horizon_hours=breach_hour,
                confidence=confidence,
                confidence_interval=(forecast["ci_lower"][breach_hour-1], forecast["ci_upper"][breach_hour-1]),
                trend_direction=forecast["trend"],
                alert_type=AlertType.THRESHOLD_BREACH,
                alert_message=f"{metric_name} predicted to breach critical threshold in {breach_hour} hours"
            )
        
        return None
    
    def generate_early_warnings(
        self,
        metrics: Dict[str, Dict]
    ) -> List[Prediction]:
        """Generate early warnings for all monitored metrics"""
        
        warnings = []
        
        for metric_name, data in metrics.items():
            current = data.get("current_value")
            historical = data.get("historical_values", [])
            
            if not current or len(historical) < 10:
                continue
            
            # Check for threshold breach prediction
            breach_pred = self.predict_threshold_breach(
                metric_name, current, historical
            )
            if breach_pred:
                warnings.append(breach_pred)
            
            # Check for unusual trend
            try:
                analysis = self.analyze_trend(
                    metric_name, 
                    historical + [current],
                    [datetime.now() - timedelta(hours=i) for i in range(len(historical), -1, -1)]
                )
                
                if analysis.risk_level in ["medium", "high"]:
                    warnings.append(Prediction(
                        metric_name=metric_name,
                        current_value=current,
                        predicted_value=analysis.forecast_values[0] if analysis.forecast_values else current,
                        prediction_time=datetime.now().isoformat(),
                        horizon_hours=24,
                        confidence=PredictionConfidence.MEDIUM,
                        confidence_interval=(0, 0),  # Placeholder
                        trend_direction=analysis.trend_direction,
                        alert_type=AlertType.EARLY_WARNING,
                        alert_message=f"Risk factors detected: {', '.join(analysis.risk_factors)}"
                    ))
            except Exception:
                pass
        
        self.predictions.extend(warnings)
        return warnings


def generate_mock_predictions() -> List[Dict]:
    """Generate mock prediction data for demo"""
    return [
        {
            "metric": "null_rate",
            "table": "analytics.orders",
            "current_value": 2.3,
            "predicted_value": 5.8,
            "threshold": 5.0,
            "breach_in_hours": 8,
            "confidence": "high",
            "trend": "increasing",
            "alert": "Null rate trending up, will breach threshold in 8 hours"
        },
        {
            "metric": "row_count",
            "table": "analytics.events",
            "current_value": 45000,
            "predicted_value": 32000,
            "threshold": 35000,
            "breach_in_hours": 12,
            "confidence": "medium",
            "trend": "decreasing",
            "alert": "Volume trending down, investigate data pipeline"
        },
        {
            "metric": "freshness_hours",
            "table": "finance.revenue",
            "current_value": 0.8,
            "predicted_value": 1.2,
            "threshold": 1.0,
            "breach_in_hours": 4,
            "confidence": "high",
            "trend": "increasing",
            "alert": "Freshness degrading, SLA at risk"
        }
    ]


def generate_mock_trend_data() -> pd.DataFrame:
    """Generate mock time series data for trend visualization"""
    np.random.seed(42)
    
    dates = pd.date_range(end=datetime.now(), periods=168, freq="H")  # 7 days
    
    # Base pattern with trend and seasonality
    x = np.arange(168)
    trend = 0.1 * x  # Upward trend
    seasonality = 10 * np.sin(2 * np.pi * x / 24)  # Daily pattern
    noise = np.random.normal(0, 5, 168)
    
    values = 100 + trend + seasonality + noise
    
    # Inject a change point
    values[120:] += 20  # Sudden jump
    
    return pd.DataFrame({
        "timestamp": dates,
        "value": values,
        "metric": "row_count"
    })
