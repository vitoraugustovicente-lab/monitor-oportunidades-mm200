import datetime
import pandas as pd
import streamlit as st
from config.settings import INDICES
from src.scanner import obter_dados_ativos, triagem_mm200

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Monitor de Oportunidades MM200",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Monitor de Oportunidades (MM200)")
st.markdown("Acompanhe os ativos próximos da Média Móvel de 200 períodos.")

# Barra lateral para configurações de filtro
st.sidebar.header("Filtros de Busca")
margem_limite = st.sidebar.slider("Proximidade da MM200 (%)", 1.0, 10.0, 5.0, 0.5)

# Seleção de Tickers padrão
tickers_exemplo = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "AAPL", "MSFT", "GOOGL"]
tickers_input = st.sidebar.text_area(
    "Tickers (separados por vírgula):", 
    value=", ".join(tickers_exemplo)
)

tickers_lista = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if st.button("Executar Análise"):
    with st.spinner("Buscando dados no Yahoo Finance..."):
        dados = obter_dados_ativos(tickers_lista)
        
        if not dados.empty:
            df_resultado = triagem_mm200(dados, percentual_limite=margem_limite)
            
            if not df_resultado.empty:
                st.success(f"Encontrados {len(df_resultado)} ativos dentro do limite estipulado!")
                st.dataframe(df_resultado, use_container_width=True)
            else:
                st.info("Nenhum ativo encontrado dentro do limite de proximidade selecionado.")
        else:
            st.error("Erro ao carregar os dados dos ativos. Verifique se os tickers estão corretos.")
