import datetime
import pandas as pd
import streamlit as st
from config.settings import CATEGORIAS
from src.scanner import obter_dados_ativos, triagem_mm200

# Configuração da página
st.set_page_config(
    page_title="Monitor de Oportunidades MM200",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Monitor de Oportunidades (MM200 + RSI & Volume)")
st.markdown("Varredura técnica combinando Média Móvel de 200 períodos, Índice de Força Relativa (RSI) e Liquidez.")

# Barra Lateral - Filtro Hierárquico
st.sidebar.header("1. Seleção de Mercado")

mercado_selecionado = st.sidebar.selectbox(
    "Escolha o Mercado (1º Nível):",
    list(CATEGORIAS.keys())
)

subcategorias = list(CATEGORIAS[mercado_selecionado].keys())
subcategoria_selecionada = st.sidebar.selectbox(
    "Escolha o Setor / Segmento (2º Nível):",
    subcategorias
)

lista_padrao = CATEGORIAS[mercado_selecionado][subcategoria_selecionada]

st.sidebar.markdown("---")
st.sidebar.header("2. Parâmetros de Análise")
margem_limite = st.sidebar.slider("Proximidade da MM200 (%)", 1.0, 10.0, 5.0, 0.5)

# Filtro Adicional por RSI máximo
rsi_filtro = st.sidebar.slider("RSI Máximo (Filtrar Sobrevendidos)", 20, 100, 100, 5, help="Selecione 30 ou 40 para encontrar apenas ativos muito sobrevendidos.")

tickers_input = st.sidebar.text_area(
    "Ativos a analisar (edite conforme necessário):",
    value=", ".join(lista_padrao),
    height=130
)

tickers_lista = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# Painel Central
col1, col2 = st.columns(2)
col1.metric("Mercado Selecionado", mercado_selecionado)
col2.metric("Segmento / Setor", subcategoria_selecionada)

st.info(f"📌 **Total de ativos prontos para varredura nesta categoria:** {len(tickers_lista)}")

if st.button("🚀 Iniciar Varredura de Mercado"):
    with st.spinner("Processando cotações, volumes e calculando RSI (14)..."):
        dados_fechamento, dados_volume = obter_dados_ativos(tickers_lista)
        
        if not dados_fechamento.empty:
            df_resultado = triagem_mm200(
                dados_fechamento, 
                dados_volume, 
                percentual_limite=margem_limite,
                rsi_maximo=rsi_filtro
            )
            
            if not df_resultado.empty:
                qtd_suporte = len(df_resultado[df_resultado['Condição'].str.contains("Suporte")])
                qtd_resistencia = len(df_resultado[df_resultado['Condição'].str.contains("Resistência")])
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total de Oportunidades", len(df_resultado))
                m2.metric("🟢 Em Zona de Suporte", qtd_suporte)
                m3.metric("🔴 Em Zona de Resistência", qtd_resistencia)
                
                st.markdown("---")
                st.success(f"Encontradas {len(df_resultado)} oportunidades dentro dos parâmetros selecionados!")
                st.dataframe(df_resultado, use_container_width=True)
            else:
                st.warning("Nenhum ativo desta categoria atendeu aos critérios de MM200 e RSI selecionados.")
        else:
            st.error("Não foi possível carregar os dados dos ativos no momento. Tente novamente.")
