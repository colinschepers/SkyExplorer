from sky_explorer.streamlit.dashboard import Dashboard
from sky_explorer.streamlit.utils import init_page_layout

init_page_layout()

dashboard = Dashboard()
dashboard.run()
