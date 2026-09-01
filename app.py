import datetime
import pandas as pd
import streamlit as st
from config.settings import INDICES, TICKERS_IBOVESPA, TICKERS_US_PRINCIPAIS
from src.scanner import obter_dados_ativos, triagem_mm200

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Monitor de Oportunidades MM200",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Monitor de Oportunidades (MM200)")
st.markdown("Acompanhe os ativos do Ibovespa, Nasdaq e NYSE próximos da Média Móvel de 200 períodos.")

# Barra lateral para configurações de filtro
st.sidebar.header("Filtros de Busca")
margem_limite = st.sidebar.slider("Proximidade da MM200 (%)", 1.0, 10.0, 5.0, 0.5)

# Seleção de Mercado
opcao_mercado = st.sidebar.selectbox(
    "Escolha o Mercado / Lista:",
    ["Ibovespa (B3)", "US - Nasdaq & NYSE (Principais)", "Todos Combinados", "Inserção Manual"]
)

if opcao_mercado == "Ibovespa (B3)":
    lista_padrao = TICKERS_IBOVESPA
elif opcao_mercado == "US - Nasdaq & NYSE (Principais)":
    lista_padrao = TICKERS_US_PRINCIPAIS
elif opcao_mercado == "Todos Combinados":
    lista_padrao = TICKERS_IBOVESPA + TICKERS_US_PRINCIPAIS
else:
    lista_padrao = ["PETR4.SA", "VALE3.SA", "AAPL", "MSFT"]

tickers_input = st.sidebar.text_area(
    "Tickers selecionados (edite se necessário):", 
    value=", ".join(lista_padrao),
    height=150
)

tickers_lista = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

st.write(f"**Total de ativos na lista atual:** {len(tickers_lista)}")

if st.button("Executar Análise"):
    with st.spinner("Buscando dados no Yahoo Finance... Isso pode levar alguns segundos."):
        dados = obter_dados_ativos(tickers_lista)
        
        if not dados.empty:
            df_resultado = triagem_mm200(dados, percentual_limite=margem_limite)
            
            if not df_resultado.empty:
                st.success(f"Encontrados {len(df_resultado)} ativos dentro do limite de {margem_limite}%!")
                st.dataframe(df_resultado, use_container_width=True)
            else:
                st.info("Nenhum ativo encontrado dentro do limite de proximidade selecionado.")
        else:
            st.error("Erro ao carregar os dados dos ativos. Verifique se a conexão ou os tickers estão corretos.")
