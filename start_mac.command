#!/bin/bash
cd "$(dirname "$0")"
echo "Installing what Wapas needs. This is slow only the first time..."
python3 -m pip install -r requirements.txt
echo "Starting Wapas. If it asks for your email, just press Enter."
python3 -m streamlit run app.py
