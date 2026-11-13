import datetime
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config.settings import CATEGORIAS
from src.scanner import obter_dados_ativos, triagem_mm200, _converter_para_simbolo_tv

# Configuração da página
st.set_page_config(
    page_title="Monitor Global de Oportunidades MM200 Semanal",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Monitor Global de Oportunidades (MM200 Semanal)")
st.markdown("Varredura unificada de B3, EUA e Criptomoedas — Preço Nominal (sem desconto de dividendos).")

# ==========================================
# UNIFICAÇÃO DE TODOS OS ATIVOS E MAPA DE ORIGEM
# ==========================================
todos_tickers_unicos = []
mapa_origem = {}

for mercado, setores in CATEGORIAS.items():
    for setor, lista_ativos in setores.items():
        for ticker in lista_ativos:
            t_limpo = ticker.strip().upper()
            if t_limpo not in mapa_origem:
                todos_tickers_unicos.append(t_limpo)
                mapa_origem[t_limpo] = f"{mercado} | {setor}"

# ==========================================
# BARRA LATERAL - PARÂMETROS GLOBAIS
# ==========================================
st.sidebar.header("⚙️ Parâmetros de Filtro")
margem_limite = st.sidebar.slider("Proximidade da MM200 (%)", 0.5, 10.0, 1.0, 0.5)
rsi_filtro = st.sidebar.slider("RSI Máximo (Filtrar Sobrevendidos)", 20, 100, 100, 5)
periodo = st.sidebar.selectbox("Período de Histórico:", ["5y", "10y", "max"], index=0)

st.sidebar.markdown("---")
st.sidebar.info(
    f"🌐 **Base Unificada:** {len(todos_tickers_unicos)} ativos únicos carregados "
    f"(B3, S&P 500, NASDAQ, NYSE e Criptomoedas)."
)

# ==========================================
# PAINEL CENTRAL - VARREDURA GLOBAL
# ==========================================
col1, col2, col3 = st.columns(3)
col1.metric("Escopo da Varredura", "Todos os Mercados + Cripto")
col2.metric("Total de Ativos Cadastrados", len(todos_tickers_unicos))
col3.metric("Base de Cálculo", "Nominal (Sem Dividendos)")

if st.button("🚀 Iniciar Varredura Global (Todos os Ativos)"):
    with st.spinner(f"Buscando velas semanais nominais dos {len(todos_tickers_unicos)} ativos no TradingView..."):
        dados_fechamento, dados_volume = obter_dados_ativos(
            todos_tickers_unicos,
            periodo=periodo,
            intervalo="1wk",
            auto_adjust=False
        )

        if dados_fechamento:
            ativos_validos_200w = sum(
                1 for serie in dados_fechamento.values()
                if len(serie) >= 200
            )

            df_resultado = triagem_mm200(
                dados_fechamento,
                dados_volume,
                percentual_limite=margem_limite,
                rsi_maximo=rsi_filtro
            )

            st.caption(
                f"📊 Diagnóstico da carga: **{len(dados_fechamento)}** ativos baixados | "
                f"**{ativos_validos_200w}** ativos com histórico completo (≥ 200 semanas)."
            )

            if not df_resultado.empty:
                def identificar_origem(ticker_tabela):
                    if f"{ticker_tabela}.SA" in mapa_origem:
                        return mapa_origem[f"{ticker_tabela}.SA"]
                    return mapa_origem.get(ticker_tabela, "Global")

                df_resultado.insert(1, "Mercado / Setor", df_resultado["Ticker"].apply(identificar_origem))

                qtd_compras_fortes = len(df_resultado[df_resultado['Diagnóstico'].str.contains("Compra Forte", na=False)])
                qtd_suporte = len(df_resultado[df_resultado['Condição MM200'].str.contains("Suporte", na=False)])
                qtd_resistencia = len(df_resultado[df_resultado['Condição MM200'].str.contains("Resistência", na=False)])

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total de Oportunidades", len(df_resultado))
                m2.metric("🎯 Compras Fortes", qtd_compras_fortes)
                m3.metric("🟢 Em Zona de Suporte", qtd_suporte)
                m4.metric("🔴 Em Zona de Resistência", qtd_resistencia)

                st.markdown("---")
                st.success(f"Encontradas {len(df_resultado)} oportunidades dentro da faixa de ±{margem_limite}% da MM200 Semanal!")

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
                st.markdown("### 📥 Exportar Relatório Consolidado")
                exp_col1, exp_col2 = st.columns(2)

                data_hoje = datetime.date.today().strftime("%Y-%m-%d")
                nome_arquivo_base = f"oportunidades_mm200_global_{data_hoje}"

                csv_data = df_resultado.to_csv(index=False).encode('utf-8')
                exp_col1.download_button(
                    label="📄 Baixar Tudo em CSV",
                    data=csv_data,
                    file_name=f"{nome_arquivo_base}.csv",
                    mime="text/csv"
                )

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name='Oportunidades_Global')
                buffer.seek(0)

                exp_col2.download_button(
                    label="📊 Baixar Tudo em Excel (.xlsx)",
                    data=buffer,
                    file_name=f"{nome_arquivo_base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning(f"Nenhum ativo atendeu aos critérios (±{margem_limite}% da MM200 e RSI ≤ {rsi_filtro}).")
        else:
            st.error("Não foi possível carregar os dados dos ativos no momento. Tente novamente.")

# ==========================================
# VISUALIZAÇÃO GRÁFICA INDIVIDUAL (TRADINGVIEW)
# ==========================================
st.markdown("---")
st.subheader("🔍 Gráfico Interativo TradingView (Semanal + MM200)")
ticker_grafico = st.selectbox("Selecione qualquer ativo monitorado para visualizar o gráfico:", todos_tickers_unicos)

if ticker_grafico:
    simbolo_widget = _converter_para_simbolo_tv(ticker_grafico)
    widget_html = f"""
    <div class="tradingview-widget-container" style="height:500px;width:100%">
      <div id="tradingview_chart" style="height:500px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{simbolo_widget}",
        "interval": "W",
        "timezone": "America/Sao_Paulo",
        "theme": "light",
        "style": "1",
        "locale": "br",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "studies": [
          {{"id": "MASimple@tv-basicstudies", "inputs": {{"length": 200}}}}
        ],
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(widget_html, height=510)
