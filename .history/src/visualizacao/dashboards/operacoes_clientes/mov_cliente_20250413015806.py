import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def calcular_movimentacao_por_periodo(dados, filtros, periodo):
    """Calcula a movimentação de cada cliente no período especificado"""
    df = dados['base']
    
    # Aplicar filtros de data
    mask = (
        (df['retirada'].dt.date >= filtros[periodo]['inicio']) &
        (df['retirada'].dt.date <= filtros[periodo]['fim'])
    )
    df_filtrado = df[mask]
    
    # Agrupar por cliente
    movimentacao = df_filtrado.groupby('CLIENTE')['id'].count().reset_index()
    movimentacao.columns = ['cliente', 'quantidade']
    
    return movimentacao

def criar_grafico_comparativo(dados_p1, dados_p2):
    """Cria gráfico comparativo entre os dois períodos"""
    # Merge dos dados dos dois períodos
    df_comp = pd.merge(
        dados_p1, 
        dados_p2, 
        on='cliente', 
        suffixes=('_p1', '_p2')
    )
    
    # Calcula variação percentual
    df_comp['variacao'] = ((df_comp['quantidade_p2'] - df_comp['quantidade_p1']) 
                          / df_comp['quantidade_p1'] * 100)
    
    # Ordena por quantidade do período 2
    df_comp = df_comp.sort_values('quantidade_p2', ascending=True)
    
    # Cria o gráfico
    fig = go.Figure()
    
    # Adiciona barras para cada período
    fig.add_trace(
        go.Bar(
            name='Período 1',
            y=df_comp['cliente'],
            x=df_comp['quantidade_p1'],
            orientation='h',
            marker_color='lightgray'
        )
    )
    
    fig.add_trace(
        go.Bar(
            name='Período 2',
            y=df_comp['cliente'],
            x=df_comp['quantidade_p2'],
            orientation='h',
            marker_color='darkblue'
        )
    )
    
    # Adiciona anotações com a variação percentual
    for i, row in df_comp.iterrows():
        fig.add_annotation(
            x=max(row['quantidade_p1'], row['quantidade_p2']),
            y=row['cliente'],
            text=f"{row['variacao']:+.1f}%",
            showarrow=False,
            xshift=10,
            font=dict(
                color='green' if row['variacao'] >= 0 else 'red'
            )
        )
    
    # Atualiza o layout
    fig.update_layout(
        title='Comparativo de Movimentação por Cliente',
        barmode='group',
        height=400 + (len(df_comp) * 20),
        showlegend=True,
        xaxis_title="Quantidade de Atendimentos",
        yaxis_title="Cliente"
    )
    
    return fig

def mostrar_aba(dados, filtros):
    """Mostra a aba de Movimentação por Cliente"""
    st.header("Movimentação por Cliente")
    
    try:
        # Calcula movimentação para os dois períodos
        mov_p1 = calcular_movimentacao_por_periodo(dados, filtros, 'periodo1')
        mov_p2 = calcular_movimentacao_por_periodo(dados, filtros, 'periodo2')
        
        # Cria e exibe o gráfico comparativo
        fig = criar_grafico_comparativo(mov_p1, mov_p2)
        st.plotly_chart(fig, use_container_width=True)
        
        # Insights
        st.subheader("📊 Insights")
        with st.expander("Ver insights"):
            # Calcula variações significativas
            df_comp = pd.merge(
                mov_p1, 
                mov_p2, 
                on='cliente', 
                suffixes=('_p1', '_p2')
            )
            df_comp['variacao'] = ((df_comp['quantidade_p2'] - df_comp['quantidade_p1']) 
                                 / df_comp['quantidade_p1'] * 100)
            
            # Maiores aumentos e reduções
            aumentos = df_comp[df_comp['variacao'] > 0].sort_values('variacao', ascending=False)
            reducoes = df_comp[df_comp['variacao'] < 0].sort_values('variacao')
            
            st.write("#### Principais Observações:")
            
            if not aumentos.empty:
                st.write("**Maiores Aumentos:**")
                for _, row in aumentos.head(3).iterrows():
                    st.write(f"- {row['cliente']}: +{row['variacao']:.1f}%")
            
            if not reducoes.empty:
                st.write("**Maiores Reduções:**")
                for _, row in reducoes.head(3).iterrows():
                    st.write(f"- {row['cliente']}: {row['variacao']:.1f}%")
    
    except Exception as e:
        st.error("Erro ao gerar a aba de Movimentação por Cliente")
        st.exception(e)