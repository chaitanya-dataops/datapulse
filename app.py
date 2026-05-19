"""
� DataPulse - Enterprise Data Quality Monitoring
Competing with Bigeye/Datafold/Anomalo - Free & Open Source

Team: Ctrl Alt Defeat!
Hackathon: Data Platform Ops
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Local imports
from data.mock_data import (
    generate_mock_table_list,
    generate_mock_row_counts,
    generate_mock_null_rates,
    generate_mock_column_stats,
    generate_mock_schema_snapshot,
    generate_mock_freshness_data,
    generate_mock_distribution_data,
    generate_mock_duplicate_data,
    generate_mock_cardinality_history,
    generate_mock_rule_test_data,
    generate_mock_comparison_data,
    generate_mock_historical_values
)
from utils.anomaly_detector import (
    detect_row_count_anomalies,
    detect_null_rate_anomalies,
    get_health_score,
    detect_schema_changes,
    detect_data_freshness,
    detect_distribution_shift,
    detect_duplicates,
    detect_cardinality_anomalies,
    validate_custom_rules,
    forecast_expected_value,
    compare_datasets,
    get_comprehensive_health_score,
    DataQualityRule,
    RuleType,
    # ML capabilities
    detect_anomalies_isolation_forest,
    detect_anomalies_dbscan,
    auto_learn_thresholds,
    detect_with_learned_thresholds,
    exponential_smoothing_forecast,
    multivariate_anomaly_score
)
from utils.column_profiler import profile_column, profile_dataframe
from utils.history_store import HistoryStore, generate_mock_history
from utils.notifications import SlackNotifier, generate_alert_html
from utils.pii_detector import scan_dataframe_for_pii, get_masking_recommendation
from utils.data_lineage import generate_mock_lineage, get_lineage_stats
from utils.sql_rules import SQLRulesEngine, DataQualityRule as SQLRule, get_predefined_rules, generate_rule_from_template
from utils.drift_detector import DriftDetector, generate_mock_drift_data
from utils.root_cause import RootCauseAnalyzer, generate_mock_rca_data, get_rca_recommendations
from utils.data_contracts import DataContract, get_sample_contract, get_contract_templates, parse_contract_yaml

# Page configuration
st.set_page_config(
    page_title="DataPulse",
    page_icon="💫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better visuals
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .anomaly-critical {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .anomaly-warning {
        background-color: #fff8e1;
        border-left: 4px solid #ff9800;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .health-good {
        color: #4caf50;
        font-size: 48px;
        font-weight: bold;
    }
    .health-warning {
        color: #ff9800;
        font-size: 48px;
        font-weight: bold;
    }
    .health-critical {
        color: #f44336;
        font-size: 48px;
        font-weight: bold;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .feature-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75em;
        margin-left: 5px;
    }
    .schema-change {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


def get_data_source():
    """Get data from mock source (can be extended to use BigQuery)"""
    # For hackathon demo, using mock data
    # TODO: Connect to BigQuery for real data
    return "mock"


def main():
    # Header
    st.title("� DataPulse")
    st.markdown("*Enterprise Data Quality Monitoring • Built by Ctrl Alt Defeat!*")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Data source toggle
        use_mock = st.checkbox("Use Demo Data", value=True, 
                               help="Toggle off to connect to BigQuery")
        
        st.markdown("---")
        
        # Table selection
        tables = generate_mock_table_list()
        table_options = [f"{t['dataset']}.{t['table_name']}" for t in tables]
        selected_table = st.selectbox("📊 Select Table", table_options)
        
        st.markdown("---")
        
        # Time range
        lookback_days = st.slider("📅 Lookback Days", 7, 90, 30)
        
        st.markdown("---")
        
        # Thresholds
        st.subheader("🎯 Detection Thresholds")
        z_threshold = st.slider("Z-Score Threshold", 1.5, 4.0, 2.5, 0.1,
                               help="Higher = fewer alerts, Lower = more sensitive")
        null_threshold = st.slider("Null Rate Alert (%)", 1, 20, 5,
                                  help="Alert if null rate exceeds this")
        
        st.markdown("---")
        st.markdown("**Team:** Ctrl Alt Defeat! 🎮")
        st.markdown("**Event:** Data Platform Ops Hackathon")
    
    # Get selected table name
    table_name = selected_table.split(".")[1]
    dataset_name = selected_table.split(".")[0]
    
    # Load data
    row_counts_df = generate_mock_row_counts(table_name, lookback_days)
    null_rates_df = generate_mock_null_rates(table_name, lookback_days)
    column_stats_df = generate_mock_column_stats(table_name)
    
    # Detect anomalies
    row_anomalies = detect_row_count_anomalies(row_counts_df, z_threshold)
    null_anomalies = detect_null_rate_anomalies(null_rates_df, null_threshold/100)
    
    # Calculate health score
    health_score, health_status = get_health_score(row_anomalies, null_anomalies)
    
    # Enterprise features data
    freshness_data = generate_mock_freshness_data(table_name)
    freshness_result = detect_data_freshness(
        freshness_data["last_update"],
        freshness_data["expected_frequency_hours"]
    )
    
    current_schema = generate_mock_schema_snapshot(table_name, "current")
    previous_schema = generate_mock_schema_snapshot(table_name, "previous")
    schema_changes = detect_schema_changes(current_schema, previous_schema)
    
    # Get comprehensive health score
    comp_score, comp_status, score_breakdown = get_comprehensive_health_score(
        row_anomalies, null_anomalies, schema_changes, freshness_result
    )
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        health_color = "🟢" if comp_score >= 80 else ("🟡" if comp_score >= 60 else "🔴")
        st.metric(
            label="Health Score",
            value=f"{health_color} {comp_score}",
            delta=comp_status
        )
    
    with col2:
        total_issues = len(row_anomalies) + len(null_anomalies) + len(schema_changes)
        if freshness_result.get("severity"):
            total_issues += 1
        st.metric(
            label="Issues Detected",
            value=total_issues,
            delta="All monitors",
            delta_color="inverse"
        )
    
    with col3:
        avg_rows = row_counts_df["row_count"].mean()
        st.metric(
            label="Avg Daily Rows",
            value=f"{avg_rows:,.0f}"
        )
    
    with col4:
        latest_rows = row_counts_df.iloc[-1]["row_count"]
        pct_change = ((latest_rows - avg_rows) / avg_rows) * 100
        st.metric(
            label="Latest Row Count",
            value=f"{latest_rows:,.0f}",
            delta=f"{pct_change:+.1f}%"
        )
    
    st.markdown("---")
    
    # Create tabs for different monitoring features
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15, tab16 = st.tabs([
        "📈 Volume & Nulls",
        "🔄 Schema Changes", 
        "⏰ Freshness",
        "📊 Distribution",
        "🔍 Duplicates",
        "✅ Custom Rules",
        "🤖 ML Detection",
        "📋 Column Profiler",
        "📜 History",
        "🔔 Alerts",
        "🔐 PII Detection",
        "🌐 Data Lineage",
        "📝 SQL Rules",
        "📉 Drift Detection",
        "🔬 Root Cause",
        "📄 Data Contracts"
    ])
    
    # ==================== TAB 1: Volume & Nulls ====================
    with tab1:
        left_col, right_col = st.columns([2, 1])
    
    with left_col:
        # Row Count Trend Chart
        st.subheader("📈 Row Count Trend")
        
        fig_rows = go.Figure()
        
        # Main line
        fig_rows.add_trace(go.Scatter(
            x=row_counts_df["date"],
            y=row_counts_df["row_count"],
            mode="lines+markers",
            name="Row Count",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=6)
        ))
        
        # Mark anomalies
        if row_anomalies:
            anomaly_dates = [a["date"] for a in row_anomalies]
            anomaly_values = [a["value"] for a in row_anomalies]
            fig_rows.add_trace(go.Scatter(
                x=anomaly_dates,
                y=anomaly_values,
                mode="markers",
                name="⚠️ Anomaly",
                marker=dict(color="red", size=15, symbol="x")
            ))
        
        # Add average line
        fig_rows.add_hline(
            y=avg_rows, 
            line_dash="dash", 
            line_color="gray",
            annotation_text=f"Avg: {avg_rows:,.0f}"
        )
        
        fig_rows.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_rows, use_container_width=True)
        
        # Null Rate Chart
        st.subheader("📉 Null Rate by Column")
        
        # Get latest null rates per column
        latest_nulls = null_rates_df.groupby("column_name").last().reset_index()
        
        fig_nulls = px.bar(
            latest_nulls,
            x="column_name",
            y="null_rate",
            color="null_rate",
            color_continuous_scale=["green", "yellow", "red"],
            range_color=[0, 0.15]
        )
        
        # Add threshold line
        fig_nulls.add_hline(
            y=null_threshold/100, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Threshold: {null_threshold}%"
        )
        
        fig_nulls.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=30, b=0),
            yaxis_tickformat=".1%",
            showlegend=False
        )
        
        st.plotly_chart(fig_nulls, use_container_width=True)
    
    with right_col:
        # Anomaly Alerts
        st.subheader("🚨 Anomaly Alerts")
        
        all_anomalies = row_anomalies + null_anomalies
        
        if not all_anomalies:
            st.success("✅ No anomalies detected! Data looks healthy.")
        else:
            for anomaly in sorted(all_anomalies, 
                                 key=lambda x: x.get("severity", "low") == "critical",
                                 reverse=True):
                severity = anomaly.get("severity", "medium")
                icon = "🔴" if severity in ["critical", "high"] else "🟡"
                
                with st.expander(
                    f"{icon} {anomaly['metric'].replace('_', ' ').title()} - "
                    f"{anomaly['date'].strftime('%b %d') if isinstance(anomaly['date'], datetime) else anomaly['date']}", 
                    expanded=True
                ):
                    if anomaly["metric"] == "row_count":
                        st.metric(
                            "Value", 
                            f"{anomaly['value']:,.0f}",
                            f"{anomaly.get('pct_change', 0):+.1f}%"
                        )
                    else:
                        st.metric(
                            f"Column: {anomaly.get('column_name', 'N/A')}",
                            f"{anomaly['value']*100:.1f}%",
                            f"Baseline: {anomaly.get('baseline', 0)*100:.1f}%"
                        )
                    
                    st.markdown("**Explanation:**")
                    st.info(anomaly.get("explanation", "No explanation available"))
        
        # Column Statistics
        st.markdown("---")
        st.subheader("📋 Column Stats")
        
        if not column_stats_df.empty:
            column_stats_df["null_rate"] = (
                column_stats_df["null_count"] / column_stats_df["total_count"] * 100
            ).round(2)
            
            st.dataframe(
                column_stats_df[["column_name", "data_type", "null_rate", "distinct_count"]],
                hide_index=True,
                use_container_width=True
            )
    
    # ==================== TAB 2: Schema Changes ====================
    with tab2:
        st.subheader("🔄 Schema Change Detection")
        st.markdown("*Comparable to Bigeye/Datafold schema monitoring*")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Current Schema**")
            st.dataframe(current_schema, hide_index=True, use_container_width=True)
        
        with col2:
            st.markdown("**Previous Schema**")
            st.dataframe(previous_schema, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Detected Changes")
        
        if not schema_changes:
            st.success("✅ No schema changes detected")
        else:
            for change in schema_changes:
                icon = "🟡" if change["severity"] == "medium" else "🔴"
                with st.expander(f"{icon} {change['change_type'].replace('_', ' ').title()}: `{change['column_name']}`", expanded=True):
                    st.markdown(f"**{change['explanation']}**")
                    if change.get("old_type") and change.get("new_type"):
                        st.code(f"Type: {change['old_type']} → {change['new_type']}")
    
    # ==================== TAB 3: Freshness ====================
    with tab3:
        st.subheader("⏰ Data Freshness Monitoring")
        st.markdown("*Comparable to Anomalo/Bigeye freshness checks*")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            freshness_icon = "🟢" if freshness_result["status"] == "fresh" else ("🟡" if freshness_result["status"] in ["late", "delayed"] else "🔴")
            st.metric(
                "Freshness Status",
                f"{freshness_icon} {freshness_result['status'].upper()}",
                f"{freshness_result['hours_since_update']}h ago"
            )
        
        with col2:
            st.metric(
                "Last Update",
                freshness_result["last_update"].strftime("%Y-%m-%d %H:%M")
            )
        
        with col3:
            st.metric(
                "Expected Frequency",
                f"Every {freshness_result['expected_frequency_hours']}h"
            )
        
        if freshness_result.get("explanation"):
            st.warning(freshness_result["explanation"])
        
        # Freshness history chart
        st.markdown("---")
        st.subheader("📅 Update History")
        
        # Generate mock update times
        update_times = pd.DataFrame({
            "date": pd.date_range(end=datetime.now(), periods=14, freq="D"),
            "hours_delay": [2, 1.5, 3, 2, 1, 2.5, 8, 2, 1.5, 2, 1, 38, 6, 2]
        })
        
        fig_fresh = px.bar(
            update_times,
            x="date",
            y="hours_delay",
            color="hours_delay",
            color_continuous_scale=["green", "yellow", "red"],
            range_color=[0, freshness_data["expected_frequency_hours"] * 2]
        )
        fig_fresh.add_hline(
            y=freshness_data["expected_frequency_hours"],
            line_dash="dash",
            line_color="red",
            annotation_text=f"SLA: {freshness_data['expected_frequency_hours']}h"
        )
        fig_fresh.update_layout(height=300)
        st.plotly_chart(fig_fresh, use_container_width=True)
    
    # ==================== TAB 4: Distribution ====================
    with tab4:
        st.subheader("📊 Distribution Shift Detection")
        st.markdown("*Comparable to Anomalo distribution monitoring*")
        
        # Get distribution data
        dist_data = generate_mock_distribution_data(table_name, "amount")
        dist_result = detect_distribution_shift(
            dist_data["current"],
            dist_data["historical"]
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            shift_icon = "🔴" if dist_result["shift_detected"] else "🟢"
            st.metric(
                "Shift Detected",
                f"{shift_icon} {'Yes' if dist_result['shift_detected'] else 'No'}",
                f"JS Divergence: {dist_result['js_divergence']:.4f}"
            )
        
        with col2:
            st.metric(
                "Current Mean",
                f"{dist_result['current_mean']:.2f}",
                f"Historical: {dist_result['historical_mean']:.2f}"
            )
        
        with col3:
            st.metric(
                "Current Std Dev",
                f"{dist_result['current_std']:.2f}",
                f"Historical: {dist_result['historical_std']:.2f}"
            )
        
        if dist_result.get("explanation"):
            st.warning(dist_result["explanation"])
        
        # Distribution comparison chart
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Historical Distribution**")
            fig_hist = px.histogram(dist_data["historical"], nbins=30, title="Historical")
            fig_hist.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            st.markdown("**Current Distribution**")
            fig_curr = px.histogram(dist_data["current"], nbins=30, title="Current")
            fig_curr.update_traces(marker_color='orange')
            fig_curr.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig_curr, use_container_width=True)
    
    # ==================== TAB 5: Duplicates ====================
    with tab5:
        st.subheader("🔍 Duplicate Detection")
        st.markdown("*Comparable to Datafold uniqueness checks*")
        
        # Get duplicate data
        dup_df = generate_mock_duplicate_data(table_name)
        key_columns = ["transaction_id"] if table_name == "sales_daily" else ["id"]
        dup_result = detect_duplicates(dup_df, key_columns)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dup_icon = "🔴" if dup_result["is_anomaly"] else ("🟡" if dup_result["has_duplicates"] else "🟢")
            st.metric(
                "Duplicate Status",
                f"{dup_icon} {dup_result['duplicate_count']:,} found",
                f"{dup_result['duplicate_pct']:.2f}% of rows"
            )
        
        with col2:
            st.metric(
                "Total Rows",
                f"{dup_result['total_rows']:,}"
            )
        
        with col3:
            st.metric(
                "Key Columns",
                ", ".join(dup_result["key_columns"])
            )
        
        if dup_result.get("explanation"):
            st.warning(dup_result["explanation"])
        
        if dup_result["sample_duplicates"]:
            st.markdown("---")
            st.subheader("Sample Duplicate Keys")
            st.dataframe(
                pd.DataFrame(dup_result["sample_duplicates"]),
                hide_index=True,
                use_container_width=True
            )
        
        # Cardinality check
        st.markdown("---")
        st.subheader("📊 Cardinality Analysis")
        
        for col_name in ["customer_id", "product_id"] if table_name == "sales_daily" else ["id"]:
            card_data = generate_mock_cardinality_history(table_name, col_name)
            card_result = detect_cardinality_anomalies(
                card_data["current_distinct"],
                card_data["historical_distinct"],
                card_data["total_rows"],
                col_name
            )
            
            if card_result["is_anomaly"]:
                st.warning(f"⚠️ **{col_name}**: {card_result['explanation']}")
            else:
                st.success(f"✅ **{col_name}**: Cardinality normal ({card_result['current_distinct']:,} distinct values)")
    
    # ==================== TAB 6: Custom Rules ====================
    with tab6:
        st.subheader("✅ Custom Data Quality Rules")
        st.markdown("*Comparable to Bigeye/Datafold custom assertions*")
        
        # Define sample rules
        sample_rules = [
            DataQualityRule(
                name="No NULL customer IDs",
                rule_type=RuleType.NOT_NULL,
                column="customer_id",
                severity="high"
            ),
            DataQualityRule(
                name="Amount must be positive",
                rule_type=RuleType.RANGE,
                column="amount",
                params={"min": 0, "max": 10000},
                severity="critical"
            ),
            DataQualityRule(
                name="Valid email format",
                rule_type=RuleType.REGEX,
                column="email",
                params={"pattern": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"},
                severity="medium"
            )
        ]
        
        # Get test data and validate
        rule_test_df = generate_mock_rule_test_data(table_name)
        rule_results = validate_custom_rules(rule_test_df, sample_rules)
        
        # Summary metrics
        passed_count = sum(1 for r in rule_results if r["passed"])
        failed_count = len(rule_results) - passed_count
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rules Passed", f"✅ {passed_count}")
        with col2:
            st.metric("Rules Failed", f"❌ {failed_count}")
        with col3:
            pass_rate = (passed_count / len(rule_results)) * 100 if rule_results else 100
            st.metric("Pass Rate", f"{pass_rate:.0f}%")
        
        st.markdown("---")
        st.subheader("Rule Results")
        
        for result in rule_results:
            icon = "✅" if result["passed"] else "❌"
            color = "success" if result["passed"] else "error"
            
            with st.expander(f"{icon} {result['rule_name']}", expanded=not result["passed"]):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Rule Type:** `{result['rule_type']}`")
                    st.markdown(f"**Column:** `{result['column']}`")
                with col2:
                    st.markdown(f"**Severity:** {result['severity']}")
                    if result.get("details"):
                        st.json(result["details"])
                
                if result.get("explanation"):
                    st.warning(result["explanation"])
        
        # Add new rule section
        st.markdown("---")
        st.subheader("➕ Add Custom Rule")
        
        with st.form("add_rule"):
            col1, col2 = st.columns(2)
            with col1:
                rule_name = st.text_input("Rule Name", placeholder="e.g., No negative amounts")
                rule_type = st.selectbox("Rule Type", ["NOT_NULL", "UNIQUE", "RANGE", "REGEX"])
            with col2:
                rule_column = st.selectbox("Column", rule_test_df.columns.tolist())
                rule_severity = st.selectbox("Severity", ["low", "medium", "high", "critical"])
            
            submitted = st.form_submit_button("Add Rule")
            if submitted:
                st.success(f"Rule '{rule_name}' would be added (demo mode)")
    
    # ==================== TAB 7: ML Detection ====================
    with tab7:
        st.subheader("🤖 Machine Learning Anomaly Detection")
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            <b>NEW!</b> AI-powered anomaly detection using Isolation Forest & DBSCAN algorithms. 
            No external APIs required - runs entirely on your infrastructure.
        </div>
        """, unsafe_allow_html=True)
        
        ml_col1, ml_col2 = st.columns(2)
        
        with ml_col1:
            st.markdown("### 🌲 Isolation Forest Detection")
            st.markdown("*Unsupervised ML that learns normal patterns*")
            
            # Create sample data for ML
            ml_df = row_counts_df.copy()
            ml_df["null_pct"] = np.random.uniform(0.01, 0.15, len(ml_df))
            ml_df["avg_value"] = np.random.normal(1000, 200, len(ml_df))
            
            contamination = st.slider("Expected anomaly rate", 0.05, 0.25, 0.10, key="iso_contam")
            
            if st.button("🔍 Run Isolation Forest", key="run_iso"):
                with st.spinner("Training ML model..."):
                    iso_results = detect_anomalies_isolation_forest(
                        ml_df,
                        feature_columns=["row_count", "null_pct", "avg_value"],
                        contamination=contamination
                    )
                    
                    if iso_results["success"]:
                        # Display metrics
                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric("Anomalies Found", iso_results["anomaly_count"])
                        with m2:
                            st.metric("Anomaly Rate", f"{iso_results['anomaly_pct']}%")
                        with m3:
                            st.metric("Severity", iso_results["severity"].upper())
                        
                        # Feature importance
                        if iso_results.get("feature_importance"):
                            st.markdown("**Top Contributing Features:**")
                            for feat, score in list(iso_results["feature_importance"].items())[:3]:
                                st.progress(min(score / 3, 1.0), text=f"{feat}: {score:.2f}")
                        
                        # Explanation
                        st.info(iso_results["explanation"])
                    else:
                        st.warning(iso_results.get("reason", "ML detection failed"))
        
        with ml_col2:
            st.markdown("### 🎯 DBSCAN Clustering")
            st.markdown("*Density-based outlier detection*")
            
            eps_val = st.slider("Cluster distance (eps)", 0.1, 2.0, 0.5, key="dbscan_eps")
            min_samples = st.slider("Min samples per cluster", 2, 10, 5, key="dbscan_min")
            
            if st.button("🔍 Run DBSCAN", key="run_dbscan"):
                with st.spinner("Clustering data..."):
                    dbscan_results = detect_anomalies_dbscan(
                        ml_df,
                        feature_columns=["row_count", "null_pct", "avg_value"],
                        eps=eps_val,
                        min_samples=min_samples
                    )
                    
                    if dbscan_results["success"]:
                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric("Clusters Found", dbscan_results["n_clusters"])
                        with m2:
                            st.metric("Noise Points", dbscan_results["anomaly_count"])
                        with m3:
                            st.metric("Outlier Rate", f"{dbscan_results['anomaly_pct']}%")
                        
                        st.success(f"Found {dbscan_results['n_clusters']} clusters with {dbscan_results['anomaly_count']} outlier points")
                    else:
                        st.warning(dbscan_results.get("reason", "Clustering failed"))
        
        st.markdown("---")
        
        # Auto-learning thresholds
        st.markdown("### 📚 Auto-Learn Thresholds")
        st.markdown("*Let ML learn what's normal from your historical data*")
        
        learn_col1, learn_col2 = st.columns([2, 1])
        
        with learn_col1:
            confidence = st.slider("Confidence Level", 0.90, 0.99, 0.95, key="confidence")
            
            if st.button("🧠 Learn Thresholds", key="learn_thresh"):
                with st.spinner("Analyzing historical patterns..."):
                    learned = auto_learn_thresholds(
                        row_counts_df,
                        value_column="row_count",
                        confidence_level=confidence
                    )
                    
                    if learned["success"]:
                        st.session_state["learned_thresholds"] = learned
                        
                        # Display learned bounds
                        st.success("✅ Thresholds learned from historical data!")
                        
                        bounds_df = pd.DataFrame({
                            "Method": ["Percentile", "Z-Score", "IQR"],
                            "Lower Bound": [
                                learned["learned_bounds"]["percentile"]["lower"],
                                learned["learned_bounds"]["zscore"]["lower"],
                                learned["learned_bounds"]["iqr"]["lower"]
                            ],
                            "Upper Bound": [
                                learned["learned_bounds"]["percentile"]["upper"],
                                learned["learned_bounds"]["zscore"]["upper"],
                                learned["learned_bounds"]["iqr"]["upper"]
                            ]
                        })
                        st.dataframe(bounds_df, use_container_width=True)
                        
                        # Trend info
                        trend = learned["trend"]
                        st.info(f"📈 Trend: **{trend['direction'].upper()}** (R²: {trend['r_squared']:.2%})")
                        
                        if learned["seasonality"]["has_weekly_pattern"]:
                            st.warning("⚠️ Weekly seasonality detected - using IQR method recommended")
                    else:
                        st.warning(learned.get("reason", "Learning failed"))
        
        with learn_col2:
            st.markdown("**Recommended Method:**")
            if "learned_thresholds" in st.session_state:
                method = st.session_state["learned_thresholds"].get("recommended_method", "percentile")
                st.code(method.upper())
            else:
                st.code("Run learning first")
        
        st.markdown("---")
        
        # ML Forecast
        st.markdown("### 🔮 ML-Powered Forecasting")
        
        forecast_col1, forecast_col2 = st.columns([2, 1])
        
        with forecast_col1:
            alpha = st.slider("Smoothing Factor (α)", 0.1, 0.9, 0.3, 
                            help="Higher = more weight on recent values", key="alpha")
            
            forecast_result = exponential_smoothing_forecast(
                row_counts_df["row_count"],
                alpha=alpha,
                forecast_periods=3
            )
            
            if forecast_result["success"]:
                # Create forecast visualization
                fig_forecast = go.Figure()
                
                # Historical data
                fig_forecast.add_trace(go.Scatter(
                    x=list(range(len(row_counts_df))),
                    y=row_counts_df["row_count"],
                    mode="lines",
                    name="Historical",
                    line=dict(color="#1f77b4")
                ))
                
                # Forecast
                forecast_x = list(range(len(row_counts_df), len(row_counts_df) + 3))
                fig_forecast.add_trace(go.Scatter(
                    x=forecast_x,
                    y=forecast_result["forecast_values"],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(color="#ff7f0e", dash="dash")
                ))
                
                # Confidence interval
                fig_forecast.add_trace(go.Scatter(
                    x=forecast_x + forecast_x[::-1],
                    y=forecast_result["upper_bound"] + forecast_result["lower_bound"][::-1],
                    fill="toself",
                    fillcolor="rgba(255, 127, 14, 0.2)",
                    line=dict(color="rgba(255,255,255,0)"),
                    name="95% CI"
                ))
                
                fig_forecast.update_layout(
                    title="Exponential Smoothing Forecast",
                    xaxis_title="Time Period",
                    yaxis_title="Row Count",
                    height=300
                )
                st.plotly_chart(fig_forecast, use_container_width=True)
        
        with forecast_col2:
            st.markdown("**Forecast Summary:**")
            if forecast_result["success"]:
                st.metric("Next Period", f"{forecast_result['forecast_values'][0]:,.0f}")
                st.metric("Trend", forecast_result["trend"].upper())
                st.metric("Last Actual", f"{forecast_result['last_actual']:,.0f}")
    
    # ==================== TAB 8: Column Profiler ====================
    with tab8:
        st.subheader("📋 Column Profiler")
        st.markdown("*Detailed statistics and quality analysis for each column*")
        
        # Create sample data for profiling
        profile_df = generate_mock_rule_test_data(selected_table)
        
        # Profile all columns
        if st.button("🔍 Profile All Columns", key="profile_all"):
            with st.spinner("Analyzing columns..."):
                full_profile = profile_dataframe(profile_df)
                st.session_state["column_profile"] = full_profile
        
        if "column_profile" in st.session_state:
            profile = st.session_state["column_profile"]
            
            # Overall stats
            st.markdown("### 📊 Dataset Overview")
            ov = profile["overall"]
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Rows", f"{ov['row_count']:,}")
            with m2:
                st.metric("Columns", ov['column_count'])
            with m3:
                st.metric("Quality Score", f"{ov['quality_score']}/100")
            with m4:
                st.metric("Null %", f"{ov['null_pct']}%")
            
            # Column type distribution
            st.markdown("### 📈 Column Types")
            type_df = pd.DataFrame([
                {"Type": k.title(), "Count": v}
                for k, v in ov.get("column_types", {}).items()
            ])
            if not type_df.empty:
                fig_types = px.pie(type_df, values="Count", names="Type", hole=0.4)
                fig_types.update_layout(height=250)
                st.plotly_chart(fig_types, use_container_width=True)
            
            # Per-column profiles
            st.markdown("### 🔍 Column Details")
            
            for col_name, col_profile in profile["columns"].items():
                quality_color = "🟢" if col_profile["quality_score"] >= 80 else "🟡" if col_profile["quality_score"] >= 60 else "🔴"
                
                with st.expander(f"{quality_color} {col_name} ({col_profile['inferred_type']})"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Quality Score", f"{col_profile['quality_score']}/100")
                        st.metric("Null %", f"{col_profile['null_pct']}%")
                    with c2:
                        st.metric("Distinct Values", f"{col_profile['distinct_count']:,}")
                        st.metric("Distinct %", f"{col_profile['distinct_pct']}%")
                    with c3:
                        st.metric("Data Type", col_profile['dtype'])
                        st.metric("Is Unique", "✅" if col_profile['is_unique'] else "❌")
                    
                    # Type-specific stats
                    if col_profile['inferred_type'] == 'numeric':
                        st.markdown("**Numeric Statistics:**")
                        stats_df = pd.DataFrame([{
                            "Mean": col_profile.get('mean'),
                            "Std": col_profile.get('std'),
                            "Min": col_profile.get('min'),
                            "Max": col_profile.get('max'),
                            "Median": col_profile.get('median')
                        }])
                        st.dataframe(stats_df, use_container_width=True)
                        
                        if col_profile.get('outlier_count', 0) > 0:
                            st.warning(f"⚠️ {col_profile['outlier_count']} outliers detected ({col_profile['outlier_pct']}%)")
                    
                    # Quality issues
                    issues = col_profile.get('quality_issues', [])
                    if issues:
                        st.markdown("**⚠️ Quality Issues:**")
                        for issue in issues:
                            st.error(issue)
                    
                    # Top values
                    if col_profile.get('top_values'):
                        st.markdown("**Top Values:**")
                        top_df = pd.DataFrame(col_profile['top_values'])
                        st.dataframe(top_df, use_container_width=True)
        else:
            st.info("Click 'Profile All Columns' to analyze the data")
    
    # ==================== TAB 9: History ====================
    with tab9:
        st.subheader("📜 Historical Dashboard")
        st.markdown("*Track anomalies and health scores over time*")
        
        # Generate mock historical data for demo
        history_data = generate_mock_history(selected_table, days=30)
        history_df = pd.DataFrame(history_data)
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
        
        # Summary metrics
        st.markdown("### 📊 30-Day Summary")
        h1, h2, h3, h4 = st.columns(4)
        
        with h1:
            avg_score = history_df["health_score"].mean()
            st.metric("Avg Health Score", f"{avg_score:.0f}")
        with h2:
            min_score = history_df["health_score"].min()
            st.metric("Lowest Score", f"{min_score}")
        with h3:
            total_anomalies = history_df["anomaly_count"].sum()
            st.metric("Total Anomalies", f"{total_anomalies}")
        with h4:
            healthy_days = (history_df["status"] == "Healthy").sum()
            st.metric("Healthy Days", f"{healthy_days}/30")
        
        # Health score trend
        st.markdown("### 📈 Health Score Trend")
        fig_trend = go.Figure()
        
        fig_trend.add_trace(go.Scatter(
            x=history_df["timestamp"],
            y=history_df["health_score"],
            mode="lines+markers",
            name="Health Score",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.1)"
        ))
        
        # Add threshold lines
        fig_trend.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Healthy")
        fig_trend.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Warning")
        
        fig_trend.update_layout(
            height=350,
            yaxis=dict(range=[0, 105]),
            xaxis_title="Date",
            yaxis_title="Health Score"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Anomaly count over time
        st.markdown("### 🚨 Anomaly Frequency")
        fig_anomalies = px.bar(
            history_df,
            x="timestamp",
            y="anomaly_count",
            color="status",
            color_discrete_map={"Healthy": "green", "Warning": "orange", "Critical": "red"}
        )
        fig_anomalies.update_layout(height=250, showlegend=True)
        st.plotly_chart(fig_anomalies, use_container_width=True)
        
        # Recent incidents
        st.markdown("### 📋 Recent Incidents")
        incidents = history_df[history_df["anomaly_count"] > 0].sort_values("timestamp", ascending=False).head(5)
        
        if len(incidents) > 0:
            for _, row in incidents.iterrows():
                status_color = "🔴" if row["status"] == "Critical" else "🟠" if row["status"] == "Warning" else "🟢"
                with st.expander(f"{status_color} {row['timestamp'].strftime('%Y-%m-%d')} - {row['anomaly_count']} anomalies"):
                    st.metric("Health Score", row["health_score"])
                    if row["anomalies"]:
                        for a in row["anomalies"]:
                            st.write(f"• **{a.get('metric', 'Unknown')}**: {a.get('type', 'anomaly')} ({a.get('severity', 'medium')})")
        else:
            st.success("✅ No incidents in the last 30 days!")
    
    # ==================== TAB 10: Alerts ====================
    with tab10:
        st.subheader("🔔 Alert Configuration")
        st.markdown("*Set up Slack and Email notifications for anomalies*")
        
        alert_col1, alert_col2 = st.columns(2)
        
        with alert_col1:
            st.markdown("### 💬 Slack Alerts")
            st.markdown("Send real-time alerts to your Slack channel")
            
            slack_webhook = st.text_input(
                "Slack Webhook URL",
                placeholder="https://hooks.slack.com/services/...",
                type="password",
                key="slack_webhook"
            )
            
            slack_enabled = st.checkbox("Enable Slack Alerts", key="slack_enabled")
            
            if slack_webhook and st.button("🧪 Test Slack", key="test_slack"):
                try:
                    notifier = SlackNotifier(slack_webhook)
                    success = notifier.send_alert(
                        title="Test Alert from DataPulse",
                        message="If you see this, Slack integration is working! 🎉",
                        severity="low",
                        fields=[
                            {"title": "Table", "value": selected_table},
                            {"title": "Status", "value": "Test"}
                        ]
                    )
                    if success:
                        st.success("✅ Test alert sent to Slack!")
                    else:
                        st.error("❌ Failed to send. Check your webhook URL.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            
            st.markdown("---")
            st.markdown("**Alert Conditions:**")
            slack_on_critical = st.checkbox("Alert on Critical issues", value=True, key="slack_critical")
            slack_on_warning = st.checkbox("Alert on Warning issues", value=False, key="slack_warning")
            slack_on_schema = st.checkbox("Alert on Schema changes", value=True, key="slack_schema")
        
        with alert_col2:
            st.markdown("### 📧 Email Reports")
            st.markdown("Receive daily summary reports via email")
            
            email_recipients = st.text_area(
                "Email Recipients (one per line)",
                placeholder="team@company.com\nmanager@company.com",
                height=100,
                key="email_recipients"
            )
            
            email_enabled = st.checkbox("Enable Email Reports", key="email_enabled")
            
            report_frequency = st.selectbox(
                "Report Frequency",
                ["Daily", "Weekly", "On Anomaly Only"],
                key="report_freq"
            )
            
            st.markdown("---")
            st.markdown("**Email Preview:**")
            
            preview_html = generate_alert_html(
                table_name=selected_table,
                health_score=health_score,
                anomalies=row_anomalies + null_anomalies
            )
            
            with st.expander("📄 Preview Email Content"):
                st.components.v1.html(preview_html, height=400, scrolling=True)
        
        # Alert history (mock)
        st.markdown("---")
        st.markdown("### 📜 Recent Alerts Sent")
        
        alert_history = pd.DataFrame([
            {"Time": "2026-05-19 10:30", "Type": "Slack", "Table": "orders", "Reason": "Row count drop"},
            {"Time": "2026-05-18 09:00", "Type": "Email", "Table": "users", "Reason": "Daily report"},
            {"Time": "2026-05-17 14:22", "Type": "Slack", "Table": "events", "Reason": "Schema change"},
        ])
        st.dataframe(alert_history, use_container_width=True)
        
        # Save settings
        st.markdown("---")
        if st.button("💾 Save Alert Settings", key="save_alerts"):
            st.success("✅ Alert settings saved! (Demo mode - settings not persisted)")
    
    # ==================== TAB 11: PII Detection ====================
    with tab11:
        st.subheader("🔐 PII Detection")
        st.markdown("*Scan data for personally identifiable information (100% local processing)*")
        
        # Use sample data
        pii_df = generate_mock_rule_test_data(selected_table)
        
        if st.button("🔍 Scan for PII", key="scan_pii"):
            with st.spinner("Scanning for PII patterns..."):
                pii_results = scan_dataframe_for_pii(pii_df)
                st.session_state["pii_results"] = pii_results
        
        if "pii_results" in st.session_state:
            results = st.session_state["pii_results"]
            
            # Risk overview
            st.markdown("### 🎯 Risk Overview")
            risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)
            
            with risk_col1:
                risk_color = "🔴" if results["risk_level"] == "Critical" else "🟠" if results["risk_level"] == "High" else "🟡" if results["risk_level"] == "Medium" else "🟢"
                st.metric("Risk Level", f"{risk_color} {results['risk_level']}")
            with risk_col2:
                st.metric("Risk Score", f"{results['risk_score']}/100")
            with risk_col3:
                st.metric("PII Columns", results["columns_with_pii"])
            with risk_col4:
                st.metric("Total Findings", results["total_findings"])
            
            # Risk breakdown chart
            st.markdown("### 📊 Risk Breakdown")
            risk_df = pd.DataFrame([
                {"Level": k.title(), "Count": v}
                for k, v in results["risk_counts"].items() if v > 0
            ])
            if not risk_df.empty:
                fig_risk = px.bar(risk_df, x="Level", y="Count", 
                                  color="Level",
                                  color_discrete_map={"Critical": "red", "High": "orange", "Medium": "yellow", "Low": "green"})
                fig_risk.update_layout(height=250, showlegend=False)
                st.plotly_chart(fig_risk, use_container_width=True)
            
            # Detailed findings
            st.markdown("### 🔍 Detailed Findings")
            
            for finding in results["findings"]:
                severity_icon = "🔴" if finding.risk_level == "critical" else "🟠" if finding.risk_level == "high" else "🟡" if finding.risk_level == "medium" else "🟢"
                
                with st.expander(f"{severity_icon} {finding.column} - {finding.pii_type}"):
                    f1, f2, f3 = st.columns(3)
                    with f1:
                        st.metric("Matches", f"{finding.sample_count}/{finding.total_values}")
                    with f2:
                        st.metric("Match Rate", f"{finding.percentage}%")
                    with f3:
                        st.metric("Confidence", finding.confidence.title())
                    
                    # Masking recommendation
                    st.info(f"💡 **Recommendation:** {get_masking_recommendation(finding.pii_type)}")
        else:
            st.info("Click 'Scan for PII' to analyze the data for sensitive information")
    
    # ==================== TAB 12: Data Lineage ====================
    with tab12:
        st.subheader("🌐 Data Lineage")
        st.markdown("*Visualize data flow and table relationships*")
        
        # Generate mock lineage
        lineage = generate_mock_lineage()
        lineage_stats = get_lineage_stats(lineage)
        
        # Overview metrics
        st.markdown("### 📊 Lineage Overview")
        l1, l2, l3, l4 = st.columns(4)
        with l1:
            st.metric("Total Tables", lineage_stats["total_tables"])
        with l2:
            st.metric("Data Flows", lineage_stats["total_edges"])
        with l3:
            st.metric("Max Depth", lineage_stats["max_depth"])
        with l4:
            st.metric("Source Tables", len(lineage_stats["root_tables"]))
        
        # Schema breakdown
        st.markdown("### 🗂️ Tables by Layer")
        schema_df = pd.DataFrame([
            {"Layer": k.title(), "Tables": v}
            for k, v in lineage_stats["schema_breakdown"].items()
        ])
        fig_schema = px.pie(schema_df, values="Tables", names="Layer", hole=0.4)
        fig_schema.update_layout(height=300)
        st.plotly_chart(fig_schema, use_container_width=True)
        
        # Lineage graph (Mermaid)
        st.markdown("### 🔗 Lineage Graph")
        mermaid_code = lineage.to_mermaid()
        st.code(mermaid_code, language="mermaid")
        
        # Impact analysis
        st.markdown("### 💥 Impact Analysis")
        selected_lineage_table = st.selectbox(
            "Select a table to analyze impact:",
            list(lineage.nodes.keys()),
            key="lineage_table"
        )
        
        if selected_lineage_table:
            impact = lineage.get_impact_analysis(selected_lineage_table)
            
            ic1, ic2 = st.columns(2)
            with ic1:
                st.metric("Downstream Tables", impact["impact_count"])
                st.metric("Risk Level", impact["risk_level"].upper())
            with ic2:
                st.markdown("**Direct Dependents:**")
                for dep in impact["direct_dependents"][:5]:
                    st.write(f"  → {dep}")
            
            if impact["all_downstream"]:
                st.markdown("**Full Impact Chain:**")
                st.write(" → ".join([selected_lineage_table] + impact["all_downstream"][:8]))
    
    # ==================== TAB 13: SQL Rules ====================
    with tab13:
        st.subheader("📝 Custom SQL Rules")
        st.markdown("*Define and execute custom data quality rules*")
        
        # Rule builder
        st.markdown("### ➕ Create New Rule")
        
        rule_col1, rule_col2 = st.columns(2)
        
        with rule_col1:
            rule_name = st.text_input("Rule Name", "My Custom Rule", key="rule_name")
            rule_type = st.selectbox(
                "Rule Type",
                ["null_check", "range_check", "regex_check", "uniqueness_check", "custom_condition"],
                key="rule_type"
            )
            rule_column = st.text_input("Column Name", "id", key="rule_column")
        
        with rule_col2:
            rule_severity = st.selectbox("Severity", ["critical", "high", "medium", "low"], key="rule_severity")
            
            # Dynamic parameters based on rule type
            if rule_type == "null_check":
                max_null = st.number_input("Max Null %", 0, 100, 0, key="max_null")
                rule_params = {"max_null_pct": max_null}
            elif rule_type == "range_check":
                min_val = st.number_input("Min Value", value=0, key="min_val")
                max_val = st.number_input("Max Value", value=100, key="max_val")
                rule_params = {"min_value": min_val, "max_value": max_val}
            elif rule_type == "regex_check":
                pattern = st.text_input("Regex Pattern", r"^[A-Za-z]+$", key="regex_pattern")
                rule_params = {"pattern": pattern}
            else:
                rule_params = {}
        
        # Initialize rules engine
        if "sql_rules_engine" not in st.session_state:
            st.session_state["sql_rules_engine"] = SQLRulesEngine()
            # Add predefined rules
            for rule in get_predefined_rules():
                st.session_state["sql_rules_engine"].add_rule(rule)
        
        if st.button("➕ Add Rule", key="add_rule"):
            new_rule = SQLRule(
                name=rule_name,
                description=f"Custom {rule_type} rule",
                rule_type=rule_type,
                severity=rule_severity,
                column=rule_column,
                parameters=rule_params
            )
            st.session_state["sql_rules_engine"].add_rule(new_rule)
            st.success(f"✅ Rule '{rule_name}' added!")
        
        # Current rules
        st.markdown("### 📋 Active Rules")
        engine = st.session_state["sql_rules_engine"]
        
        rules_df = pd.DataFrame([
            {
                "Name": r.name,
                "Type": r.rule_type,
                "Column": r.column or "N/A",
                "Severity": r.severity.upper(),
                "Enabled": "✅" if r.enabled else "❌"
            }
            for r in engine.rules
        ])
        st.dataframe(rules_df, use_container_width=True)
        
        # Execute rules
        st.markdown("### ▶️ Execute Rules")
        if st.button("🚀 Run All Rules", key="run_rules"):
            test_df = generate_mock_rule_test_data(selected_table)
            
            with st.spinner("Executing rules..."):
                results = engine.execute_all_rules(test_df)
                summary = engine.get_summary()
            
            # Summary
            s1, s2, s3 = st.columns(3)
            with s1:
                st.metric("Total Rules", summary["total"])
            with s2:
                st.metric("Passed", summary["passed"], delta=None)
            with s3:
                st.metric("Failed", summary["failed"], delta=f"-{summary['failed']}" if summary["failed"] > 0 else None)
            
            # Results
            for result in results:
                icon = "✅" if result.passed else "❌"
                color = "green" if result.passed else "red"
                
                with st.expander(f"{icon} {result.rule_name}"):
                    st.markdown(f"**Status:** {'PASSED' if result.passed else 'FAILED'}")
                    st.markdown(f"**Message:** {result.message}")
                    st.markdown(f"**Rows Checked:** {result.rows_checked:,}")
                    st.markdown(f"**Failure Rate:** {result.failure_rate:.2f}%")
                    st.markdown(f"**Execution Time:** {result.execution_time_ms:.2f}ms")
    
    # ==================== TAB 14: Drift Detection ====================
    with tab14:
        st.subheader("📉 Statistical Drift Detection")
        st.markdown("*Detect distribution changes using statistical tests (KS-test, Chi-Square, PSI)*")
        
        if st.button("🔍 Run Drift Analysis", key="run_drift"):
            with st.spinner("Analyzing distributions..."):
                baseline_df, current_df = generate_mock_drift_data(selected_table)
                detector = DriftDetector(significance_level=0.05)
                drift_results = detector.detect_drift_dataframe(baseline_df, current_df)
                drift_summary = detector.get_drift_summary(drift_results)
                
                st.session_state["drift_results"] = drift_results
                st.session_state["drift_summary"] = drift_summary
        
        if "drift_results" in st.session_state:
            summary = st.session_state["drift_summary"]
            results = st.session_state["drift_results"]
            
            # Overview
            st.markdown("### 📊 Drift Overview")
            d1, d2, d3, d4 = st.columns(4)
            with d1:
                health_color = "🔴" if summary["overall_health"] == "Critical" else "🟠" if summary["overall_health"] == "Warning" else "🟡" if summary["overall_health"] == "Moderate" else "🟢"
                st.metric("Health", f"{health_color} {summary['overall_health']}")
            with d2:
                st.metric("Columns Analyzed", summary["total_columns"])
            with d3:
                st.metric("With Drift", summary["columns_with_drift"])
            with d4:
                st.metric("Drift Rate", f"{summary['drift_rate']:.1f}%")
            
            # Drift heatmap
            st.markdown("### 🗺️ Drift Scores")
            drift_scores = pd.DataFrame([
                {"Column": r.column, "Drift Score": r.drift_score, "Severity": r.severity}
                for r in results
            ])
            
            fig_drift = px.bar(
                drift_scores,
                x="Column",
                y="Drift Score",
                color="Severity",
                color_discrete_map={"critical": "red", "high": "orange", "medium": "yellow", "low": "lightgreen", "none": "green"}
            )
            fig_drift.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="High Risk")
            fig_drift.update_layout(height=350)
            st.plotly_chart(fig_drift, use_container_width=True)
            
            # Detailed results
            st.markdown("### 🔬 Column Details")
            
            for result in results:
                severity_icon = "🔴" if result.severity == "critical" else "🟠" if result.severity == "high" else "🟡" if result.severity == "medium" else "🟢"
                
                with st.expander(f"{severity_icon} {result.column} (Score: {result.drift_score})"):
                    dc1, dc2 = st.columns(2)
                    
                    with dc1:
                        st.markdown("**Baseline Stats:**")
                        for k, v in result.baseline_stats.items():
                            st.write(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")
                    
                    with dc2:
                        st.markdown("**Current Stats:**")
                        for k, v in result.current_stats.items():
                            st.write(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")
                    
                    st.markdown(f"**Test Used:** {result.test_used}")
                    st.markdown(f"**P-Value:** {result.p_value}")
                    st.info(f"💡 {result.recommendation}")
        else:
            st.info("Click 'Run Drift Analysis' to compare baseline vs current distributions")
    
    # ==================== TAB 15: Root Cause Analysis ====================
    with tab15:
        st.subheader("🔬 Root Cause Analysis")
        st.markdown("*Automatically identify why anomalies occurred*")
        
        if st.button("🔍 Run Root Cause Analysis", key="run_rca"):
            with st.spinner("Analyzing root causes..."):
                baseline_df, current_df = generate_mock_rca_data()
                analyzer = RootCauseAnalyzer()
                
                rca_result = analyzer.analyze_anomaly(
                    baseline_df, current_df,
                    metric_col="revenue",
                    dimension_cols=["region", "product", "channel"],
                    anomaly_type="Revenue Drop"
                )
                
                st.session_state["rca_result"] = rca_result
        
        if "rca_result" in st.session_state:
            result = st.session_state["rca_result"]
            
            # Anomaly overview
            st.markdown("### 🎯 Anomaly Overview")
            a1, a2, a3 = st.columns(3)
            with a1:
                st.metric("Anomaly Type", result.anomaly_type)
            with a2:
                st.metric("Expected", f"{result.expected_value:,.0f}")
            with a3:
                delta_color = "inverse" if result.deviation_pct < 0 else "normal"
                st.metric("Actual", f"{result.anomaly_value:,.0f}", 
                         delta=f"{result.deviation_pct:+.1f}%")
            
            # Summary
            st.markdown("### 📝 Summary")
            st.info(result.summary)
            
            # Root causes
            st.markdown("### 🔍 Root Causes")
            
            if result.root_causes:
                # Contribution chart
                causes_df = pd.DataFrame([
                    {
                        "Segment": f"{c.dimension}={c.value}",
                        "Contribution": abs(c.contribution),
                        "Direction": "Increase" if c.contribution > 0 else "Decrease"
                    }
                    for c in result.root_causes
                ])
                
                fig_causes = px.bar(
                    causes_df,
                    x="Segment",
                    y="Contribution",
                    color="Direction",
                    color_discrete_map={"Increase": "green", "Decrease": "red"}
                )
                fig_causes.update_layout(height=300, yaxis_title="Contribution %")
                st.plotly_chart(fig_causes, use_container_width=True)
                
                # Detailed causes
                for cause in result.root_causes:
                    confidence_icon = "🔴" if cause.confidence == "high" else "🟠" if cause.confidence == "medium" else "🟡"
                    
                    with st.expander(f"{confidence_icon} {cause.dimension} = '{cause.value}'"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.metric("Baseline", f"{cause.baseline_value:,.0f}")
                        with c2:
                            st.metric("Current", f"{cause.current_value:,.0f}")
                        with c3:
                            st.metric("Change", f"{cause.change_pct:+.1f}%")
                        
                        st.markdown(f"**Contribution:** {cause.contribution:+.1f}%")
                        st.markdown(f"**Confidence:** {cause.confidence.upper()}")
                        st.write(cause.explanation)
            
            # Recommendations
            st.markdown("### 💡 Recommendations")
            recommendations = get_rca_recommendations(result)
            for rec in recommendations:
                st.write(rec)
        else:
            st.info("Click 'Run Root Cause Analysis' to diagnose anomalies")
    
    # ==================== TAB 16: Data Contracts ====================
    with tab16:
        st.subheader("📄 Data Contracts")
        st.markdown("*Define and enforce data quality SLAs using YAML contracts*")
        
        # Contract editor
        st.markdown("### 📝 Contract Editor")
        
        # Template selector
        templates = get_contract_templates()
        template_choice = st.selectbox(
            "Start from template:",
            ["Custom"] + list(templates.keys()),
            key="contract_template"
        )
        
        # Get initial contract text
        if template_choice == "Custom":
            default_contract = get_sample_contract()
        else:
            default_contract = templates[template_choice]
        
        # Contract YAML editor
        contract_yaml = st.text_area(
            "Contract YAML",
            value=default_contract,
            height=400,
            key="contract_yaml"
        )
        
        # Validate and parse
        col_validate, col_run = st.columns(2)
        
        with col_validate:
            if st.button("✅ Validate Contract", key="validate_contract"):
                result = parse_contract_yaml(contract_yaml)
                if result["valid"]:
                    st.success("✅ Contract YAML is valid!")
                    st.session_state["parsed_contract"] = result["config"]
                else:
                    st.error(f"❌ {result['error']}")
        
        with col_run:
            if st.button("🚀 Run Contract Validation", key="run_contract"):
                try:
                    # Parse contract
                    contract = DataContract(contract_yaml)
                    
                    # Get test data
                    test_df = generate_mock_rule_test_data(selected_table)
                    
                    # Run validation (datetime already imported at top of file)
                    last_updated = datetime.now() - timedelta(hours=2)  # Mock freshness
                    
                    validation = contract.validate(test_df, last_updated)
                    st.session_state["contract_validation"] = validation
                    st.session_state["contract_obj"] = contract
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Show validation results
        if "contract_validation" in st.session_state:
            validation = st.session_state["contract_validation"]
            contract = st.session_state["contract_obj"]
            
            st.markdown("---")
            st.markdown("### 📊 Validation Results")
            
            # Status banner
            status_colors = {
                "passing": ("🟢", "green", "All SLAs Passing"),
                "warning": ("🟡", "orange", "Some Warnings"),
                "failing": ("🔴", "red", "SLA Violations Detected"),
                "not_evaluated": ("⚪", "gray", "Not Evaluated")
            }
            icon, color, text = status_colors.get(validation.status.value, ("⚪", "gray", "Unknown"))
            
            # Summary metrics
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.metric("Status", f"{icon} {text}")
            with s2:
                st.metric("Score", f"{validation.overall_score}%")
            with s3:
                st.metric("Passed", validation.passed_count)
            with s4:
                st.metric("Failed", validation.failed_count, 
                         delta=f"-{validation.failed_count}" if validation.failed_count > 0 else None,
                         delta_color="inverse")
            
            # Contract info
            st.markdown("### 📋 Contract Info")
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.write(f"**Name:** {contract.name}")
                st.write(f"**Version:** {contract.version}")
            with info_col2:
                st.write(f"**Owner:** {contract.owner}")
                st.write(f"**Dataset:** {contract.dataset.get('name', 'N/A')}")
            
            # SLA checks detail
            st.markdown("### 🔍 SLA Check Details")
            
            # Group by SLA type
            sla_types = {}
            for check in validation.sla_checks:
                if check.sla_type not in sla_types:
                    sla_types[check.sla_type] = []
                sla_types[check.sla_type].append(check)
            
            for sla_type, checks in sla_types.items():
                passed_in_type = sum(1 for c in checks if c.passed)
                type_icon = "✅" if passed_in_type == len(checks) else "⚠️" if passed_in_type > 0 else "❌"
                
                with st.expander(f"{type_icon} {sla_type.upper()} ({passed_in_type}/{len(checks)} passing)"):
                    for check in checks:
                        check_icon = "✅" if check.passed else "❌"
                        severity_badge = f"[{check.severity.upper()}]"
                        
                        st.markdown(f"""
                        **{check_icon} {check.name}** {severity_badge}
                        - Expected: `{check.expected}`
                        - Actual: `{check.actual}`
                        - {check.message}
                        """)
            
            # Export contract
            st.markdown("---")
            st.markdown("### 💾 Export")
            
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                st.download_button(
                    "📥 Download Contract YAML",
                    contract_yaml,
                    file_name=f"{contract.name}.yaml",
                    mime="text/yaml"
                )
            with export_col2:
                # Create validation report
                report = f"""# Contract Validation Report
Contract: {contract.name}
Date: {validation.timestamp}
Status: {validation.status.value.upper()}
Score: {validation.overall_score}%

## Summary
- Passed: {validation.passed_count}
- Failed: {validation.failed_count}
- Warnings: {validation.warning_count}

## SLA Checks
"""
                for check in validation.sla_checks:
                    status = "PASS" if check.passed else "FAIL"
                    report += f"- [{status}] {check.name}: {check.message}\n"
                
                st.download_button(
                    "📥 Download Report",
                    report,
                    file_name=f"{contract.name}_report.md",
                    mime="text/markdown"
                )
    
    # Health Score Breakdown
    st.markdown("---")
    st.subheader("📊 Health Score Breakdown")
    
    breakdown_df = pd.DataFrame([
        {"Dimension": "Row Count", "Score": score_breakdown["row_count"], "Weight": "20%"},
        {"Dimension": "Null Rate", "Score": score_breakdown["null_rate"], "Weight": "15%"},
        {"Dimension": "Schema", "Score": score_breakdown["schema"], "Weight": "15%"},
        {"Dimension": "Freshness", "Score": score_breakdown["freshness"], "Weight": "15%"},
        {"Dimension": "Distribution", "Score": score_breakdown["distribution"], "Weight": "10%"},
        {"Dimension": "Duplicates", "Score": score_breakdown["duplicates"], "Weight": "15%"},
        {"Dimension": "Rules", "Score": score_breakdown["rules"], "Weight": "10%"},
    ])
    
    fig_breakdown = px.bar(
        breakdown_df,
        x="Dimension",
        y="Score",
        color="Score",
        color_continuous_scale=["red", "yellow", "green"],
        range_color=[0, 100],
        text="Score"
    )
    fig_breakdown.update_layout(height=300, showlegend=False)
    fig_breakdown.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Healthy")
    fig_breakdown.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Warning")
    st.plotly_chart(fig_breakdown, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        Built with ❤️ by <b>Ctrl Alt Defeat!</b> | Data Platform Ops Hackathon 2026
        </div>
        """, 
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
