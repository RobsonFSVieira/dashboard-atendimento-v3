import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def detectar_tema():
    """Detecta se o tema atual é claro ou escuro"""
    try:
        theme_param = st.query_params.get('theme', None)
        if theme_param:
            return json.loads(theme_param)['base']
        else:
            return st.config.get_option('theme.base')
    except:
        return 'light'

def obter_cores_tema():
    """Retorna as cores baseadas no tema atual"""
    is_dark = detectar_tema() == 'dark'
    return {
        'primaria': '#1a5fb4' if is_dark else '#1864ab',
        'secundaria': '#4dabf7' if is_dark else '#83c9ff',
        'texto': '#ffffff' if is_dark else '#2c3e50',
        'fundo': '#0e1117' if is_dark else '#ffffff',
        'grid': '#2c3e50' if is_dark else '#e9ecef',
        'sucesso': '#2dd4bf' if is_dark else '#29b09d',
        'erro': '#ff6b6b' if is_dark else '#ff5757'
    }

def calcular_tempos_por_periodo(dados, filtros, periodo, grupo='CLIENTE'):
    """Calcula tempos médios de atendimento por cliente/operação no período"""
    df = dados['base']
    df_medias = dados['medias']
    
    # Aplicar filtros de data
    mask = (
        (df['retirada'].dt.date >= filtros[periodo]['inicio']) &
        (df['retirada'].dt.date <= filtros[periodo]['fim'])
    )
    df_filtrado = df[mask]
    
    # Aplicar filtros adicionais
    if filtros['cliente'] != ['Todos'] and grupo == 'OPERAÇÃO':
        df_filtrado = df_filtrado[df_filtrado['CLIENTE'].isin(filtros['cliente'])]
    
    # Calcula média de atendimento
    tempos = df_filtrado.groupby(grupo)['tpatend'].agg([
        ('media', 'mean'),
        ('contagem', 'count')
    ]).reset_index()
    
    # Converte tempo para minutos
    tempos['media'] = tempos['media'] / 60
    
    return tempos

def criar_grafico_comparativo(dados_p1, dados_p2, dados_medias, grupo='CLIENTE', filtros=None):
    """Cria gráfico comparativo de tempos médios entre períodos"""
    cores_tema = obter_cores_tema()
    
    # Merge dos dados dos dois períodos
    df_comp = pd.merge(
        dados_p1,
        dados_p2,
        on=grupo,
        suffixes=('_p1', '_p2')
    )
    
    # Adiciona as metas individuais ao DataFrame
    if dados_medias is not None and isinstance(dados_medias, pd.DataFrame):
        df_comp = pd.merge(
            df_comp,
            dados_medias[[grupo, 'META']],
            on=grupo,
            how='left'
        )
    
    df_comp['variacao'] = ((df_comp['media_p2'] - df_comp['media_p1']) 
                          / df_comp['media_p1'] * 100)
    
    # Ordena por total decrescente (menores tempos no topo)
    df_comp['total'] = df_comp['media_p1'] + df_comp['media_p2']
    df_comp = df_comp.sort_values('total', ascending=False)
    
    fig = go.Figure()
    
    # Prepara legendas com data formatada
    legenda_p1 = "Período 1"
    legenda_p2 = "Período 2"
    if filtros:
        legenda_p1 = (f"Período 1 ({filtros['periodo1']['inicio'].strftime('%d/%m/%Y')} "
                      f"a {filtros['periodo1']['fim'].strftime('%d/%m/%Y')})")
        legenda_p2 = (f"Período 2 ({filtros['periodo2']['inicio'].strftime('%d/%m/%Y')} "
                      f"a {filtros['periodo2']['fim'].strftime('%d/%m/%Y')})")
    
    # Calcula o tamanho do texto baseado na largura das barras
    max_valor = max(df_comp['media_p1'].max(), df_comp['media_p2'].max())
    
    def calcular_tamanho_fonte(valor):
        min_size, max_size = 12, 20
        tamanho = max_size * (valor / max_valor)
        return max(min_size, min(max_size, tamanho))
    
    # Adiciona barras para período 1
    fig.add_trace(
        go.Bar(
            name=legenda_p1,
            y=df_comp[grupo],
            x=df_comp['media_p1'],
            orientation='h',
            text=df_comp['media_p1'].round(1),
            textposition='inside',
            marker_color=cores_tema['primaria'],
            textfont={
                'size': df_comp['media_p1'].apply(calcular_tamanho_fonte),
                'color': '#ffffff'
            },
            opacity=0.85
        )
    )
    
    # Adiciona barras para período 2
    fig.add_trace(
        go.Bar(
            name=legenda_p2,
            y=df_comp[grupo],
            x=df_comp['media_p2'],
            orientation='h',
            text=df_comp['media_p2'].round(1),
            textposition='inside',
            marker_color=cores_tema['secundaria'],
            textfont={
                'size': df_comp['media_p2'].apply(calcular_tamanho_fonte),
                'color': '#000000'
            },
            opacity=0.85
        )
    )
    
    # Adiciona marcadores de meta individual para cada cliente/operação
    if 'META' in df_comp.columns:
        fig.add_trace(
            go.Scatter(
                name='Meta Individual',
                y=df_comp[grupo],
                x=df_comp['META'],
                mode='markers+text',
                marker=dict(
                    symbol='diamond',
                    size=12,
                    color=cores_tema['erro'],
                    line=dict(width=2, color=cores_tema['erro'])
                ),
                text=df_comp['META'].round(1),
                textposition='middle right',
                textfont=dict(color=cores_tema['erro']),
                hovertemplate='Meta %{y}: %{x:.1f} min<extra></extra>'
            )
        )
    
    # Adiciona anotações de variação
    for i, row in df_comp.iterrows():
        # Inverte a lógica das cores: vermelho para aumento, verde para redução
        cor = cores_tema['sucesso'] if row['variacao'] < 0 else cores_tema['erro']
        fig.add_annotation(
            y=row[grupo],
            x=row['total'],  # Posição após as barras empilhadas
            text=f"{row['variacao']:+.1f}%",
            showarrow=False,
            font=dict(color=cor, size=14),
            xanchor='left',
            yanchor='middle',
            xshift=10
        )
    
    # Atualiza layout
    fig.update_layout(
        title={
            'text': f'Comparativo de Tempo Médio de Atendimento por {grupo}',
            'font': {'size': 16, 'color': cores_tema['texto']}
        },
        barmode='stack',
        bargap=0.15,
        bargroupgap=0.1,
        height=max(600, len(df_comp) * 45),
        font={'size': 12, 'color': cores_tema['texto']},
        showlegend=True,
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1,
            'font': {'color': cores_tema['texto']},
            'traceorder': 'normal',
            'itemsizing': 'constant'
        },
        margin=dict(l=20, r=180, t=80, b=40),  # Aumentado margin right para acomodar as metas
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor=cores_tema['fundo']
    )
    
    # Atualiza eixos
    fig.update_xaxes(
        title='Tempo Médio (minutos)',
        title_font={'color': cores_tema['texto']},
        tickfont={'color': cores_tema['texto']},
        gridcolor=cores_tema['grid'],
        showline=True,
        linewidth=1,
        linecolor=cores_tema['grid'],
        zeroline=False
    )
    
    fig.update_yaxes(
        title=grupo,
        title_font={'color': cores_tema['texto']},
        tickfont={'color': cores_tema['texto']},
        gridcolor=cores_tema['grid'],
        showline=True,
        linewidth=1,
        linecolor=cores_tema['grid'],
        zeroline=False
    )
    
    return fig

def gerar_insights(df_comp, titulo="Insights"):
    """Gera insights sobre os tempos de atendimento"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Visão Geral")
        media_geral_p1 = (df_comp['media_p1'] * df_comp['contagem_p1']).sum() / df_comp['contagem_p1'].sum()
        media_geral_p2 = (df_comp['media_p2'] * df_comp['contagem_p2']).sum() / df_comp['contagem_p2'].sum()
        var_media = ((media_geral_p2 - media_geral_p1) / media_geral_p1 * 100)
        
        st.markdown(f"""
        - Tempo médio período 1: **{media_geral_p1:.1f}** minutos
        - Tempo médio período 2: **{media_geral_p2:.1f}** minutos
        - Variação média: **{var_media:+.1f}%**
        """)
    
    with col2:
        st.subheader("📈 Maiores Variações")
        # Inverte a lógica: melhorias são reduções no tempo
        melhorias = df_comp[df_comp['variacao'] < 0].sort_values('variacao')
        pioras = df_comp[df_comp['variacao'] > 0].sort_values('variacao', ascending=False)
        
        if not melhorias.empty:
            st.markdown("**Maiores Reduções (Melhorias):**")
            for _, row in melhorias.head(3).iterrows():
                # Valores negativos são bons (verde)
                st.markdown(f"- {row['CLIENTE']}: {row['variacao']:.1f}% :green[⬇]")
        
        if not pioras.empty:
            st.markdown("**Maiores Aumentos (Pioras):**")
            for _, row in pioras.head(3).iterrows():
                # Valores positivos são ruins (vermelho)
                st.markdown(f"- {row['CLIENTE']}: +{row['variacao']:.1f}% :red[⬆]")

def mostrar_aba(dados, filtros):
    """Mostra a aba de Tempo de Atendimento"""
    st.header("Tempo de Atendimento")
    
    try:
        # Adiciona um key único que muda quando o tema muda
        st.session_state['tema_atual'] = detectar_tema()
        
        tipo_analise = st.radio(
            "Analisar por:",
            ["Cliente", "Operação"],
            horizontal=True
        )
        
        grupo = "CLIENTE" if tipo_analise == "Cliente" else "OPERAÇÃO"
        
        # Calcula tempos para os dois períodos
        tempos_p1 = calcular_tempos_por_periodo(dados, filtros, 'periodo1', grupo)
        tempos_p2 = calcular_tempos_por_periodo(dados, filtros, 'periodo2', grupo)
        
        if tempos_p1.empty or tempos_p2.empty:
            st.warning("Não há dados para exibir no período selecionado.")
            return
            
        # Verifica se há dados de médias antes de passar para o gráfico
        medias = dados.get('medias')
        if medias is None:
            st.info("Dados de meta não disponíveis. O gráfico será exibido sem a linha de meta.")
            
        # Cria e exibe o gráfico comparativo
        fig = criar_grafico_comparativo(tempos_p1, tempos_p2, medias, grupo, filtros)
        st.plotly_chart(
            fig, 
            use_container_width=True,
            key=f"grafico_tempo_{grupo}_{st.session_state['tema_atual']}"
        )
        
        # Adiciona insights
        st.markdown("---")
        with st.expander("📊 Ver Insights", expanded=True):
            df_comp = pd.merge(
                tempos_p1,
                tempos_p2,
                on=grupo,
                suffixes=('_p1', '_p2')
            )
            df_comp['variacao'] = ((df_comp['media_p2'] - df_comp['media_p1']) 
                                 / df_comp['media_p1'] * 100)
            gerar_insights(df_comp)
    
    except Exception as e:
        st.error("Erro ao gerar a aba de Tempo de Atendimento")
        st.exception(e)