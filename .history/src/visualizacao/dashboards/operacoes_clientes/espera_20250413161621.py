import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# ...existing code for detectar_tema() and obter_cores_tema()...

def formatar_tempo(minutos):
    """Formata o tempo em minutos para o formato mm:ss"""
    minutos_int = int(minutos)
    segundos = int((minutos - minutos_int) * 60)
    return f"{minutos_int:02d}:{segundos:02d}"

# ...existing code for converter_para_minutos() and determinar_turno()...

def calcular_tempos_por_periodo(dados, filtros, periodo, grupo='CLIENTE'):
    """Calcula tempos médios de espera por cliente/operação no período"""
    df = dados['base']
    df_medias = dados['medias']
    
    # Debug info
    st.write(f"Total registros antes dos filtros: {len(df)}")
    
    # Aplicar filtros de data
    mask = (
        (df['retirada'].dt.date >= filtros[periodo]['inicio']) &
        (df['retirada'].dt.date <= filtros[periodo]['fim'])
    )
    df_filtrado = df[mask].copy()
    st.write(f"Registros após filtro de data: {len(df_filtrado)}")
    
    # Determina o turno com base no horário de retirada
    df_filtrado['TURNO'] = df_filtrado['retirada'].apply(determinar_turno)
    
    # Aplicar filtros
    if filtros['cliente'] != ['Todos']:
        df_filtrado = df_filtrado[df_filtrado['CLIENTE'].isin(filtros['cliente'])]
        st.write(f"Registros após filtro de cliente: {len(df_filtrado)}")
    
    if filtros['operacao'] != ['Todas']:
        df_filtrado = df_filtrado[df_filtrado['OPERAÇÃO'].isin(filtros['operacao'])]
        st.write(f"Registros após filtro de operação: {len(df_filtrado)}")
    
    if filtros['turno'] != ['Todos']:
        df_filtrado = df_filtrado[df_filtrado['TURNO'].isin(filtros['turno'])]
        st.write(f"Registros após filtro de turno: {len(df_filtrado)}")
    
    if len(df_filtrado) == 0:
        st.warning(f"Nenhum dado encontrado para o período {periodo} com os filtros selecionados.")
        return pd.DataFrame()
    
    # Calcula média de espera usando 'tpespera' ao invés de 'tpatend'
    tempos = df_filtrado.groupby(grupo)['tpespera'].agg([
        ('media', 'mean'),
        ('contagem', 'count')
    ]).reset_index()
    
    # Converte tempo para minutos
    tempos['media'] = tempos['media'] / 60
    
    return tempos

def criar_grafico_comparativo(dados_p1, dados_p2, dados_medias, grupo='CLIENTE', filtros=None):
    """Cria gráfico comparativo de tempos médios de espera entre períodos"""
    cores_tema = obter_cores_tema()
    
    # ...existing code for data preparation...
    
    fig = go.Figure()
    
    # Prepara legendas com data formatada
    legenda_p1 = "Período 1"
    legenda_p2 = "Período 2"
    if filtros:
        legenda_p1 = (f"Período 1 ({filtros['periodo1']['inicio'].strftime('%d/%m/%Y')} "
                      f"a {filtros['periodo1']['fim'].strftime('%d/%m/%Y')})")
        legenda_p2 = (f"Período 2 ({filtros['periodo2']['inicio'].strftime('%d/%m/%Y')} "
                      f"a {filtros['periodo2']['fim'].strftime('%d/%m/%Y')})")
    
    # ...existing code for plotting...
    
    # Atualiza layout
    fig.update_layout(
        title={
            'text': f'Comparativo de Tempo Médio de Espera por {grupo}',
            'font': {'size': 16, 'color': cores_tema['texto']}
        },
        # ...rest of existing layout code...
    )
    
    return fig

def gerar_insights(df_comp, grupo='CLIENTE', titulo="Insights", dados_medias=None):
    """Gera insights sobre os tempos de espera"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Visão Geral")
        media_geral_p1 = (df_comp['media_p1'] * df_comp['contagem_p1']).sum() / df_comp['contagem_p1'].sum()
        media_geral_p2 = (df_comp['media_p2'] * df_comp['contagem_p2']).sum() / df_comp['contagem_p2'].sum()
        var_media = ((media_geral_p2 - media_geral_p1) / media_geral_p1 * 100)
        
        st.markdown(f"""
        - Tempo médio de espera período 1: **{formatar_tempo(media_geral_p1)} min**
        - Tempo médio de espera período 2: **{formatar_tempo(media_geral_p2)} min**
        - Variação média: **{var_media:+.1f}%**
        """)
        
        # ...rest of existing insights code...

def mostrar_aba(dados, filtros):
    """Mostra a aba de Tempo de Espera"""
    st.header("Tempo de Espera em Fila")
    
    try:
        # ...rest of existing code with updated titles and descriptions...
    
    except Exception as e:
        st.error("Erro ao gerar a aba de Tempo de Espera")
        st.exception(e)
