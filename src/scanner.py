import time
import pandas as pd
import yfinance as yf

def calcular_rsi(serie, periodos=14):
    """Calcula o Índice de Força Relativa (RSI/IFR) de 14 períodos."""
    delta = serie.diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=periodos).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=periodos).mean()
    
    rs = ganho / perda
    rsi = 100 - (100 / (1 + rs))
    return rsi

def obter_dados_ativos(tickers, dias_historico=300, tamanho_lote=40):
    """
    Baixa dados em lotes fracionados retornando Preço de Fechamento e Volume.
    """
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
                progress=False,
                threads=True
            )
            
            # Extração de Fechamento e Volume
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
    """
    Calcula MM200, distância percentual, tendência (Suporte/Resistência), RSI e Volume Médio.
    """
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
        
        # Cálculo de Distância %
        distancia_pct = ((preco_atual - mm200) / mm200) * 100
        
        # Cálculo de RSI (14)
        rsi_serie = calcular_rsi(serie_preco)
        rsi_atual = rsi_serie.iloc[-1] if not rsi_serie.empty else None
        
        # Cálculo de Volume Médio Diário (últimos 20 dias em Milhões)
        if not serie_vol.empty and len(serie_vol) >= 20:
            vol_medio_20d = (serie_vol.iloc[-20:] * serie_preco.iloc[-20:]).mean() / 1_000_000
        else:
            vol_medio_20d = 0.0
        
        # Aplica os Filtros (Margem da MM200 e Filtro de RSI Opcional)
        if abs(distancia_pct) <= percentual_limite:
            if rsi_atual is not None and rsi_atual <= rsi_maximo:
                
                condicao = "🟢 Suporte (Acima)" if preco_atual >= mm200 else "🔴 Resistência (Abaixo)"
                
                # Classificação rápida do RSI
                if rsi_atual <= 30:
                    status_rsi = f"{round(rsi_atual, 1)} (Sobrevendido 🔥)"
                elif rsi_atual >= 70:
                    status_rsi = f"{round(rsi_atual, 1)} (Sobrecomprado ⚠️)"
                else:
                    status_rsi = f"{round(rsi_atual, 1)}"
                
                resultados.append({
                    'Ativo': ticker,
                    'Preço Atual': round(preco_atual, 2),
                    'MM200': round(mm200, 2),
                    'Distância (%)': round(distancia_pct, 2),
                    'Condição': condicao,
                    'RSI (14)': status_rsi,
                    'Vol Médio (20d Mi)': round(vol_medio_20d, 2)
                })
            
    df_resultados = pd.DataFrame(resultados)
    if not df_resultados.empty:
        df_resultados['Dist_Abs'] = df_resultados['Distância (%)'].abs()
        df_resultados = df_resultados.sort_values(by='Dist_Abs').drop(columns=['Dist_Abs'])
        
    return df_resultados
