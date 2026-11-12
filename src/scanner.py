import time
import pandas as pd
import numpy as np
import yfinance as yf


def _baixar_bloco(tickers, periodo, intervalo, auto_adjust):
    """Função auxiliar para baixar um bloco homogêneo de tickers."""
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()

    lista_fech = []
    lista_vol = []
    tamanho_lote = 50

    for i in range(0, len(tickers), tamanho_lote):
        lote = tickers[i:i + tamanho_lote]
        try:
            dados = yf.download(
                lote,
                period=periodo,
                interval=intervalo,
                auto_adjust=auto_adjust,
                group_by="column",
                threads=True,
                progress=False
            )

            if dados.empty:
                continue

            if isinstance(dados.columns, pd.MultiIndex):
                # Garante o uso exclusivo da coluna 'Close' (preço nominal quando auto_adjust=False)
                fech = dados['Close'].copy()
                vol = dados['Volume'].copy()
            else:
                fech = dados[['Close']].rename(columns={'Close': lote[0]}).copy()
                vol = dados[['Volume']].rename(columns={'Volume': lote[0]}).copy()

            lista_fech.append(fech)
            lista_vol.append(vol)
            time.sleep(0.4)
        except Exception as e:
            print(f"Erro no lote {lote[:3]}: {e}")

    if not lista_fech:
        return pd.DataFrame(), pd.DataFrame()

    df_f = pd.concat(lista_fech, axis=1)
    df_v = pd.concat(lista_vol, axis=1)

    df_f = df_f.loc[:, ~df_f.columns.duplicated()]
    df_v = df_v.loc[:, ~df_v.columns.duplicated()]
    return df_f, df_v


def obter_dados_ativos(tickers, periodo="5y", intervalo="1wk", auto_adjust=False):
    """
    Separa Ações/ETFs de Criptomoedas antes do download para evitar conflito de
    calendário (5 dias vs 7 dias) e garante cálculo nominal consistente.
    """
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()

    tickers_cripto = [t for t in tickers if "-USD" in str(t).upper()]
    tickers_acoes = [t for t in tickers if "-USD" not in str(t).upper()]

    fech_acoes, vol_acoes = _baixar_bloco(tickers_acoes, periodo, intervalo, auto_adjust)
    fech_cripto, vol_cripto = _baixar_bloco(tickers_cripto, periodo, intervalo, auto_adjust)

    partes_fech = [df for df in [fech_acoes, fech_cripto] if not df.empty]
    partes_vol = [df for df in [vol_acoes, vol_cripto] if not df.empty]

    if not partes_fech:
        return pd.DataFrame(), pd.DataFrame()

    fechamento_total = pd.concat(partes_fech, axis=1)
    volume_total = pd.concat(partes_vol, axis=1)

    fechamento_total = fechamento_total.loc[:, ~fechamento_total.columns.duplicated()]
    volume_total = volume_total.loc[:, ~volume_total.columns.duplicated()]

    return fechamento_total, volume_total


def gerar_link_tradingview(ticker_original):
    """
    Formata o link do TradingView de acordo com o mercado do ticker.
    """
    ticker_str = str(ticker_original).strip().upper()

    if ticker_str.endswith(".SA"):
        simbolo = f"BMFBOVESPA:{ticker_str.replace('.SA', '')}"
    elif "-USD" in ticker_str:
        simbolo = f"CRYPTO:{ticker_str.replace('-USD', 'USD')}"
    else:
        simbolo = ticker_str

    return f"https://br.tradingview.com/chart/?symbol={simbolo}"


def triagem_mm200(dados_fechamento, dados_volume, percentual_limite=5.0, rsi_maximo=100):
    """
    Calcula a MM200 Semanal e o RSI(14) sobre a mesma série nominal de fechamento.
    """
    resultados = []

    if isinstance(dados_fechamento, pd.Series):
        dados_fechamento = dados_fechamento.to_frame()

    for ticker in dados_fechamento.columns:
        # Remove semanas sem negociação (NaN) específicas daquele ativo
        serie_preco = dados_fechamento[ticker].dropna()

        # Exige mínimo de 200 semanas válidas
        if len(serie_preco) < 200:
            continue

        # 1. Cálculo da MM200 Semanal na mesma série nominal do preço atual
        mm200_serie = serie_preco.rolling(window=200).mean()

        preco_atual = float(serie_preco.iloc[-1])
        mm200_atual = float(mm200_serie.iloc[-1])

        if pd.isna(mm200_atual) or mm200_atual == 0:
            continue

        distancia_pct = ((preco_atual - mm200_atual) / mm200_atual) * 100

        # 2. Cálculo do RSI (14 períodos)
        delta = serie_preco.diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        rsi_serie = 100 - (100 / (1 + rs))
        rsi_atual = float(rsi_serie.iloc[-1]) if not pd.isna(rsi_serie.iloc[-1]) else 50.0

        # 3. Filtros
        if abs(distancia_pct) <= percentual_limite and rsi_atual <= rsi_maximo:
            condicao = "🟢 Suporte MM200" if preco_atual >= mm200_atual else "🔴 Resistência MM200"

            if preco_atual >= mm200_atual and rsi_atual <= 40:
                diag = "🎯 Compra Forte (MM200 + RSI)"
            elif preco_atual >= mm200_atual:
                diag = "✅ Tendência de Alta (Acima MM200)"
            else:
                diag = "⚠️ Abaixo da MM200"

            ticker_limpo = str(ticker).replace(".SA", "")
            link_tv = gerar_link_tradingview(ticker)

            resultados.append({
                "Ticker": ticker_limpo,
                "Preço Atual": round(preco_atual, 2),
                "Gráfico": link_tv,
                "MM200 Semanal": round(mm200_atual, 2),
                "Distância (%)": f"{distancia_pct:+.2f}%",
                "RSI (14)": round(rsi_atual, 1),
                "Condição MM200": condicao,
                "Diagnóstico": diag
            })

    return pd.DataFrame(resultados)
