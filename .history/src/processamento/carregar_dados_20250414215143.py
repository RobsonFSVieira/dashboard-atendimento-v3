import streamlit as st
import pandas as pd
from datetime import datetime

def validar_dados(df):
    """Valida os dados conforme as premissas do projeto"""
    try:
        # Convertendo colunas de tempo para datetime
        df['retirada'] = pd.to_datetime(df['retirada'])
        df['inicio'] = pd.to_datetime(df['inicio'])
        df['fim'] = pd.to_datetime(df['fim'])
        
        # Aplicando filtros conforme premissas
        df = df[
            (df['tpatend'] >= 60) &  # Mínimo 1 minuto
            (df['tpatend'] <= 1800) &  # Máximo 30 minutos
            (df['tpesper'] <= 14400) &  # Máximo 4 horas de espera
            (df['status'].isin(['ATENDIDO', 'TRANSFERIDA']))
        ]
        
        return df
    
    except Exception as e:
        st.error(f"Erro na validação dos dados: {str(e)}")
        return None

def validar_colunas(df):
    """Valida e padroniza os nomes das colunas"""
    # Mapeamento de possíveis nomes para nomes padronizados
    mapa_colunas = {
        # Status
        'status_descricao': 'status',
        'status descrição': 'status',
        'Status Descrição': 'status',
        'Status': 'status',
        'STATUS': 'status',
        
        # Guichê
        'guiche': 'guichê',
        'guichê': 'guichê',
        'Guichê': 'guichê',
        'Guiche': 'guichê',
        'GUICHE': 'guichê',
        
        # Usuário
        'usuario': 'usuário',
        'usuário': 'usuário',
        'Usuário': 'usuário',
        'Usuario': 'usuário',
        'USUARIO': 'usuário',
        
        # Datas e Tempos (já estão corretos)
        'retirada': 'retirada',
        'inicio': 'inicio',
        'fim': 'fim',
        'tpatend': 'tpatend',
        'tpesper': 'tpesper'
    }
    
    # Mostrar colunas para debug
    with st.sidebar.expander("Debug"):
        st.write("Colunas no arquivo:", df.columns.tolist())
        st.write("Colunas após merge com códigos serão adicionadas: CLIENTE, OPERAÇÃO")
    
    # Renomear colunas existentes
    for col_atual in df.columns:
        col_lower = col_atual.lower().strip()
        for key, value in mapa_colunas.items():
            if col_lower == key.lower():
                df = df.rename(columns={col_atual: value})
                break
    
    # Verificar colunas obrigatórias da base
    colunas_obrigatorias = [
        'status', 'guichê', 'usuário',
        'retirada', 'inicio', 'fim', 
        'tpatend', 'tpesper', 'prefixo'  # prefixo necessário para merge
    ]
    
    colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
    
    if colunas_faltantes:
        st.error(f"❌ Colunas não encontradas: {', '.join(colunas_faltantes)}")
        st.write("Por favor, verifique se seu arquivo possui as seguintes colunas:")
        for col in colunas_obrigatorias:
            st.write(f"- {col}")
        raise ValueError("Estrutura do arquivo inválida")
    
    return df

def carregar_dados():
    """Carrega e processa os arquivos necessários"""
    try:
        # Debug info
        st.sidebar.markdown("### 🔄 Status do Carregamento")
        
        arquivo_base = st.sidebar.file_uploader(
            "Base de Dados (base.xlsx)", 
            type="xlsx",
            help="Arquivo com os dados brutos de atendimento"
        )
        
        arquivo_codigo = st.sidebar.file_uploader(
            "Códigos (codigo.xlsx)", 
            type="xlsx",
            help="Arquivo com os códigos de cliente e operação"
        )
        
        arquivo_medias = st.sidebar.file_uploader(
            "Médias (medias_atend.xlsx)", 
            type="xlsx",
            help="Arquivo com as médias de atendimento"
        )
        
        if not all([arquivo_base, arquivo_codigo, arquivo_medias]):
            return None
            
        with st.spinner('Carregando dados...'):
            # Carregar arquivos com validação
            try:
                df_base = pd.read_excel(arquivo_base)
                st.sidebar.success("✅ Base carregada")
            except Exception as e:
                st.sidebar.error(f"❌ Erro ao carregar base: {str(e)}")
                return None

            try:
                df_codigo = pd.read_excel(arquivo_codigo)
                st.sidebar.success("✅ Códigos carregados")
            except Exception as e:
                st.sidebar.error(f"❌ Erro ao carregar códigos: {str(e)}")
                return None

            try:
                df_medias = pd.read_excel(arquivo_medias, sheet_name="DADOS")
                st.sidebar.success("✅ Médias carregadas")
            except Exception as e:
                st.sidebar.error(f"❌ Erro ao carregar médias: {str(e)}")
                return None
            
            # Validar e padronizar colunas
            df_base = validar_colunas(df_base)
            
            # Validar dados
            df_base = validar_dados(df_base)
            
            if df_base is None:
                return None
            
            # Merge com códigos
            df_final = pd.merge(
                df_base,
                df_codigo[['prefixo', 'CLIENTE', 'OPERAÇÃO']],  # Especificar colunas
                on='prefixo',
                how='left'
            )
            
            # Verificar merge
            if df_final['CLIENTE'].isna().any() or df_final['OPERAÇÃO'].isna().any():
                st.sidebar.warning("⚠️ Alguns registros não têm correspondência nos códigos")
            
            # Calcular tempo de permanência
            df_final['tempo_permanencia'] = df_final['tpatend'] + df_final['tpesper']
            
            st.sidebar.success("✅ Processamento concluído")
            
            # Debug info
            st.sidebar.markdown("### 📊 Info dos Dados")
            st.sidebar.write(f"Registros carregados: {len(df_final)}")
            st.sidebar.write(f"Período: {df_final['retirada'].dt.date.min()} a {df_final['retirada'].dt.date.max()}")
            
            return {
                'base': df_final,
                'medias': df_medias,
                'codigo': df_codigo
            }
            
    except Exception as e:
        st.sidebar.error(f"❌ Erro no carregamento: {str(e)}")
        return None