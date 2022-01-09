from sky_explorer.streamlit.overview_dashboard import OverviewDashboard
from sky_explorer.streamlit.multipage import MultiPageApp
from sky_explorer.streamlit.statistics_dashboard import StatisticsDashboard
from sky_explorer.streamlit.utils import init_page_layout

init_page_layout()

app = MultiPageApp()
app.add_page("Overview", OverviewDashboard())
app.add_page("Statistics", StatisticsDashboard())
app.run()
