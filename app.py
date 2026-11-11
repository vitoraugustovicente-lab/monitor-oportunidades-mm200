if st.button("🚀 Iniciar Varredura de Mercado (Semanal)"):
    with st.spinner("Analisando cotações semanais, aplicando MM200 e RSI..."):
        # Passa os parâmetros de 5 anos e barras semanais (1wk)
        dados_fechamento, dados_volume = obter_dados_ativos(tickers_lista, periodo="5y", intervalo="1wk")
        
        if not dados_fechamento.empty:
            df_resultado = triagem_mm200(
                dados_fechamento, 
                dados_volume, 
                percentual_limite=margem_limite,
                rsi_maximo=rsi_filtro
            )
            # ... mantém o resto da exibição da tabela e exportação
