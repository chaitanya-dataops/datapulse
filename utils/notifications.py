"""
Notification system for DataPulse
Supports Slack webhooks and Email alerts
"""
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime
import json


class SlackNotifier:
    """Send alerts to Slack via webhooks"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "medium",
        fields: Optional[List[Dict]] = None
    ) -> bool:
        """
        Send an alert to Slack
        
        Args:
            title: Alert title
            message: Alert message
            severity: low, medium, high, critical
            fields: Additional fields to display
        
        Returns:
            True if sent successfully
        """
        color_map = {
            "low": "#36a64f",      # green
            "medium": "#ffcc00",   # yellow
            "high": "#ff9900",     # orange
            "critical": "#ff0000"  # red
        }
        
        emoji_map = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🔶",
            "critical": "🚨"
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji_map.get(severity, '📊')} DataPulse Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n{message}"
                }
            }
        ]
        
        # Add fields if provided
        if fields:
            field_blocks = []
            for field in fields:
                field_blocks.append({
                    "type": "mrkdwn",
                    "text": f"*{field['title']}*\n{field['value']}"
                })
            
            blocks.append({
                "type": "section",
                "fields": field_blocks[:10]  # Slack limit
            })
        
        # Add timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })
        
        payload = {
            "blocks": blocks,
            "attachments": [
                {
                    "color": color_map.get(severity, "#808080"),
                    "text": ""
                }
            ]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Slack notification failed: {e}")
            return False
    
    def send_anomaly_summary(
        self,
        table_name: str,
        health_score: int,
        anomalies: List[Dict]
    ) -> bool:
        """Send a summary of anomalies for a table"""
        
        severity = "critical" if health_score < 50 else "high" if health_score < 70 else "medium"
        
        anomaly_text = "\n".join([
            f"• {a.get('metric', 'Unknown')}: {a.get('type', 'anomaly')} ({a.get('severity', 'unknown')})"
            for a in anomalies[:5]
        ])
        
        if len(anomalies) > 5:
            anomaly_text += f"\n_...and {len(anomalies) - 5} more_"
        
        fields = [
            {"title": "Table", "value": table_name},
            {"title": "Health Score", "value": f"{health_score}/100"},
            {"title": "Anomalies Found", "value": str(len(anomalies))}
        ]
        
        return self.send_alert(
            title=f"Data Quality Alert: {table_name}",
            message=anomaly_text if anomalies else "No anomalies detected ✅",
            severity=severity,
            fields=fields
        )


class EmailNotifier:
    """Send alerts via email"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
    
    def send_alert(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str
    ) -> bool:
        """Send an email alert"""
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = ", ".join(to_emails)
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, to_emails, msg.as_string())
            return True
        except Exception as e:
            print(f"Email notification failed: {e}")
            return False
    
    def send_daily_report(
        self,
        to_emails: List[str],
        tables_summary: List[Dict]
    ) -> bool:
        """Send daily summary report"""
        
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                         color: white; padding: 20px; text-align: center; }
                .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .table th, .table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                .table th { background-color: #f4f4f4; }
                .healthy { color: #4caf50; }
                .warning { color: #ff9800; }
                .critical { color: #f44336; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>💫 DataPulse Daily Report</h1>
                <p>""" + datetime.now().strftime('%Y-%m-%d') + """</p>
            </div>
            <table class="table">
                <tr>
                    <th>Table</th>
                    <th>Health Score</th>
                    <th>Anomalies</th>
                    <th>Status</th>
                </tr>
        """
        
        for table in tables_summary:
            score = table.get('health_score', 0)
            status_class = 'healthy' if score >= 80 else 'warning' if score >= 60 else 'critical'
            status_text = 'Healthy' if score >= 80 else 'Warning' if score >= 60 else 'Critical'
            
            html += f"""
                <tr>
                    <td>{table.get('table_name', 'Unknown')}</td>
                    <td>{score}/100</td>
                    <td>{table.get('anomaly_count', 0)}</td>
                    <td class="{status_class}">{status_text}</td>
                </tr>
            """
        
        html += """
            </table>
            <p style="color: #666; font-size: 12px;">
                Powered by DataPulse - Enterprise Data Quality Monitoring
            </p>
        </body>
        </html>
        """
        
        return self.send_alert(
            to_emails=to_emails,
            subject=f"📊 DataPulse Daily Report - {datetime.now().strftime('%Y-%m-%d')}",
            html_content=html
        )


def generate_alert_html(
    table_name: str,
    health_score: int,
    anomalies: List[Dict],
    include_details: bool = True
) -> str:
    """Generate HTML content for alerts"""
    
    status_color = '#4caf50' if health_score >= 80 else '#ff9800' if health_score >= 60 else '#f44336'
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
            <h2>💫 DataPulse Alert</h2>
        </div>
        <div style="padding: 20px; border: 1px solid #ddd; border-top: none;">
            <h3>Table: {table_name}</h3>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 36px; color: {status_color}; font-weight: bold;">
                    {health_score}
                </span>
                <span style="color: #666;">/100 Health Score</span>
            </div>
    """
    
    if anomalies and include_details:
        html += "<h4>Anomalies Detected:</h4><ul>"
        for a in anomalies[:10]:
            html += f"<li><strong>{a.get('metric', 'Unknown')}</strong>: {a.get('explanation', 'No details')[:100]}</li>"
        html += "</ul>"
    
    html += f"""
            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </div>
    """
    
    return html
