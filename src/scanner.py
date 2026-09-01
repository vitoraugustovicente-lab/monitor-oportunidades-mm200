import pandas as pd
import yfinance as yf

def obter_dados_ativos(tickers, dias_historico=300):
    """
    Baixa os dados históricos de fechamento para uma lista de tickers usando o yfinance.
    """
    try:
        dados = yf.download(
            tickers, 
            period=f"{dias_historico}d", 
            progress=False
        )['Close']
        return dados
    except Exception as e:
        print(f"Erro ao baixar dados: {e}")
        return pd.DataFrame()

def triagem_mm200(dados_fechamento, percentual_limite=5.0):
    """
    Calcula a Média Móvel de 200 períodos e identifica os ativos que estão 
    próximos da MM200 dentro do percentual limite estipulado.
    """
    resultados = []
    
    if dados_fechamento.empty:
        return pd.DataFrame(resultados)

    for ticker in dados_fechamento.columns:
        serie = dados_fechamento[ticker].dropna()
        
        # Verifica se há dados suficientes para calcular a MM200
        if len(serie) < 200:
            continue
            
        preco_atual = serie.iloc[-1]
        mm200 = serie.rolling(window=200).mean().iloc[-1]
        
        # Calcula a distância percentual em relação à MM200
        distancia_pct = ((preco_atual - mm200) / mm200) * 100
        
        # Filtra ativos dentro da margem estipulada (ex: +/- 5%)
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
