import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Monitor de Ações (MMA200 Semanal)", layout="wide")

st.title("📈 Monitor de Ações - Média Móvel de 200 Semanas")
st.write("Acompanhamento de ativos da B3 em relação à MMA200 no gráfico **semanal**.")

# Lista padrão de tickers da B3
DEFAULT_TICKERS = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "WEGE3.SA", "BBAS3.SA"]

# Sidebar para seleção de ativos
st.sidebar.header("Configurações")
tickers_input = st.sidebar.text_input(
    "Tickers (separados por vírgula):",
    value=", ".join(DEFAULT_TICKERS)
)
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# Período maior para garantir mais de 200 semanas de histórico
periodo = st.sidebar.selectbox("Período de Dados:", ["5y", "10y", "max"], index=0)

@st.cache_data(ttl=3600)
def carregar_dados(lista_tickers, per):
    dados_acoes = []
    
    for ticker in lista_tickers:
        try:
            # Baixa os dados no tempo gráfico SEMANAL (interval="1wk")
            df = yf.download(ticker, period=per, interval="1wk", progress=False)
            if df.empty:
                continue
            
            # Trata MultiIndex caso retorne do yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df = df['Close']
            else:
                df = df[['Close']]
                
            # Média Móvel de 200 semanas
            df['MMA200_Semanal'] = df.iloc[:, 0].rolling(window=200).mean()
            
            preco_atual = float(df.iloc[-1, 0])
            mma200_atual = float(df['MMA200_Semanal'].dropna().iloc[-1]) if not df['MMA200_Semanal'].dropna().empty else None
            
            if mma200_atual:
                distancia = ((preco_atual - mma200_atual) / mma200_atual) * 100
                status = "🟢 Acima da MMA200 Semanal" if preco_atual >= mma200_atual else "🔴 Abaixo da MMA200 Semanal"
            else:
                distancia = None
                status = "⚠️ Histórico insuficiente (< 200 semanas)"

            dados_acoes.append({
                "Ticker": ticker.replace(".SA", ""),
                "Preço Atual (R$)": round(preco_atual, 2),
                "MMA 200 Semanal (R$)": round(mma200_atual, 2) if mma200_atual else "N/A",
                "Distância (%)": f"{distancia:+.2f}%" if distancia is not None else "N/A",
                "Status": status
            })
        except Exception as e:
            st.error(f"Erro ao carregar {ticker}: {e}")
            
    return pd.DataFrame(dados_acoes)

if tickers:
    df_resultado = carregar_dados(tickers, periodo)
    
    if not df_resultado.empty:
        st.subheader("Resumo dos Ativos (Semanal)")
        st.dataframe(df_resultado, use_container_width=True)
        
        # Gráficos individuais
        st.subheader("Visualização Gráfica Semanal")
        ticker_selecionado = st.selectbox("Selecione o ativo para visualizar o gráfico:", tickers)
        
        df_grafico = yf.download(ticker_selecionado, period=periodo, interval="1wk", progress=False)
        if isinstance(df_grafico.columns, pd.MultiIndex):
            df_grafico = df_grafico['Close']
            df_grafico.columns = [ticker_selecionado]
        else:
            df_grafico = df_grafico[['Close']]
            
        df_grafico['MMA200 Semanal'] = df_grafico.iloc[:, 0].rolling(window=200).mean()
        st.line_chart(df_grafico)
else:
    st.info("Insira ao menos um ticker para visualizar o monitor.")
