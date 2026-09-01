import time
import pandas as pd
import yfinance as yf

def obter_dados_ativos(tickers, dias_historico=300, tamanho_lote=40):
    """
    Baixa dados em lotes fracionados para evitar timeout e bloqueios do Yahoo Finance.
    """
    if not tickers:
        return pd.DataFrame()
        
    todos_dados = []
    
    # Divide a lista de tickers em blocos de tamanho fixo
    for i in range(0, len(tickers), tamanho_lote):
        lote = tickers[i:i + tamanho_lote]
        try:
            dados_lote = yf.download(
                lote, 
                period=f"{dias_historico}d", 
                progress=False,
                threads=True
            )['Close']
            
            if isinstance(dados_lote, pd.Series):
                dados_lote = dados_lote.to_frame(name=lote[0])
                
            if not dados_lote.empty:
                todos_dados.append(dados_lote)
        except Exception as e:
            print(f"Erro ao baixar lote {i//tamanho_lote + 1}: {e}")
            
        time.sleep(0.2) # Pausa técnica para respeitar a API

    if todos_dados:
        df_consolidado = pd.concat(todos_dados, axis=1)
        # Remove colunas duplicadas se houver
        df_consolidado = df_consolidado.loc[:, ~df_consolidado.columns.duplicated()]
        return df_consolidado
    
    return pd.DataFrame()

def triagem_mm200(dados_fechamento, percentual_limite=5.0):
    resultados = []
    
    if dados_fechamento.empty:
        return pd.DataFrame(resultados)

    for ticker in dados_fechamento.columns:
        serie = dados_fechamento[ticker].dropna()
        
        if len(serie) < 200:
            continue
            
        preco_atual = serie.iloc[-1]
        mm200 = serie.rolling(window=200).mean().iloc[-1]
        
        distancia_pct = ((preco_atual - mm200) / mm200) * 100
        
        if abs(distancia_pct) <= percentual_limite:
            resultados.append({
                'Ativo': ticker,
                'Preço Atual': round(preco_atual, 2),
                'MM200': round(mm200, 2),
                'Distância (%)': round(distancia_pct, 2)
            })
            
    df_resultados = pd.DataFrame(resultados)
    if not df_resultados.empty:
        df_resultados = df_resultados.sort_values(by='Distância (%)')
        
    return df_resultados
