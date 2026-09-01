import datetime
import io
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

st.title("📈 Monitor de Oportunidades (MM200 + Exportação)")
st.markdown("Varredura técnica combinando MM200, RSI, Volume, TradingView e Exportação de Relatórios.")

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
rsi_filtro = st.sidebar.slider("RSI Máximo (Filtrar Sobrevendidos)", 20, 100, 100, 5)

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
    with st.spinner("Analisando mercado, calculando indicadores e preparando relatório..."):
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
                st.success(f"Encontradas {len(df_resultado)} oportunidades dentro dos parâmetros!")
                
                # Exibição com Coluna de Link Clicável
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
                
                # --- ÁREA DE EXPORTAÇÃO (ITEM 4) ---
                st.markdown("### 📥 Exportar Resultados")
                exp_col1, exp_col2 = st.columns(2)
                
                data_hoje = datetime.date.today().strftime("%Y-%m-%d")
                nome_arquivo_base = f"oportunidades_mm200_{mercado_selecionado.lower().replace(' ', '_')}_{data_hoje}"
                
                # Exportação CSV
                csv_data = df_resultado.to_csv(index=False).encode('utf-8')
                exp_col1.download_button(
                    label="📄 Baixar em CSV",
                    data=csv_data,
                    file_name=f"{nome_arquivo_base}.csv",
                    mime="text/csv"
                )
                
                # Exportação Excel (.xlsx)
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
