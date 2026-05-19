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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Volume & Nulls",
        "🔄 Schema Changes", 
        "⏰ Freshness",
        "📊 Distribution",
        "🔍 Duplicates",
        "✅ Custom Rules",
        "🤖 ML Detection"
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
