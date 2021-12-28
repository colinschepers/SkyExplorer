import streamlit as st
from PIL import Image

from sky_explorer.streamlit.dashboard import Dashboard

st.set_page_config(
    page_title="Sky Explorer",
    page_icon=Image.open("favicon.ico"),
    layout="wide"
)
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding: 1rem;}
    </style>
    """,
    unsafe_allow_html=True
)

dashboard = Dashboard()
dashboard.run()
