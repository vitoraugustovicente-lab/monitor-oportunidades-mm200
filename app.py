import datetime
import pandas as pd
import streamlit as st
from config.settings import INDICES
from src.scanner import obter_dados_ativos, triagem_mm200

def processar_mercado(mercado, tickers, percentual_limite=5.0, data_alvo=None):
    """
    Função adaptada para aceitar o mercado e filtrar os dados até a data_alvo selecionada.
    """
    # 1. Baixa os dados históricos (busca cerca de 350 dias para garantir o cálculo da MM200)
    dados_ativos = obter_dados_ativos(tickers, periodo="350d")
    
    # 2. Se o usuário escolheu uma data alvo específica no calendário, filtramos os dados até ela
    if data_alvo is not None and dados_ativos:
        dados_filtrados = {}
        # Converte a data alvo para o formato datetime do pandas para comparação segura
        limite_data = pd.to_datetime(data_alvo).tz_localize(None)
        
        for ticker, serie_preco in dados_ativos.items():
            # Garante que os índices de datas não tenham fuso horário para comparar diretamente
            serie_sem_tz = serie_preco.copy()
            serie_sem_tz.index = serie_sem_tz.index.tz_localize(None)
            
            # Corta a série histórica para conter apenas dados até a data selecionada
            serie_cortada = serie_sem_tz[serie_sem_tz.index <= limite_data]
            
            if len(serie_cortada) >= 200:
                dados_filtrados[ticker] = serie_cortada
        
        dados_ativos = dados_filtrados

    # 3. Executa a triagem com a lista de dados consolidada
    df_resultado = triagem_mm200(dados_ativos, percentual_limite)
    return df_resultado

st.set_page_config(
    page_title="Monitor de Oportunidades - MM200",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Monitor de Oportunidades: Média Móvel de 200 Períodos")

# --- BARRA LATERAL ---
st.sidebar.header("Configurações do Filtro")

limite_proximidade = st.sidebar.slider(
    "Distância máxima da MM200 (%)",
    min_value=1.0,
    max_value=15.0,
    value=3.0,
    step=0.5,
    help="Filtra ativos que estão dentro desta faixa percentual acima ou abaixo da MM200."
)

data_selecionada = st.sidebar.date_input(
    "Escolha a data de análise:",
    value=datetime.date(2026, 7, 10),  # Sexta-feira útil de referência
    max_value=datetime.date.today(),
)

st.sidebar.subheader("Mercados")
analisar_ibov = st.sidebar.checkbox("Ibovespa Completo (Brasil)", value=True)
analisar_nasdaq = st.sidebar.checkbox("Nasdaq 100 Completo (EUA)", value=True)
analisar_dow = st.sidebar.checkbox("Dow Jones Completo (EUA)", value=True)

disparar_scan = st.sidebar.button("🔍 Executar Triagem", use_container_width=True)

# --- LISTAS OFICIAIS COMPLETAS (PORTFÓLIO DE COBERTURA INTEGRAL) ---
carteira_completa = {
    "Ibovespa": [
        "ALOS3.SA", "ALPA4.SA", "ABEV3.SA", "ARZZ3.SA", "ASAI3.SA", "AZUL4.SA", "B3SA3.SA", 
        "BBAS3.SA", "BBDC3.SA", "BBDC4.SA", "BBSE3.SA", "BEEF3.SA", "BPAC11.SA", "BRAP4.SA", 
        "BRFS3.SA", "BRKM5.SA", "CCRO3.SA", "CIEL3.SA", "CMIG4.SA", "COGN3.SA", "CPFE3.SA", 
        "CPLE6.SA", "CRFB3.SA", "CSAN3.SA", "CSNA3.SA", "CYRE3.SA", "DXCO3.SA", "EGIE3.SA", 
        "ELET3.SA", "ELET6.SA", "EMBR3.SA", "ENEV3.SA", "ENGI11.SA", "EQTL3.SA", "EZTC3.SA", 
        "FLRY3.SA", "GGBR4.SA", "GOAU4.SA", "GOLL4.SA", "HAPV3.SA", "HYPE3.SA", "IGTI11.SA", 
        "IRBR3.SA", "ITSA4.SA", "ITUB4.SA", "JBSS3.SA", "KLBN11.SA", "LREN3.SA", "LWSA3.SA", 
        "MGLU3.SA", "MRFG3.SA", "MRVE3.SA", "MULT3.SA", "NTCO3.SA", "PCAR3.SA", "PETR3.SA", 
        "PETR4.SA", "RECV3.SA", "PRIO3.SA", "RADL3.SA", "RAIZ4.SA", "RAIL3.SA", "RENT3.SA", 
        "SANB11.SA", "SBSP3.SA", "SLCE3.SA", "SMTO3.SA", "SOMA3.SA", "SUZB3.SA", "TAEE11.SA", 
        "TIMS3.SA", "TOTS3.SA", "TRPL4.SA", "UGPA3.SA", "USIM5.SA", "VALE3.SA", "VAMO3.SA", 
        "VBBR3.SA", "VIVT3.SA", "WEGE3.SA", "YDUQ3.SA"
    ],
    "Nasdaq 100": [
        "AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", 
        "COST", "ADBE", "CSCO", "NFLX", "AMD", "QCOM", "TMUS", "INTC", "TXN", "AMGN", 
        "HON", "INTU", "AMAT", "BKNG", "SBUX", "MDLZ", "ISRG", "GILD", "LRCX", "ADP", 
        "REGN", "VRTX", "MU", "PANW", "SNPS", "CDNS", "KLAC", "CSX", "MAR", "MNST", 
        "ORLY", "CTAS", "ASML", "ADI", "NXPI", "PCAR", "KDP", "PAYX", "LULU", "ROST", 
        "FAST", "ODFL", "IDXX", "VRSK", "AEP", "CHTR", "CPRT", "CTSH", "EA", "EXC", 
        "GEHC", "KHC", "MCHP", "WBD", "WDAY", "TEAM", "DDOG", "BILI", "JD", "PDD", 
        "MELI", "ANSS", "ALGN", "AWK", "BGEN", "BMRN", "CDW", "DLTR", "DXCM", "EBAY", 
        "ENPH", "FTNT", "GRMN", "ILMN", "INCY", "JBHT", "KEYS", "MTCH", "NTES", "OKTA", 
        "SWKS", "VRSN", "WYNN", "ZS", "CEG", "MDB", "SPLK", "FANG"
    ],
    "Dow Jones": [
        "UNH", "GS", "HD", "MSFT", "CRM", "MCD", "CAT", "V", "AMGN", "AXP", "BA", "PG",
        "JNJ", "WMT", "DIS", "CVX", "MRK", "AAPL", "NKE", "IBM", "TRV", "HON", "KO",
        "CSCO", "INTC", "MMM", "AMZN", "VZ", "WBA", "DOW"
    ]
}

# --- EXECUÇÃO ---
if disparar_scan:
    with st.spinner("Buscando dados históricos e mapeando Médias de 200 períodos..."):
        
        # Sobrescreve dinamicamente o parâmetro do settings com a escolha da tela
        import config.settings as settings
        settings.LIMITE_PROXIMIDADE_PCT = limite_proximidade

        # --- PAINEL DE DIAGNÓSTICO ---
        st.subheader("🛠️ Monitoramento Ativo (Cobertura de Mercado)")
        col_db1, col_db2, col_db3 = st.columns(3)
        col_db1.metric("Ações no Ibovespa", len(carteira_completa['Ibovespa']))
        col_db2.metric("Ações na Nasdaq 100", len(carteira_completa['Nasdaq 100']))
        col_db3.metric("Ações no Dow Jones", len(carteira_completa['Dow Jones']))
        st.write("---")

        mercados_filtrados = {}
        if analisar_ibov: mercados_filtrados["Ibovespa"] = carteira_completa.get("Ibovespa")
        if analisar_nasdaq: mercados_filtrados["Nasdaq 100"] = carteira_completa.get("Nasdaq 100")
        if analisar_dow: mercados_filtrados["Dow Jones"] = carteira_completa.get("Dow Jones")

        lista_dfs = []

        # 2. Processa as ações de cada mercado
        for mercado, tickers in mercados_filtrados.items():
            df_mercado = processar_mercado(mercado, tickers, percentual_limite=limite_proximidade, data_alvo=data_selecionada)
            if df_mercado is not None and not df_mercado.empty:
                df_mercado["Mercado"] = mercado
                lista_dfs.append(df_mercado)

        # 3. Processa os Índices Cheios do config.settings
        df_indices = processar_mercado("ÍNDICES", list(INDICES.values()), percentual_limite=limite_proximidade, data_alvo=data_selecionada)
        if df_indices is not None and not df_indices.empty:
            df_indices["Mercado"] = "Índice"
            lista_dfs.append(df_indices)

        # Consolida todos os resultados obtidos
        if lista_dfs:
            df_final = pd.concat(lista_dfs, ignore_index=True)
        else:
            df_final = pd.DataFrame()

        # --- EXIBIÇÃO ---
        st.subheader(f"📋 Resultados Encontrados para: {data_selecionada.strftime('%d/%m/%Y')}")

        if not df_final.empty and "Distância %" in df_final.columns:
            # Ordena pela proximidade exata da MM200 (independente se suporte ou resistência)
            df_final["Abs_Dist"] = df_final["Distância %"].abs()
            df_final = df_final.sort_values(by="Abs_Dist")
            
            # Remove a coluna temporária de ordenação
            df_exibicao = df_final.drop(columns=["Abs_Dist"])

            # Como removemos o "Contexto" por simplificação do scanner, criamos uma classificação visual simples
            # Se preço acima da média -> Suporte. Se abaixo -> Resistência.
            df_exibicao["Contexto"] = df_exibicao["Distância %"].apply(
                lambda x: "🟢 Suporte (Preço Acima)" if x >= 0 else "🔴 Resistência (Preço Abaixo)"
            )

            total_ativos = len(df_exibicao)
            suportes = len(df_exibicao[df_exibicao["Distância %"] >= 0])
            resistencias = total_ativos - suportes

            col1, col2, col3 = st.columns(3)
            col1.metric("Oportunidades Encontradas", total_ativos)
            col2.metric("Suportes", suportes)
            col3.metric("Resistências", resistencias)

            # Reorganiza as colunas para ficar elegante na tela
            colunas_ordenadas = ["Ativo", "Mercado", "Preço Atual", "MM200", "Distância %", "Contexto"]
            colunas_existentes = [col for col in colunas_ordenadas if col in df_exibicao.columns]
            df_exibicao = df_exibicao[colunas_existentes]

            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.warning(
                f"⚠️ Nenhum ativo dos índices ficou a menos de {limite_proximidade}% da MM200 em {data_selecionada.strftime('%d/%m/%Y')}. "
                "Tente aumentar o limite na barra lateral ou selecione outra data."
            )
else:
    st.info("Ajuste os parâmetros na barra lateral esquerda e clique em **Executar Triagem**.")