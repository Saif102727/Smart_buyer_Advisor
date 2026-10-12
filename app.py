import sys
from pathlib import Path

# يضمن أن مجلدات core/ و ui/ تُوجد على مسار الاستيراد مهما كان مكان التشغيل
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(page_title="مستشار الشراء الذكي", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")

from ui.app import SmartBuyerApp, get_container  # noqa: E402  (بعد set_page_config)

SmartBuyerApp(get_container()).run()
