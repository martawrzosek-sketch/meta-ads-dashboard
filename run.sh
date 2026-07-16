#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "📦 Installing dependencies..."
pip3 install -q -r requirements.txt

echo "🚀 Starting Meta Ads Dashboard on http://localhost:8501"
python3 -m streamlit run app.py --server.port=8501 --browser.gatherUsageStats=false
