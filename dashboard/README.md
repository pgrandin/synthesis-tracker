# Dashboard Options for Synthesis Tracker

## Quick Start - Streamlit Dashboard

1. Install dependencies:
```bash
cd dashboard
pip install -r requirements.txt
```

2. Run the dashboard:
```bash
streamlit run streamlit_dashboard.py
```

3. Open browser to http://localhost:8501

The dashboard shows:
- Weekly activity trends
- Daily breakdown for most recent week
- Individual session timeline
- Summary metrics
- Recent activity tables

## Alternative Dashboard Options

### 1. **Google Sheets** (Easiest for sharing)
Export to CSV and import:
```python
# Add to synthesis_tracker.py
df = pd.DataFrame(results['progress'])
df.to_csv('weekly_progress.csv')
```

### 2. **Grafana + SQLite** (Professional)
```bash
# Store in SQLite
import sqlite3
conn = sqlite3.connect('synthesis.db')
df.to_sql('activity', conn, if_exists='append')
```

### 3. **Static HTML** (GitHub Pages)
Generate static charts:
```python
import plotly.offline as pyo
fig.write_html('dashboard.html')
# Commit and push to gh-pages branch
```

### 4. **Jupyter Notebook** (Interactive analysis)
```bash
jupyter notebook analysis.ipynb
# Use pandas, matplotlib, seaborn for exploration
```

### 5. **Automated Daily Updates**
Add to cron:
```bash
# Daily at 6pm
0 18 * * * cd /path/to/tracker && python3 synthesis_tracker.py
```

## Data Structure

The `synthesis_data.json` contains:
- `sessions`: Individual session details
- `progress`: Weekly summaries with daily breakdowns
- `summary`: Aggregate statistics

Update data by running:
```bash
python3 ../email_parser/synthesis_tracker.py
```