# � DataPulse

**Team: Ctrl Alt Defeat!**  
**Event: Data Platform Ops Hackathon 2026**

A visual, AI-native anomaly detection tool that replaces expensive external tools like Datafold.

![Demo](docs/demo.png)

---

## ✨ Features

- **📈 Row Count Monitoring** - Detect unexpected drops or spikes in data volume
- **📉 Null Rate Tracking** - Identify data quality issues across columns
- **🎯 Smart Detection** - Uses Z-score statistical analysis (no manual thresholds needed)
- **💡 Auto Explanations** - Rule-based explanations for each anomaly
- **📊 Beautiful Visuals** - Interactive Plotly charts
- **💰 Free to Run** - No paid APIs required

---

## 🚀 Quick Start

### Option 1: One-Click Run (Recommended)

**Windows (PowerShell):**
```powershell
.\run.ps1
```

**Windows (CMD):**
```cmd
run.bat
```

This script automatically:
- ✅ Detects existing venv (skips setup if found)
- ✅ Creates venv if missing
- ✅ Installs dependencies from locked versions
- ✅ Launches the app

### Option 2: Manual Setup

#### Prerequisites
- Python 3.9+
- (Optional) GCP account with BigQuery access

#### Installation

```bash
# Navigate to project folder
cd anomaly-detector

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies (use lock file for exact versions)
pip install -r requirements-lock.txt
```

### Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 🎮 Using the App

### Demo Mode (Default)
The app comes with mock data pre-loaded. Just run it and explore!

### Connect to BigQuery (Production)

1. Copy `.env.example` to `.env`
2. Fill in your GCP project details:
   ```
   GCP_PROJECT_ID=your-project-id
   BQ_DATASET=your_dataset
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
   ```
3. Uncheck "Use Demo Data" in the sidebar

---

## 📁 Project Structure

```
anomaly-detector/
├── app.py                  # Main Streamlit application
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
│
├── data/
│   └── mock_data.py       # Mock data generators for demo
│
├── queries/
│   └── bigquery_client.py # BigQuery connection & queries
│
└── utils/
    └── anomaly_detector.py # Anomaly detection algorithms
```

---

## 🧠 How It Works

### Anomaly Detection Algorithm

We use **Z-score analysis** to detect anomalies:

1. Calculate mean and standard deviation of historical data
2. Flag values that deviate more than 2.5 standard deviations
3. Generate explanations based on anomaly type and severity

```python
Z-score = (value - mean) / std_deviation

If |Z-score| > 2.5 → ANOMALY
```

### Why Not Machine Learning?

- **Simpler** - No training required
- **Faster** - Works immediately on any table
- **Transparent** - Easy to explain to stakeholders
- **Free** - No ML infrastructure costs

---

## 🎯 Roadmap

### MVP (Hackathon)
- [x] Row count anomaly detection
- [x] Null rate monitoring
- [x] Interactive charts
- [x] Rule-based explanations
- [x] Mock data for demo

### Future Enhancements
- [ ] Slack/Email alerts
- [ ] Multiple table comparison
- [ ] BigQuery integration
- [ ] Gemini AI explanations
- [ ] Historical anomaly tracking
- [ ] Custom alert rules

---

## 👥 Team Ctrl Alt Defeat!

| Name | Role |
|------|------|
| TBD | Anomaly Detection |
| TBD | UI/Frontend |
| TBD | BigQuery Integration |

---

## 📄 License

Internal use only - Data Platform Ops Hackathon 2026

---

## 🙏 Acknowledgments

- Sayali & Mahdi for organizing the hackathon
- The Data Platform Ops team for the inspiration
- Streamlit for making data apps easy
