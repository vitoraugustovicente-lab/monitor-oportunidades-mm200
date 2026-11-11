import pandas as pd
import numpy as np
import yfinance as yf

def obter_dados_ativos(tickers, periodo="5y", intervalo="1wk"):
    """
    Baixa dados com histórico longo (5 anos) no tempo gráfico semanal (1wk)
    para garantir 200 barras para a MM200.
    """
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()
        
    try:
        dados = yf.download(tickers, period=periodo, interval=intervalo, progress=False)
        
        if dados.empty:
            return pd.DataFrame(), pd.DataFrame()
            
        if isinstance(dados.columns, pd.MultiIndex):
            fechamento = dados['Close']
            volume = dados['Volume']
        else:
            fechamento = dados[['Close']]
            volume = dados[['Volume']]
            
        return fechamento, volume
    except Exception as e:
        print(f"Erro ao baixar dados: {e}")
        return pd.DataFrame(), pd.DataFrame()


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
    Calcula a MM200 Semanal, RSI de 14 períodos e gera diagnósticos com link do TradingView na 3ª coluna.
    """
    resultados = []
    
    # Trata caso a busca tenha retornado apenas um ativo (Series em vez de DataFrame)
    if isinstance(dados_fechamento, pd.Series):
        dados_fechamento = dados_fechamento.to_frame()
        
    for ticker in dados_fechamento.columns:
        serie_preco = dados_fechamento[ticker].dropna()
        
        # Precisa ter no mínimo 200 semanas de histórico
        if len(serie_preco) < 200:
            continue
            
        # 1. Cálculo da MM200 Semanal
        mm200_serie = serie_preco.rolling(window=200).mean()
        
        preco_atual = float(serie_preco.iloc[-1])
        mm200_atual = float(mm200_serie.iloc[-1])
        
        if pd.isna(mm200_atual):
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
            
            # Ordem exata das colunas: 1. Ticker | 2. Preço Atual | 3. Gráfico (Botão TradingView)
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
