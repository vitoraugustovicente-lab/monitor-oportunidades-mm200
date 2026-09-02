import time
import pandas as pd
import yfinance as yf

def gerar_link_tradingview(ticker):
    """Gera a URL direta do gráfico no TradingView com base no mercado do ativo."""
    if ticker.endswith(".SA"):
        codigo = ticker.replace(".SA", "")
        symbol = f"BMFBOVESPA:{codigo}"
    elif ticker.endswith("-USD"):
        codigo = ticker.replace("-USD", "USD")
        symbol = f"BINANCE:{codigo}T"
    else:
        symbol = ticker
        
    return f"https://br.tradingview.com/chart/?symbol={symbol}"

def calcular_rsi(serie, periodos=14):
    """Calcula o Índice de Força Relativa (RSI/IFR) de 14 períodos."""
    delta = serie.diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=periodos).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=periodos).mean()
    
    rs = ganho / perda
    rsi = 100 - (100 / (1 + rs))
    return rsi

def classificar_analise_combinada(preco_atual, mm200, rsi_atual):
    """Gera o diagnóstico operacional combinando MM200 e RSI."""
    esta_acima_mm = preco_atual >= mm200
    
    if rsi_atual is None:
        return "⚪ Sem Dados RSI"
        
    if esta_acima_mm and rsi_atual <= 35:
        return "🎯 Compra Forte (Suporte + Sobrevendido)"
    elif esta_acima_mm and rsi_atual < 50:
        return "🟢 Neutro Autêntico (Suporte em Teste)"
    elif esta_acima_mm and rsi_atual >= 70:
        return "⚠️ Alerta de Correção (Esticado em Alta)"
    elif not esta_acima_mm and rsi_atual >= 65:
        return "🔴 Venda / Risco (Resistência + Sobrecomprado)"
    elif not esta_acima_mm and rsi_atual <= 30:
        return "⚡ Possível Repique (Abaixo da MM200)"
    else:
        return "🟡 Acompanhar / Neutro"

def obter_dados_ativos(tickers, dias_historico=365, tamanho_lote=40):
    """Baixa dados em lotes com auto_adjust=True para alinhar proventos com TradingView."""
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()
        
    todos_fechamentos = []
    todos_volumes = []
    
    for i in range(0, len(tickers), tamanho_lote):
        lote = tickers[i:i + tamanho_lote]
        try:
            dados_lote = yf.download(
                lote, 
                period=f"{dias_historico}d", 
                auto_adjust=True,
                progress=False,
                threads=True
            )
            
            if len(lote) == 1:
                df_close = dados_lote['Close'].to_frame(name=lote[0])
                df_vol = dados_lote['Volume'].to_frame(name=lote[0])
            else:
                df_close = dados_lote['Close']
                df_vol = dados_lote['Volume']
                
            if not df_close.empty:
                todos_fechamentos.append(df_close)
                todos_volumes.append(df_vol)
        except Exception as e:
            print(f"Erro ao baixar lote {i//tamanho_lote + 1}: {e}")
            
        time.sleep(0.2)

    if todos_fechamentos:
        df_close_consolidado = pd.concat(todos_fechamentos, axis=1)
        df_vol_consolidado = pd.concat(todos_volumes, axis=1)
        
        df_close_consolidado = df_close_consolidado.loc[:, ~df_close_consolidado.columns.duplicated()]
        df_vol_consolidado = df_vol_consolidado.loc[:, ~df_vol_consolidado.columns.duplicated()]
        
        return df_close_consolidado, df_vol_consolidado
    
    return pd.DataFrame(), pd.DataFrame()

def triagem_mm200(dados_fechamento, dados_volume, percentual_limite=5.0, rsi_maximo=100):
    """Calcula indicadores, análise combinada e gera links do TradingView."""
    resultados = []
    
    if dados_fechamento.empty:
        return pd.DataFrame(resultados)

    for ticker in dados_fechamento.columns:
        serie_preco = dados_fechamento[ticker].dropna()
        serie_vol = dados_volume[ticker].dropna() if ticker in dados_volume.columns else pd.Series()
        
        if len(serie_preco) < 200:
            continue
            
        preco_atual = serie_preco.iloc[-1]
        mm200 = serie_preco.rolling(window=200).mean().iloc[-1]
        
        distancia_pct = ((preco_atual - mm200) / mm200) * 100
        
        rsi_serie = calcular_rsi(serie_preco)
        rsi_atual = rsi_serie.iloc[-1] if not rsi_serie.empty else None
        
        if not serie_vol.empty and len(serie_vol) >= 20:
            vol_medio_20d = (serie_vol.iloc[-20:] * serie_preco.iloc[-20:]).mean() / 1_000_000
        else:
            vol_medio_20d = 0.0
        
        if abs(distancia_pct) <= percentual_limite:
            if rsi_atual is not None and rsi_atual <= rsi_maximo:
                
                condicao = "🟢 Suporte (Acima)" if preco_atual >= mm200 else "🔴 Resistência (Abaixo)"
                
                # Análise Combinada
                diagnostico = classificar_analise_combinada(preco_atual, mm200, rsi_atual)
                
                if rsi_atual <= 30:
                    status_rsi = f"{round(rsi_atual, 1)} (Sobrevendido 🔥)"
                elif rsi_atual >= 70:
                    status_rsi = f"{round(rsi_atual, 1)} (Sobrecomprado ⚠️)"
                else:
                    status_rsi = f"{round(rsi_atual, 1)}"
                
                url_tradingview = gerar_link_tradingview(ticker)
                
                resultados.append({
                    'Ativo': ticker,
                    'Gráfico': url_tradingview,
                    'Diagnóstico': diagnostico,
                    'Preço Atual': round(preco_atual, 2),
                    'MM200': round(mm200, 2),
                    'Distância (%)': round(distancia_pct, 2),
                    'Condição MM200': condicao,
                    'RSI (14)': status_rsi,
                    'Vol Médio (20d Mi)': round(vol_medio_20d, 2)
                })
            
    df_resultados = pd.DataFrame(resultados)
    if not df_resultados.empty:
        df_resultados['Dist_Abs'] = df_resultados['Distância (%)'].abs()
        df_resultados = df_resultados.sort_values(by='Dist_Abs').drop(columns=['Dist_Abs'])
        
    return df_resultados
