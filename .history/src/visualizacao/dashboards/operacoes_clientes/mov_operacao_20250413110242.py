import streamlit as st
import pandas as pd
import plotly.express as px
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
    """Cria gráfico comparativo entre os dois períodos"""
    try:
        # Merge dos dados dos dois períodos
        df_comp = pd.merge(
            dados_p1, 
            dados_p2, 
            on='operacao', 
            suffixes=('_p1', '_p2')
        )
        
        # Prepara dados para o gráfico
        df_plot = pd.melt(
            df_comp,
            id_vars=['operacao'],
            value_vars=['quantidade_p1', 'quantidade_p2'],
            var_name='periodo',
            value_name='quantidade'
        )
        
        # Ajusta os nomes dos períodos para incluir as datas
        df_plot['periodo'] = df_plot['periodo'].map({
            'quantidade_p1': f"Período 1 ({formatar_data(filtros['periodo1']['inicio'])} a {formatar_data(filtros['periodo1']['fim'])})",
            'quantidade_p2': f"Período 2 ({formatar_data(filtros['periodo2']['inicio'])} a {formatar_data(filtros['periodo2']['fim'])})"
        })
        
        # Cria o gráfico usando plotly express
        fig = px.bar(
            df_plot,
            x='quantidade',
            y='operacao',
            color='periodo',
            title='Comparativo de Movimentação por Operação',
            orientation='h',
            barmode='group',
            height=400 + (len(df_comp) * 30)
        )
        
        # Atualiza layout
        fig.update_layout(
            font_size=12,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
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