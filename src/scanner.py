import io
from concurrent.futures import ThreadPoolExecutor
import requests
import pandas as pd
import yfinance as yf


def _baixar_csv_stooq(ticker_original):
    """
    Baixa histórico semanal 100% nominal (sem ajuste de dividendos) do Stooq
    para ações da B3 (.SA -> .br) e EUA (.us), sem necessidade de token.
    """
    t = str(ticker_original).strip().upper()
    if t.endswith(".SA"):
        simbolo = f"{t.replace('.SA', '').lower()}.br"
    else:
        # Stooq usa hífen em classes de ações como BRK-B -> brk-b.us
        simbolo = f"{t.lower()}.us"

    url = f"https://stooq.com/q/d/l/?s={simbolo}&i=w"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200 or "Date,Open" not in resp.text:
            return ticker_original, pd.Series(dtype=float)

        df = pd.read_csv(io.StringIO(resp.text))
        if df.empty or "Close" not in df.columns:
            return ticker_original, pd.Series(dtype=float)

        df["Date"] = pd.to_datetime(df["Date"])
        serie = df.set_index("Date")["Close"].dropna().sort_index()
        serie = serie[~serie.index.duplicated(keep="last")]
        return ticker_original, serie
    except Exception:
        return ticker_original, pd.Series(dtype=float)


def obter_dados_ativos(tickers, periodo="5y", intervalo="1wk", auto_adjust=False):
    """
    - Ações B3 e EUA: Stooq (100% nominal, sem ajuste de dividendos, sem token)
    - Criptomoedas (-USD): yfinance (100% nominal, pois não há dividendos)
    """
    if not tickers:
        return {}, {}

    dados_por_ticker = {}

    tickers_cripto = [t for t in tickers if "-USD" in str(t).upper()]
    tickers_acoes = [t for t in tickers if t not in tickers_cripto]

    # 1. Criptomoedas via yfinance
    if tickers_cripto:
        try:
            dados_c = yf.download(
                tickers_cripto,
                period=periodo,
                interval="1wk",
                group_by="ticker",
                threads=True,
                progress=False
            )
            if not dados_c.empty:
                for t in tickers_cripto:
                    if t in dados_c.columns.get_level_values(0):
                        s = dados_c[t]["Close"].dropna().sort_index()
                        if not s.empty:
                            dados_por_ticker[t] = s[~s.index.duplicated(keep="last")]
        except Exception:
            pass

    # 2. Ações B3 e EUA em paralelo via Stooq (10 workers simultâneos)
    if tickers_acoes:
        with ThreadPoolExecutor(max_workers=10) as executor:
            resultados_stooq = executor.map(_baixar_csv_stooq, tickers_acoes)
            for ticker, serie in resultados_stooq:
                if not serie.empty:
                    dados_por_ticker[ticker] = serie

    return dados_por_ticker, {}


def gerar_link_tradingview(ticker_original):
    ticker_str = str(ticker_original).strip().upper()
    if ticker_str.endswith(".SA"):
        simbolo = f"BMFBOVESPA:{ticker_str.replace('.SA', '')}"
    elif "-USD" in ticker_str:
        simbolo = f"CRYPTO:{ticker_str.replace('-USD', 'USD')}"
    else:
        simbolo = ticker_str
    return f"https://br.tradingview.com/chart/?symbol={simbolo}"


def triagem_mm200(dados_fechamento, dados_volume, percentual_limite=5.0, rsi_maximo=100):
    resultados = []
    iterador = (
        {col: dados_fechamento[col].dropna().sort_index() for col in dados_fechamento.columns}
        if isinstance(dados_fechamento, pd.DataFrame)
        else dados_fechamento
    )

    for ticker, serie_bruta in iterador.items():
        serie_preco = (
            serie_bruta.iloc[:, 0].dropna().sort_index()
            if isinstance(serie_bruta, pd.DataFrame)
            else serie_bruta.dropna().sort_index()
        )
        serie_preco = serie_preco[~serie_preco.index.duplicated(keep="last")]

        if len(serie_preco) < 200:
            continue

        # Cálculo exato da MM200 Semanal sobre série 100% nominal
        mm200_serie = serie_preco.rolling(window=200).mean()
        preco_atual = float(serie_preco.iloc[-1])
        mm200_atual = float(mm200_serie.iloc[-1])

        if pd.isna(mm200_atual) or mm200_atual <= 0:
            continue

        distancia_pct = ((preco_atual - mm200_atual) / mm200_atual) * 100

        # Cálculo do RSI (14 períodos)
        delta = serie_preco.diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        rsi_serie = 100 - (100 / (1 + rs))
        rsi_atual = float(rsi_serie.iloc[-1]) if not pd.isna(rsi_serie.iloc[-1]) else 50.0

        if abs(distancia_pct) <= float(percentual_limite) and rsi_atual <= float(rsi_maximo):
            condicao = "🟢 Suporte MM200" if preco_atual >= mm200_atual else "🔴 Resistência MM200"
            if preco_atual >= mm200_atual and rsi_atual <= 40:
                diag = "🎯 Compra Forte (MM200 + RSI)"
            elif preco_atual >= mm200_atual:
                diag = "✅ Tendência de Alta (Acima MM200)"
            else:
                diag = "⚠️ Abaixo da MM200"

            ticker_limpo = str(ticker).replace(".SA", "")
            resultados.append({
                "Ticker": ticker_limpo,
                "Preço Atual": round(preco_atual, 2),
                "Gráfico": gerar_link_tradingview(ticker),
                "MM200 Semanal": round(mm200_atual, 2),
                "Distância (%)": f"{distancia_pct:+.2f}%",
                "RSI (14)": round(rsi_atual, 1),
                "Condição MM200": condicao,
                "Diagnóstico": diag
            })

    return pd.DataFrame(resultados)
