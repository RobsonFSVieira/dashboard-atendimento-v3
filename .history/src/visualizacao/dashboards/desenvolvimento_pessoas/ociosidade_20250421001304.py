import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta

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

def formatar_tempo(segundos):
    """Formata o tempo em segundos para o formato HH:MM:SS"""
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    return f"{horas:02d}:{minutos:02d}:{segs:02d} min"

def calcular_ociosidade_por_periodo(dados, filtros, periodo):
    """Calcula o tempo de ociosidade por colaborador no período especificado"""
    df = dados['base'].copy()
    
    if df.empty:
        st.warning("Base de dados está vazia")
        return pd.DataFrame()
    
    # Aplicar filtros de data
    mask = (
        (df['retirada'].dt.date >= filtros[periodo]['inicio']) &
        (df['retirada'].dt.date <= filtros[periodo]['fim'])
    )
    
    # Adicionar filtro de data específica se existir
    if filtros.get('data_especifica'):
        mask &= (df['retirada'].dt.date == filtros['data_especifica'])
    
    df_filtrado = df[mask]
    
    # Aplicar filtro de colaborador específico
    if filtros.get('colaborador') and filtros['colaborador'] != "Todos":
        df_filtrado = df_filtrado[df_filtrado['usuário'] == filtros['colaborador']]
    
    # Aplicar filtros adicionais
    if filtros['cliente'] != ['Todos']:
        df_filtrado = df_filtrado[df_filtrado['CLIENTE'].isin(filtros['cliente'])]
        
    if filtros['operacao'] != ['Todas']:
        df_filtrado = df_filtrado[df_filtrado['OPERAÇÃO'].isin(filtros['operacao'])]
        
    if filtros['turno'] != ['Todos']:
        def get_turno(hour):
            if 7 <= hour < 15:
                return 'TURNO A'
            elif 15 <= hour < 23:
                return 'TURNO B'
            else:
                return 'TURNO C'
        df_filtrado = df_filtrado[df_filtrado['retirada'].dt.hour.apply(get_turno).isin(filtros['turno'])]
    
    # Calcular ociosidade por colaborador
    ociosidade = []
    for usuario in df_filtrado['usuário'].unique():
        # Agrupar por dia
        for data in df_filtrado[df_filtrado['usuário'] == usuario]['retirada'].dt.date.unique():
            atend_dia = df_filtrado[
                (df_filtrado['usuário'] == usuario) & 
                (df_filtrado['retirada'].dt.date == data)
            ].copy()
            
            if len(atend_dia) > 0:
                # Ordenar por horário
                atend_dia = atend_dia.sort_values('inicio')
                
                # Calcular intervalos entre atendimentos
                intervalos = []
                
                # Intervalo entre atendimentos
                for i in range(len(atend_dia)-1):
                    fim_atual = atend_dia['fim'].iloc[i]
                    inicio_prox = atend_dia['inicio'].iloc[i+1]
                    intervalo = (inicio_prox - fim_atual).total_seconds()
                    # Considerar apenas intervalos menores que 2 horas (7200 segundos)
                    if 0 < intervalo <= 7200:
                        intervalos.append(intervalo)
                
                if intervalos:
                    # Remover o maior intervalo (presumivelmente almoço)
                    if len(intervalos) > 1:
                        intervalos.remove(max(intervalos))
                    
                    tempo_ocioso = sum(intervalos)
                    ociosidade.append({
                        'colaborador': usuario,
                        'data': data,
                        'tempo_ocioso': tempo_ocioso,
                        'qtd_intervalos': len(intervalos)
                    })
    
    # Criar DataFrame com média por colaborador
    if ociosidade:
        df_ociosidade = pd.DataFrame(ociosidade)
        df_ociosidade = df_ociosidade.groupby('colaborador')['tempo_ocioso'].mean().reset_index()
        return df_ociosidade
    
    return pd.DataFrame()

def criar_grafico_comparativo(dados_p1, dados_p2, filtros):
    """Cria gráfico comparativo de ociosidade entre períodos"""
    try:
        # Merge dos dados
        df_comp = pd.merge(
            dados_p1, 
            dados_p2, 
            on='colaborador',
            suffixes=('_p1', '_p2'),
            how='outer'
        ).fillna(0)
        
        # Ordena por tempo de ociosidade do período 2 (crescente - menores tempos no topo)
        df_comp = df_comp.sort_values('tempo_ocioso_p2', ascending=False)
        
        # Calcula variação percentual
        df_comp['variacao'] = ((df_comp['tempo_ocioso_p2'] - df_comp['tempo_ocioso_p1']) / 
                              df_comp['tempo_ocioso_p1'] * 100).replace([float('inf')], 100)
        
        cores_tema = obter_cores_tema()
        
        # Prepara legendas
        legenda_p1 = (f"Período 1 ({filtros['periodo1']['inicio'].strftime('%d/%m/%Y')} "
                      f"a {filtros['periodo1']['fim'].strftime('%d/%m/%Y')})")
        legenda_p2 = (f"Período 2 ({filtros['periodo2']['inicio'].strftime('%d/%m/%Y')} "
                      f"a {filtros['periodo2']['fim'].strftime('%d/%m/%Y')})")
        
        # Cria o gráfico
        fig = go.Figure()
        
        # Adiciona barras para período 1
        fig.add_trace(go.Bar(
            name=legenda_p1,
            y=df_comp['colaborador'],
            x=df_comp['tempo_ocioso_p1'],
            orientation='h',
            text=[formatar_tempo(t) for t in df_comp['tempo_ocioso_p1']],
            textposition='inside',
            marker_color=cores_tema['primaria'],
            textfont={'color': '#ffffff', 'size': 16},
            opacity=0.85
        ))
        
        # Adiciona barras para período 2
        fig.add_trace(go.Bar(
            name=legenda_p2,
            y=df_comp['colaborador'],
            x=df_comp['tempo_ocioso_p2'],
            orientation='h',
            text=[formatar_tempo(t) for t in df_comp['tempo_ocioso_p2']],
            textposition='inside',
            marker_color=cores_tema['secundaria'],
            textfont={'color': '#000000', 'size': 16},
            opacity=0.85
        ))
        
        # Ajusta layout
        fig.update_layout(
            title={
                'text': 'Comparativo de Tempo de Ociosidade por Colaborador (Excluindo Horário de Almoço)',
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
                'traceorder': 'normal'  # Mudado para 'normal' para manter ordem original das legendas
            },
            margin=dict(l=20, r=160, t=80, b=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor=cores_tema['fundo']
        )
        
        return fig
    except Exception as e:
        st.error(f"Erro ao criar gráfico: {str(e)}")
        return None

def gerar_insights_ociosidade(ocio_p1, ocio_p2):
    """Gera insights sobre a ociosidade dos colaboradores"""
    try:
        # Merge dos dados
        df_insights = pd.merge(
            ocio_p1, 
            ocio_p2, 
            on='colaborador',
            suffixes=('_p1', '_p2'),
            how='outer'
        ).fillna(0)
        
        # Calcular variação percentual
        df_insights['variacao'] = ((df_insights['tempo_ocioso_p2'] - df_insights['tempo_ocioso_p1']) / 
                                  df_insights['tempo_ocioso_p1'] * 100).replace([float('inf')], 100)
        
        # Criar 4 colunas principais
        col_perf1, col_perf2, col_perf3, col_insights = st.columns([0.25, 0.25, 0.25, 0.25])
        
        # Dividir colaboradores em 3 partes
        tamanho_parte = len(df_insights) // 3
        resto = len(df_insights) % 3
        indices = [
            (0, tamanho_parte + (1 if resto > 0 else 0)),
            (tamanho_parte + (1 if resto > 0 else 0), 2*tamanho_parte + (2 if resto > 1 else 1 if resto > 0 else 0)),
            (2*tamanho_parte + (2 if resto > 1 else 1 if resto > 0 else 0), len(df_insights))
        ]

        # Primeira coluna de performance
        with col_perf1:
            st.write("#### Performance (1/3)")
            df_parte = df_insights.iloc[indices[0][0]:indices[0][1]]
            for _, row in df_parte.iterrows():
                status = "✅" if row['tempo_ocioso_p2'] <= row['tempo_ocioso_p1'] else "⚠️"
                st.write(
                    f"**{row['colaborador']}** {status}\n\n"
                    f"- P1: {formatar_tempo(row['tempo_ocioso_p1'])}\n"
                    f"- P2: {formatar_tempo(row['tempo_ocioso_p2'])}\n"
                    f"- Variação: {row['variacao']:+.1f}%"
                )

        # Segunda coluna de performance
        with col_perf2:
            st.write("#### Performance (2/3)")
            df_parte = df_insights.iloc[indices[1][0]:indices[1][1]]
            for _, row in df_parte.iterrows():
                status = "✅" if row['tempo_ocioso_p2'] <= row['tempo_ocioso_p1'] else "⚠️"
                st.write(
                    f"**{row['colaborador']}** {status}\n\n"
                    f"- P1: {formatar_tempo(row['tempo_ocioso_p1'])}\n"
                    f"- P2: {formatar_tempo(row['tempo_ocioso_p2'])}\n"
                    f"- Variação: {row['variacao']:+.1f}%"
                )

        # Terceira coluna de performance
        with col_perf3:
            st.write("#### Performance (3/3)")
            df_parte = df_insights.iloc[indices[2][0]:indices[2][1]]
            for _, row in df_parte.iterrows():
                status = "✅" if row['tempo_ocioso_p2'] <= row['tempo_ocioso_p1'] else "⚠️"
                st.write(
                    f"**{row['colaborador']}** {status}\n\n"
                    f"- P1: {formatar_tempo(row['tempo_ocioso_p1'])}\n"
                    f"- P2: {formatar_tempo(row['tempo_ocioso_p2'])}\n"
                    f"- Variação: {row['variacao']:+.1f}%"
                )

        # Coluna de insights
        with col_insights:
            st.write("#### 📈 Insights")
            
            # Melhor performance (menor ociosidade)
            melhor = df_insights.loc[df_insights['tempo_ocioso_p2'].idxmin()]
            st.markdown(
                f"<div class='success-box'>"
                f"<b>🎯 Menor Ociosidade</b><br>"
                f"{melhor['colaborador']}<br>"
                f"Tempo: {formatar_tempo(melhor['tempo_ocioso_p2'])}"
                f"</div>",
                unsafe_allow_html=True
            )
            
            # Maior ociosidade
            pior = df_insights.loc[df_insights['tempo_ocioso_p2'].idxmax()]
            st.markdown(
                f"<div class='warning-box'>"
                f"<b>⚠️ Maior Ociosidade</b><br>"
                f"{pior['colaborador']}<br>"
                f"Tempo: {formatar_tempo(pior['tempo_ocioso_p2'])}"
                f"</div>",
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Erro ao gerar insights: {str(e)}")

def mostrar_aba(dados, filtros):
    """Mostra a aba de Análise de Ociosidade"""
    st.header("Análise de Ociosidade")
    rador = st.selectbox(
    try:        "Selecione o Colaborador",
        st.session_state['tema_atual'] = detectar_tema()
         key='ociosidade_colaborador'
        ocio_p1 = calcular_ociosidade_por_periodo(dados, filtros, 'periodo1')
        ocio_p2 = calcular_ociosidade_por_periodo(dados, filtros, 'periodo2')
        
        if ocio_p1.empty or ocio_p2.empty:
            st.warning("Não há dados suficientes para análise de ociosidade no período selecionado.")urno = st.selectbox(
            return        "Selecione o Turno",
        rnos,
        fig = criar_grafico_comparativo(ocio_p1, ocio_p2, filtros)
        if fig:
            st.plotly_chart(
                fig,    with col3:
                use_container_width=True,odos"] + sorted(dados['base']['CLIENTE'].unique().tolist())
                key=f"grafico_ociosidade_{st.session_state['tema_atual']}"
            )one o Cliente",
                        options=clientes,









        st.exception(e)        st.error(f"Erro ao mostrar aba: {str(e)}")    except Exception as e:                gerar_insights_ociosidade(ocio_p1, ocio_p2)        with st.expander("Ver análise detalhada", expanded=True):        st.subheader("📈 Análise Detalhada")        st.markdown("---")                key='ociosidade_cliente'
            )

        with col4:
            datas_disponiveis = sorted(dados['base']['retirada'].dt.date.unique())
            datas_opcoes = ["Todas"] + [data.strftime("%d/%m/%Y") for data in datas_disponiveis]
            data_selecionada = st.selectbox(
                "Selecione a Data",
                options=datas_opcoes,
                key='ociosidade_data'
            )

        # Atualizar filtros mantendo a estrutura original
        filtros_atualizados = filtros.copy()
        filtros_atualizados['colaborador'] = colaborador
        filtros_atualizados['turno'] = [turno] if turno != "Todos" else ["Todos"]
        filtros_atualizados['cliente'] = [cliente] if cliente != "Todos" else ["Todos"]
        
        if data_selecionada != "Todas":
            dia, mes, ano = map(int, data_selecionada.split('/'))
            filtros_atualizados['data_especifica'] = pd.to_datetime(f"{ano}-{mes}-{dia}").date()
        else:
            filtros_atualizados['data_especifica'] = None
        
        # Calcular ociosidade com os filtros atualizados
        ocio_p1 = calcular_ociosidade_por_periodo(dados, filtros_atualizados, 'periodo1')
        ocio_p2 = calcular_ociosidade_por_periodo(dados, filtros_atualizados, 'periodo2')
        
        if ocio_p1.empty or ocio_p2.empty:
            st.warning("Não há dados suficientes para análise de ociosidade no período selecionado.")
            return
        
        fig = criar_grafico_comparativo(ocio_p1, ocio_p2, filtros_atualizados)
        if fig:
            st.plotly_chart(
                fig,
                use_container_width=True,
                key=f"grafico_ociosidade_{st.session_state['tema_atual']}"
            )
        
        st.markdown("---")
        st.subheader("📈 Análise Detalhada")
        with st.expander("Ver análise detalhada", expanded=True):
            gerar_insights_ociosidade(ocio_p1, ocio_p2)
    
    except Exception as e:
        st.error(f"Erro ao mostrar aba: {str(e)}")
        st.exception(e)
