import streamlit as st
import dash_bootstrap_components as dbc
from visualizacao.dashboards.desenvolvimento_pessoas.ranking import create_ranking_layout

# Inicialize o app com o tema Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Crie o layout
app.layout = create_ranking_layout(app)

if __name__ == '__main__':
    app.run_server(debug=True)
