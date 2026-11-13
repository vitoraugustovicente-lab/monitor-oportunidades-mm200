import requests
import pandas as pd


def _converter_para_simbolo_tv(ticker_original):
    """
    Converte os tickers do settings.py para os formatos oficiais do TradingView
    cobrindo B3, EUA (NASDAQ/NYSE/AMEX) e Criptomoedas.
    """
    t = str(ticker_original).strip().upper()
    if t.endswith(".SA"):
        return [f"BMFBOVESPA:{t.replace('.SA', '')}"]
    elif "-USD" in t:
        base = t.replace("-USD", "")
        return [f"CRYPTO:{base}USD", f"BINANCE:{base}USDT", f"COINBASE:{base}USD"]
    else:
        return [f"NASDAQ:{t}", f"NYSE:{t}", f"AMEX:{t}"]


def obter_dados_ativos(tickers, periodo="5y", intervalo="1wk", auto_adjust=False):
    """
    Consulta exclusivamente o endpoint do TradingView Scanner em lote.
    Retorna preço atual, SMA200 Semanal e RSI(14) Semanal para todos os mercados.
    """
    if not tickers:
        return {}, {}

    mapa_simbolo_para_original = {}
    todos_simbolos_tv = []

    for t in tickers:
        simbolos = _converter_para_simbolo_tv(t)
        for s in simbolos:
            mapa_simbolo_para_original[s] = t
            todos_simbolos_tv.append(s)

    url = "https://scanner.tradingview.com/global/scan"
    payload = {
        "symbols": {
            "tickers": todos_simbolos_tv,
            "query": {"types": []}
        },
        "columns": [
            "close",        # Preço atual
            "SMA200|1W",    # Média Móvel Simples de 200 semanas
            "RSI|1W"        # RSI 14 no gráfico semanal
        ]
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    dados_por_ticker = {}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            resultados_api = resp.json().get("data", [])
            for item in resultados_api:
                simbolo_tv = item.get("s")
                valores = item.get("d", [])
                if len(valores) >= 3 and valores[0] is not None and valores[1] is not None:
                    ticker_orig = mapa_simbolo_para_original.get(simbolo_tv)
                    if ticker_orig and ticker_orig not in dados_por_ticker:
                        dados_por_ticker[ticker_orig] = {
                            "simbolo_tv": simbolo_tv,
                            "preco": float(valores[0]),
                            "mm200": float(valores[1]),
                            "rsi": float(valores[2]) if valores[2] is not None else 50.0
                        }
    except Exception as e:
        print(f"Erro ao consultar TradingView Scanner: {e}")

    return dados_por_ticker, {}


def gerar_link_tradingview(simbolo_tv_ou_ticker):
    """
    Gera o link direto do gráfico no TradingView com o prefixo exato da bolsa.
    """
    s = str(simbolo_tv_ou_ticker).strip().upper()
    if ":" in s:
        simbolo = s
    elif s.endswith(".SA"):
        simbolo = f"BMFBOVESPA:{s.replace('.SA', '')}"
    elif "-USD" in s:
        simbolo = f"CRYPTO:{s.replace('-USD', 'USD')}"
    else:
        simbolo = s
    return f"https://br.tradingview.com/chart/?symbol={simbolo}"


def triagem_mm200(dados_ativos, dados_volume, percentual_limite=5.0, rsi_maximo=100):
    """
    Filtra os ativos com base nos dados retornados pelo TradingView Scanner.
    """
    resultados = []

    if not isinstance(dados_ativos, dict):
        return pd.DataFrame(resultados)

    for ticker, info in dados_ativos.items():
        preco_atual = info.get("preco")
        mm200_atual = info.get("mm200")
        rsi_atual = info.get("rsi", 50.0)
        simbolo_tv = info.get("simbolo_tv", ticker)

        if not preco_atual or not mm200_atual or mm200_atual <= 0:
            continue

        distancia_pct = ((preco_atual - mm200_atual) / mm200_atual) * 100

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
                "Gráfico": gerar_link_tradingview(simbolo_tv),
                "MM200 Semanal": round(mm200_atual, 2),
                "Distância (%)": f"{distancia_pct:+.2f}%",
                "RSI (14)": round(rsi_atual, 1),
                "Condição MM200": condicao,
                "Diagnóstico": diag
            })

    return pd.DataFrame(resultados)
