import time
import pandas as pd
import numpy as np
import yfinance as yf


def obter_dados_ativos(tickers, periodo="5y", intervalo="1wk", auto_adjust=False):
    """
    Baixa dados agrupados por ticker (group_by='ticker') para evitar qualquer
    mistura de colunas ou calendários entre B3, EUA e Criptomoedas.
    """
    if not tickers:
        return {}, {}

    dados_por_ticker = {}
    tamanho_lote = 50

    for i in range(0, len(tickers), tamanho_lote):
        lote = tickers[i:i + tamanho_lote]
        try:
            dados = yf.download(
                lote,
                period=periodo,
                interval=intervalo,
                auto_adjust=auto_adjust,
                group_by="ticker",
                threads=True,
                progress=False
            )

            if dados.empty:
                continue

            if len(lote) == 1:
                ticker = lote[0]
                if "Close" in dados.columns:
                    serie = dados["Close"].dropna().sort_index()
                    if not serie.empty:
                        dados_por_ticker[ticker] = serie
            else:
                for ticker in lote:
                    if ticker in dados.columns.get_level_values(0):
                        df_t = dados[ticker]
                        if "Close" in df_t.columns:
                            serie = df_t["Close"].dropna().sort_index()
                            if not serie.empty:
                                dados_por_ticker[ticker] = serie

            time.sleep(0.4)
        except Exception as e:
            print(f"Erro ao baixar lote {lote[:3]}: {e}")

    return dados_por_ticker, {}


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
    Calcula a MM200 Semanal e o RSI(14) isoladamente na série histórica de cada ticker.
    """
    resultados = []

    if isinstance(dados_fechamento, pd.DataFrame):
        iterador = {col: dados_fechamento[col].dropna().sort_index() for col in dados_fechamento.columns}
    else:
        iterador = dados_fechamento

    for ticker, serie_bruta in iterador.items():
        if isinstance(serie_bruta, pd.DataFrame):
            serie_preco = serie_bruta.iloc[:, 0].dropna().sort_index()
        else:
            serie_preco = serie_bruta.dropna().sort_index()

        # Remove eventuais índices duplicados (ex: semana em andamento duplicada pelo Yahoo)
        serie_preco = serie_preco[~serie_preco.index.duplicated(keep='last')]

        # Exige mínimo de 200 semanas reais de histórico
        if len(serie_preco) < 200:
            continue

        # 1. Cálculo exato da MM200 Semanal
        mm200_serie = serie_preco.rolling(window=200).mean()

        preco_atual = float(serie_preco.iloc[-1])
        mm200_atual = float(mm200_serie.iloc[-1])

        if pd.isna(mm200_atual) or mm200_atual <= 0:
            continue

        distancia_pct = ((preco_atual - mm200_atual) / mm200_atual) * 100

        # 2. Cálculo do RSI (14 períodos)
        delta = serie_preco.diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        rsi_serie = 100 - (100 / (1 + rs))
        rsi_atual = float(rsi_serie.iloc[-1]) if not pd.isna(rsi_serie.iloc[-1]) else 50.0

        # 3. Filtro rigoroso de proximidade e RSI
        if abs(distancia_pct) <= float(percentual_limite) and rsi_atual <= float(rsi_maximo):
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
