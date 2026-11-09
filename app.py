import datetime
import io
import pandas as pd
import streamlit as st
import yfinance as yf

from config.settings import CATEGORIAS
from src.scanner import obter_dados_ativos, triagem_mm200

# Configuração da página (apenas uma chamada no início)
st.set_page_config(
    page_title="Monitor de Oportunidades MM200 Semanal",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Monitor de Oportunidades (MM200 Semanal + Análise Combinada)")
st.markdown("Varredura técnica inteligente com cruzamento de Média Móvel de 200 Semanas e RSI.")

# ==========================================
# BARRA LATERAL - FILTRO HIERÁRQUICO DE MERCADO
# ==========================================
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
rsi_filtro = st.sidebar.slider("RSI Máximo (Filtrar Sobrevendidos)", 20, 100, 100, 5)
periodo = st.sidebar.selectbox("Período de Histórico:", ["5y", "10y", "max"], index=0)

st.sidebar.markdown("---")
tickers_input = st.sidebar.text_area(
    "Ativos a analisar (edite se desejar):",
    value=", ".join(lista_padrao),
    height=130
)

tickers_lista = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# ==========================================
# PAINEL CENTRAL - MÉTRICAS E VARREDURA
# ==========================================
col1, col2 = st.columns(2)
col1.metric("Mercado Selecionado", mercado_selecionado)
col2.metric("Segmento / Setor", subcategoria_selecionada)

st.info(f"📌 **Total de ativos prontos para varredura nesta categoria:** {len(tickers_lista)}")

if st.button("🚀 Iniciar Varredura de Mercado (Semanal)"):
    with st.spinner("Analisando cotações semanais, aplicando MM200 e RSI..."):
        # Executa a busca passando intervalo semanal e período para garantir histórico de 200 semanas
       dados_fechamento, dados_volume = obter_dados_ativos(tickers_lista)
        
        if not dados_fechamento.empty:
            df_resultado = triagem_mm200(
                dados_fechamento, 
                dados_volume, 
                percentual_limite=margem_limite,
                rsi_maximo=rsi_filtro
            )
            
            if not df_resultado.empty:
                # Métricas de resumo
                qtd_compras_fortes = len(df_resultado[df_resultado['Diagnóstico'].str.contains("Compra Forte", na=False)])
                qtd_suporte = len(df_resultado[df_resultado['Condição MM200'].str.contains("Suporte", na=False)])
                qtd_resistencia = len(df_resultado[df_resultado['Condição MM200'].str.contains("Resistência", na=False)])
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total de Oportunidades", len(df_resultado))
                m2.metric("🎯 Compras Fortes", qtd_compras_fortes)
                m3.metric("🟢 Em Zona de Suporte", qtd_suporte)
                m4.metric("🔴 Em Zona de Resistência", qtd_resistencia)
                
                st.markdown("---")
                st.success(f"Encontradas {len(df_resultado)} oportunidades dentro dos parâmetros no gráfico semanal!")
                
                # Exibição da tabela interativa
                st.dataframe(
                    df_resultado,
                    column_config={
                        "Gráfico": st.column_config.LinkColumn(
                            "Gráfico TradingView",
                            display_text="Abrir Chart 📊"
                        )
                    },
                    use_container_width=True
                )
                
                # ==========================================
                # ÁREA DE EXPORTAÇÃO (CSV E EXCEL)
                # ==========================================
                st.markdown("### 📥 Exportar Relatório")
                exp_col1, exp_col2 = st.columns(2)
                
                data_hoje = datetime.date.today().strftime("%Y-%m-%d")
                nome_arquivo_base = f"oportunidades_mm200_semanal_{mercado_selecionado.lower().replace(' ', '_')}_{data_hoje}"
                
                # Exportação CSV
                csv_data = df_resultado.to_csv(index=False).encode('utf-8')
                exp_col1.download_button(
                    label="📄 Baixar em CSV",
                    data=csv_data,
                    file_name=f"{nome_arquivo_base}.csv",
                    mime="text/csv"
                )
                
                # Exportação Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name='Oportunidades')
                buffer.seek(0)
                
                exp_col2.download_button(
                    label="📊 Baixar em Excel (.xlsx)",
                    data=buffer,
                    file_name=f"{nome_arquivo_base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Nenhum ativo desta categoria atendeu aos critérios de MM200 e RSI selecionados.")
        else:
            st.error("Não foi possível carregar os dados dos ativos no momento. Tente novamente.")

# ==========================================
# VISUALIZAÇÃO GRÁFICA INDIVIDUAL (OPCIONAL)
# ==========================================
st.markdown("---")
st.subheader("🔍 Análise Gráfica Individual (Semanal)")
ticker_grafico = st.selectbox("Selecione um ativo para visualizar o gráfico semanal:", tickers_lista)

if ticker_grafico:
    df_grafico = yf.download(ticker_grafico, period=periodo, interval="1wk", progress=False)
    if not df_grafico.empty:
        if isinstance(df_grafico.columns, pd.MultiIndex):
            df_grafico = df_grafico['Close']
            df_grafico.columns = [ticker_grafico]
        else:
            df_grafico = df_grafico[['Close']]
            
        df_grafico['MMA200 Semanal'] = df_grafico.iloc[:, 0].rolling(window=200).mean()
        st.line_chart(df_grafico)
           
