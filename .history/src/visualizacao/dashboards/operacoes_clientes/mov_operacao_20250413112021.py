import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def formatar_data(data):
    """Formata a data para o padrão dd/mm/aaaa"""
    if isinstance(data, datetime):
        return data.strftime('%d/%m/%Y')
    return data

def calcular_movimentacao_por_periodo(dados, filtros, periodo):
    """Calcula a movimentação de cada operação no período especificado"""
    df = dados['base']
    
    # Aplicar filtros de data
    mask = (
        (df['retirada'].dt.date >= filtros[periodo]['inicio']) &
        (df['retirada'].dt.date <= filtros[periodo]['fim'])
    )
    df_filtrado = df[mask]
    
    # Aplicar filtros adicionais se especificados
    if filtros['cliente'] != ['Todos']:
        df_filtrado = df_filtrado[df_filtrado['CLIENTE'].isin(filtros['cliente'])]
    
    # Agrupar por operação
    movimentacao = df_filtrado.groupby('OPERAÇÃO')['id'].count().reset_index()
    movimentacao.columns = ['operacao', 'quantidade']
    
    return movimentacao

def criar_grafico_comparativo(dados_p1, dados_p2, filtros):
    try:
        # Merge e prepara dados
        df_comp = pd.merge(
            dados_p1, 
            dados_p2, 
            on='operacao', 
            suffixes=('_p1', '_p2')
        )
        
        # Calcula total e variação percentual
        df_comp['total'] = df_comp['quantidade_p1'] + df_comp['quantidade_p2']
        df_comp['variacao'] = ((df_comp['quantidade_p2'] - df_comp['quantidade_p1']) / 
                              df_comp['quantidade_p1'] * 100)
        
        # Ordena por total decrescente
        df_comp = df_comp.sort_values('total', ascending=False)
        
        # Prepara legendas
        legenda_p1 = f"Período 1 ({formatar_data(filtros['periodo1']['inicio'])} a {formatar_data(filtros['periodo1']['fim'])})"
        legenda_p2 = f"Período 2 ({formatar_data(filtros['periodo2']['inicio'])} a {formatar_data(filtros['periodo2']['fim'])})"
        
        # Cria figura base
        fig = go.Figure()
        
        # Adiciona barras para período 1
        fig.add_trace(go.Bar(
            name=legenda_p1,
            y=df_comp['operacao'],
            x=df_comp['quantidade_p1'],
            orientation='h',
            text=df_comp['quantidade_p1'],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=12),
            width=0.8
        ))
        
        # Adiciona barras para período 2
        fig.add_trace(go.Bar(
            name=legenda_p2,
            y=df_comp['operacao'],
            x=df_comp['quantidade_p2'],
            orientation='h',
            text=df_comp['quantidade_p2'],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=12),
            width=0.8
        ))
        
        # Adiciona anotações de variação percentual
        for i, row in df_comp.iterrows():
            cor = 'green' if row['variacao'] >= 0 else 'red'
            x_pos = max(row['quantidade_p1'], row['quantidade_p2']) + 1
            
            fig.add_annotation(
                y=row['operacao'],
                x=x_pos,
                text=f"{row['variacao']:+.1f}%",
                showarrow=False,
                font=dict(color=cor, size=12),
                xanchor='left',
                yanchor='middle'
            )
        
        # Calcula a margem direita adequada
        max_value = df_comp[['quantidade_p1', 'quantidade_p2']].max().max()
        right_margin = int(max_value * 0.3)  # 30% do maior valor
        
        # Atualiza layout
        fig.update_layout(
            title={
                'text': 'Comparativo de Movimentação por Operação',
                'font': {'size': 16}
            },
            barmode='group',
            bargap=0.15,
            bargroupgap=0.1,
            height=max(400, len(df_comp) * 40),  # Ajuste dinâmico da altura
            font_size=12,
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            margin=dict(l=20, r=right_margin, t=60, b=20),
            yaxis=dict(
                tickfont=dict(size=12),
                automargin=True
            ),
            xaxis=dict(
                tickfont=dict(size=12),
                automargin=True
            )
        )
        
        return fig
    except Exception as e:
        st.error(f"Erro ao criar gráfico: {str(e)}")
        return None

def mostrar_aba(dados, filtros):
    """Mostra a aba de Movimentação por Operação"""
    st.header("Movimentação por Operação")
    
    try:
        # Calcula movimentação para os dois períodos
        mov_p1 = calcular_movimentacao_por_periodo(dados, filtros, 'periodo1')
        mov_p2 = calcular_movimentacao_por_periodo(dados, filtros, 'periodo2')
        
        # Cria e exibe o gráfico comparativo
        fig = criar_grafico_comparativo(mov_p1, mov_p2, filtros)
        st.plotly_chart(fig, use_container_width=True)
        
        # Insights
        st.subheader("📊 Insights")
        with st.expander("Ver insights"):
            # Calcula variações significativas
            df_comp = pd.merge(
                mov_p1, 
                mov_p2, 
                on='operacao', 
                suffixes=('_p1', '_p2')
            )
            df_comp['variacao'] = ((df_comp['quantidade_p2'] - df_comp['quantidade_p1']) 
                                 / df_comp['quantidade_p1'] * 100)
            
            # Maiores aumentos e reduções
            aumentos = df_comp[df_comp['variacao'] > 0].sort_values('variacao', ascending=False)
            reducoes = df_comp[df_comp['variacao'] < 0].sort_values('variacao')
            
            # Total de atendimentos
            total_p1 = mov_p1['quantidade'].sum()
            total_p2 = mov_p2['quantidade'].sum()
            var_total = ((total_p2 - total_p1) / total_p1 * 100)
            
            st.write("#### Principais Observações:")
            st.write(f"**Variação Total**: {var_total:+.1f}%")
            
            if not aumentos.empty:
                st.write("**Operações com Maior Crescimento:**")
                for _, row in aumentos.head(3).iterrows():
                    st.write(f"- {row['operacao']}: +{row['variacao']:.1f}%")
            
            if not reducoes.empty:
                st.write("**Operações com Maior Redução:**")
                for _, row in reducoes.head(3).iterrows():
                    st.write(f"- {row['operacao']}: {row['variacao']:.1f}%")
    
    except Exception as e:
        st.error("Erro ao gerar a aba de Movimentação por Operação")
        st.exception(e)