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

st.title("📈 Monitor de Oportunidades (MM200)")
st.markdown("Varredura de ativos próximos da Média Móvel de 200 períodos com identificação de Suporte e Resistência.")

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

tickers_input = st.sidebar.text_area(
    "Ativos a analisar (edite conforme necessário):",
    value=", ".join(lista_padrao),
    height=150
)

tickers_lista = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# Painel Central
col1, col2 = st.columns(2)
col1.metric("Mercado Selecionado", mercado_selecionado)
col2.metric("Segmento / Setor", subcategoria_selecionada)

st.info(f"📌 **Total de ativos prontos para varredura nesta categoria:** {len(tickers_lista)}")

if st.button("🚀 Iniciar Varredura de Mercado"):
    with st.spinner("Processando cotações e analisando tendências da MM200..."):
        dados = obter_dados_ativos(tickers_lista)
        
        if not dados.empty:
            df_resultado = triagem_mm200(dados, percentual_limite=margem_limite)
            
            if not df_resultado.empty:
                # Métricas rápidas do resultado
                qtd_suporte = len(df_resultado[df_resultado['Condição / Sinal'].str.contains("Suporte")])
                qtd_resistencia = len(df_resultado[df_resultado['Condição / Sinal'].str.contains("Resistência")])
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total de Oportunidades", len(df_resultado))
                m2.metric("🟢 Em Zona de Suporte", qtd_suporte)
                m3.metric("🔴 Em Zona de Resistência", qtd_resistencia)
                
                st.markdown("---")
                st.success(f"Encontradas {len(df_resultado)} oportunidades a menos de {margem_limite}% da MM200!")
                st.dataframe(df_resultado, use_container_width=True)
            else:
                st.warning("Nenhum ativo desta categoria está dentro da margem de proximidade configurada.")
        else:
            st.error("Não foi possível carregar os dados dos ativos no momento. Tente novamente.")
