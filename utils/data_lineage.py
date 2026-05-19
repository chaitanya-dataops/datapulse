"""
Data Lineage Module for DataPulse
Tracks data flow and table relationships
100% local processing - no external services
"""

from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class TableNode:
    """Represents a table in the lineage graph"""
    name: str
    schema: str = "public"
    database: str = "main"
    columns: List[str] = field(default_factory=list)
    row_count: int = 0
    last_updated: str = ""
    node_type: str = "table"  # table, view, external


@dataclass
class LineageEdge:
    """Represents a data flow between tables"""
    source: str
    target: str
    transformation: str = "SELECT"
    columns_affected: List[str] = field(default_factory=list)
    sql_snippet: str = ""


class DataLineageTracker:
    """Track and visualize data lineage"""
    
    def __init__(self):
        self.nodes: Dict[str, TableNode] = {}
        self.edges: List[LineageEdge] = []
    
    def add_table(self, name: str, **kwargs) -> None:
        """Add a table node to the lineage graph"""
        self.nodes[name] = TableNode(name=name, **kwargs)
    
    def add_edge(self, source: str, target: str, **kwargs) -> None:
        """Add a lineage edge (data flow)"""
        self.edges.append(LineageEdge(source=source, target=target, **kwargs))
    
    def parse_sql_for_lineage(self, sql: str) -> List[LineageEdge]:
        """
        Parse SQL to extract lineage relationships
        Supports basic SELECT, INSERT, CREATE TABLE AS patterns
        """
        edges = []
        sql_upper = sql.upper()
        
        # Extract target table
        target = None
        
        # INSERT INTO pattern
        insert_match = re.search(r'INSERT\s+INTO\s+(\w+)', sql_upper)
        if insert_match:
            target = insert_match.group(1).lower()
        
        # CREATE TABLE AS pattern
        create_match = re.search(r'CREATE\s+TABLE\s+(\w+)\s+AS', sql_upper)
        if create_match:
            target = create_match.group(1).lower()
        
        # Extract source tables from FROM and JOIN clauses
        from_pattern = r'FROM\s+(\w+)'
        join_pattern = r'JOIN\s+(\w+)'
        
        sources = set()
        for match in re.finditer(from_pattern, sql_upper):
            sources.add(match.group(1).lower())
        for match in re.finditer(join_pattern, sql_upper):
            sources.add(match.group(1).lower())
        
        # Create edges
        if target and sources:
            for source in sources:
                if source != target:  # Avoid self-loops
                    edges.append(LineageEdge(
                        source=source,
                        target=target,
                        transformation="SQL",
                        sql_snippet=sql[:200] + "..." if len(sql) > 200 else sql
                    ))
        
        return edges
    
    def get_upstream_tables(self, table_name: str) -> Set[str]:
        """Get all tables that feed into this table"""
        upstream = set()
        
        def find_upstream(t: str, visited: Set[str]):
            for edge in self.edges:
                if edge.target == t and edge.source not in visited:
                    upstream.add(edge.source)
                    visited.add(edge.source)
                    find_upstream(edge.source, visited)
        
        find_upstream(table_name, set())
        return upstream
    
    def get_downstream_tables(self, table_name: str) -> Set[str]:
        """Get all tables that this table feeds into"""
        downstream = set()
        
        def find_downstream(t: str, visited: Set[str]):
            for edge in self.edges:
                if edge.source == t and edge.target not in visited:
                    downstream.add(edge.target)
                    visited.add(edge.target)
                    find_downstream(edge.target, visited)
        
        find_downstream(table_name, set())
        return downstream
    
    def get_impact_analysis(self, table_name: str) -> Dict[str, Any]:
        """Analyze impact of changes to a table"""
        downstream = self.get_downstream_tables(table_name)
        
        return {
            "table": table_name,
            "direct_dependents": [e.target for e in self.edges if e.source == table_name],
            "all_downstream": list(downstream),
            "impact_count": len(downstream),
            "risk_level": "high" if len(downstream) > 5 else "medium" if len(downstream) > 2 else "low"
        }
    
    def to_mermaid(self) -> str:
        """Export lineage as Mermaid diagram"""
        lines = ["graph LR"]
        
        for edge in self.edges:
            lines.append(f"    {edge.source}[{edge.source}] --> {edge.target}[{edge.target}]")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export lineage as dictionary for visualization"""
        return {
            "nodes": [
                {
                    "id": name,
                    "label": name,
                    "type": node.node_type,
                    "schema": node.schema,
                    "columns": node.columns
                }
                for name, node in self.nodes.items()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "transformation": edge.transformation
                }
                for edge in self.edges
            ]
        }


def generate_mock_lineage() -> DataLineageTracker:
    """Generate mock lineage data for demo purposes"""
    tracker = DataLineageTracker()
    
    # Add tables
    tables = [
        ("raw_events", "raw", ["id", "event_type", "user_id", "timestamp", "payload"]),
        ("raw_users", "raw", ["id", "email", "name", "created_at"]),
        ("raw_orders", "raw", ["id", "user_id", "product_id", "amount", "created_at"]),
        ("stg_events", "staging", ["event_id", "event_type", "user_id", "event_date"]),
        ("stg_users", "staging", ["user_id", "email_hash", "name", "signup_date"]),
        ("stg_orders", "staging", ["order_id", "user_id", "product_id", "amount", "order_date"]),
        ("dim_users", "mart", ["user_key", "user_id", "name", "segment", "tenure_days"]),
        ("dim_products", "mart", ["product_key", "product_id", "name", "category"]),
        ("fct_orders", "mart", ["order_key", "user_key", "product_key", "amount", "order_date"]),
        ("fct_events", "mart", ["event_key", "user_key", "event_type", "event_date"]),
        ("agg_daily_sales", "analytics", ["date", "total_orders", "total_revenue", "unique_users"]),
        ("agg_user_metrics", "analytics", ["user_key", "total_orders", "lifetime_value", "last_order_date"]),
        ("report_executive", "reports", ["date", "revenue", "orders", "new_users", "churn_rate"])
    ]
    
    for name, schema, columns in tables:
        tracker.add_table(name, schema=schema, columns=columns)
    
    # Add lineage edges (data flow)
    edges = [
        # Raw to Staging
        ("raw_events", "stg_events", "Clean & Dedupe"),
        ("raw_users", "stg_users", "PII Mask"),
        ("raw_orders", "stg_orders", "Validate & Clean"),
        
        # Staging to Dimensions
        ("stg_users", "dim_users", "SCD Type 2"),
        ("stg_orders", "dim_products", "Distinct Products"),
        
        # Staging to Facts
        ("stg_events", "fct_events", "Join with dim_users"),
        ("stg_orders", "fct_orders", "Join with dims"),
        ("dim_users", "fct_orders", "User Key Lookup"),
        ("dim_products", "fct_orders", "Product Key Lookup"),
        ("dim_users", "fct_events", "User Key Lookup"),
        
        # Facts to Aggregates
        ("fct_orders", "agg_daily_sales", "Daily Aggregation"),
        ("fct_orders", "agg_user_metrics", "User Aggregation"),
        ("fct_events", "agg_user_metrics", "Event Metrics"),
        
        # Aggregates to Reports
        ("agg_daily_sales", "report_executive", "Executive Summary"),
        ("agg_user_metrics", "report_executive", "User Metrics"),
    ]
    
    for source, target, transform in edges:
        tracker.add_edge(source, target, transformation=transform)
    
    return tracker


def get_lineage_stats(tracker: DataLineageTracker) -> Dict[str, Any]:
    """Get statistics about the lineage graph"""
    # Count tables by schema
    schema_counts = {}
    for node in tracker.nodes.values():
        schema_counts[node.schema] = schema_counts.get(node.schema, 0) + 1
    
    # Find root tables (no upstream)
    roots = []
    for name in tracker.nodes:
        upstream = tracker.get_upstream_tables(name)
        if not upstream:
            roots.append(name)
    
    # Find leaf tables (no downstream)
    leaves = []
    for name in tracker.nodes:
        downstream = tracker.get_downstream_tables(name)
        if not downstream:
            leaves.append(name)
    
    # Calculate max depth
    def get_depth(table: str, visited: Set[str]) -> int:
        if table in visited:
            return 0
        visited.add(table)
        downstream = [e.target for e in tracker.edges if e.source == table]
        if not downstream:
            return 0
        return 1 + max(get_depth(d, visited.copy()) for d in downstream)
    
    max_depth = max(get_depth(r, set()) for r in roots) if roots else 0
    
    return {
        "total_tables": len(tracker.nodes),
        "total_edges": len(tracker.edges),
        "schema_breakdown": schema_counts,
        "root_tables": roots,
        "leaf_tables": leaves,
        "max_depth": max_depth + 1,  # +1 for root level
        "avg_connections": len(tracker.edges) / len(tracker.nodes) if tracker.nodes else 0
    }
