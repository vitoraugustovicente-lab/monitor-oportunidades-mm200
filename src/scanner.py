import base64
import json
import os
import random
import re
import socket
import ssl
import string
from concurrent.futures import ThreadPoolExecutor
import pandas as pd


def _converter_para_simbolo_tv(ticker_original):
    """Converte o ticker para o formato oficial do TradingView."""
    t = str(ticker_original).strip().upper()
    if t.endswith(".SA"):
        return f"BMFBOVESPA:{t.replace('.SA', '')}"
    elif "-USD" in t:
        return f"CRYPTO:{t.replace('-USD', 'USD')}"
    else:
        return t


def _gerar_id_sessao(prefixo):
    letras = "".join(random.choices(string.ascii_lowercase, k=12))
    return f"{prefixo}_{letras}"


def _formatar_msg_tv(funcao, parametros):
    conteudo = json.dumps({"m": funcao, "p": parametros}, separators=(",", ":"))
    return f"~m~{len(conteudo)}~m~{conteudo}"


def _buscar_velas_nominais_tv(ticker_original, qtd_velas=210):
    """
    Conecta via WebSocket nativo ao servidor de gráficos do TradingView e extrai
    as últimas 210 velas semanais NOMINAIS (adjustment='splits', sem desconto de dividendos).
    """
    simbolo = _converter_para_simbolo_tv(ticker_original)
    host = "data.tradingview.com"
    path = "/socket.io/websocket"

    try:
        sock = socket.create_connection((host, 443), timeout=10)
        contexto = ssl.create_default_context()
        ws = contexto.wrap_socket(sock, server_hostname=host)

        chave_ws = base64.b64encode(os.urandom(16)).decode("utf-8")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {chave_ws}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"Origin: https://www.tradingview.com\r\n"
            f"User-Agent: Mozilla/5.0\r\n\r\n"
        )
        ws.sendall(handshake.encode("utf-8"))

        # Lê cabeçalho HTTP 101 Switching Protocols
        resp_http = b""
        while b"\r\n\r\n" not in resp_http:
            chunk = ws.recv(1024)
            if not chunk:
                ws.close()
                return ticker_original, pd.Series(dtype=float)
            resp_http += chunk

        def enviar_frame(texto):
            dados = texto.encode("utf-8")
            tamanho = len(dados)
            mascara = os.urandom(4)
            if tamanho <= 125:
                cabecalho = bytes([0x81, 0x80 | tamanho])
            elif tamanho <= 65535:
                cabecalho = bytes([0x81, 0x80 | 126]) + tamanho.to_bytes(2, "big")
            else:
                cabecalho = bytes([0x81, 0x80 | 127]) + tamanho.to_bytes(8, "big")
            mascarado = bytes(b ^ mascara[i % 4] for i, b in enumerate(dados))
            ws.sendall(cabecalho + mascara + mascarado)

        def ler_frame():
            cab = ws.recv(2)
            if len(cab) < 2:
                return None
            opcode = cab[0] & 0x0F
            if opcode == 8:  # Close frame
                return None
            tamanho = cab[1] & 0x7F
            if tamanho == 126:
                tamanho = int.from_bytes(ws.recv(2), "big")
            elif tamanho == 127:
                tamanho = int.from_bytes(ws.recv(8), "big")
            payload = b""
            while len(payload) < tamanho:
                pedaco = ws.recv(tamanho - len(payload))
                if not pedaco:
                    break
                payload += pedaco
            return payload.decode("utf-8", errors="ignore")

        chart_session = _gerar_id_sessao("cs")
        # 'adjustment': 'splits' garante preço NOMINAL (ajusta só desdobramento, NÃO desconta dividendos)
        simbolo_config = json.dumps({"symbol": simbolo, "adjustment": "splits"})

        mensagens_iniciais = [
            _formatar_msg_tv("set_auth_token", ["unauthorized_user_token"]),
            _formatar_msg_tv("chart_create_session", [chart_session, ""]),
            _formatar_msg_tv("resolve_symbol", [chart_session, "sds_sym_1", f"={simbolo_config}"]),
            _formatar_msg_tv("create_series", [chart_session, "sds_1", "s1", "sds_sym_1", "1W", qtd_velas, ""]),
        ]

        for m in mensagens_iniciais:
            enviar_frame(m)

        fechamentos = {}
        for _ in range(25):  # Lê até receber a série completa
            frame = ler_frame()
            if frame is None:
                break

            # Responde ping (~h~) para manter conexão viva
            if "~h~" in frame:
                enviar_frame(frame)
                continue

            if '"timescale_update"' in frame or '"du"' in frame:
                partes = re.split(r"~m~\d+~m~", frame)
                for p in partes:
                    if not p.startswith("{"):
                        continue
                    try:
                        obj = json.loads(p)
                        if obj.get("m") in ("timescale_update", "du"):
                            series_data = obj["p"][1].get("sds_1", {}).get("s", [])
                            for vela in series_data:
                                v = vela.get("v", [])
                                if len(v) >= 5:
                                    ts = int(v[0])
                                    close_price = float(v[4])
                                    fechamentos[ts] = close_price
                    except Exception:
                        pass

            if '"series_completed"' in frame:
                break

        ws.close()

        if not fechamentos:
            return ticker_original, pd.Series(dtype=float)

        serie = pd.Series(fechamentos).sort_index()
        return ticker_original, serie

    except Exception:
        return ticker_original, pd.Series(dtype=float)


def obter_dados_ativos(tickers, periodo="5y", intervalo="1wk", auto_adjust=False):
    """
    Baixa em paralelo as últimas 210 velas semanais NOMINAIS do TradingView
    para todos os ativos (B3, EUA e Cripto).
    """
    if not tickers:
        return {}, {}

    dados_por_ticker = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        resultados = executor.map(_buscar_velas_nominais_tv, tickers)
        for ticker, serie in resultados:
            if not serie.empty:
                dados_por_ticker[ticker] = serie

    return dados_por_ticker, {}


def gerar_link_tradingview(ticker_original):
    simbolo = _converter_para_simbolo_tv(ticker_original)
    return f"https://br.tradingview.com/chart/?symbol={simbolo}"


def triagem_mm200(dados_fechamento, dados_volume, percentual_limite=5.0, rsi_maximo=100):
    """
    Calcula a MM200 Semanal e o RSI(14) exatamente sobre as 200 velas semanais
    nominais extraídas do gráfico do TradingView.
    """
    resultados = []

    if not isinstance(dados_fechamento, dict):
        return pd.DataFrame(resultados)

    for ticker, serie_preco in dados_fechamento.items():
        if len(serie_preco) < 200:
            continue

        # Média Móvel Simples das últimas 200 semanas nominais
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
