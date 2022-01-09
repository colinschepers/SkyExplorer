from collections import Callable

import streamlit as st


class MultiPageApp:
    def __init__(self) -> None:
        self.pages = {}

    def add_page(self, title: str, func: Callable) -> None:
        self.pages[title] = func

    def run(self):
        title = st.sidebar.selectbox('Navigation', self.pages.keys(), key="navigation")
        self.pages[title]()
