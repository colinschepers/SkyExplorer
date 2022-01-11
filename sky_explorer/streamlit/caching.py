import streamlit as st


@st.cache(allow_output_mutation=True, show_spinner=False)
def _get_global_cache() -> dict:
    return {}


GLOBAL_CACHE = _get_global_cache()
