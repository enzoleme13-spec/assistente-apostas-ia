import streamlit as st
import requests
import openai
import datetime

# =================== CONFIGURAÇÕES FIXAS ===================
OPENAI_API_KEY = "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"
API_FOOTBALL_KEY = "2675014453msh50a550a176f7fb3p1714fbjsnac60012"
API_FOOTBALL_HOST = "api-football-v1.p.rapidapi.com"

# =================== CONFIG OPENAI ===================
openai.api_key = OPENAI_API_KEY

# =================== FUNÇÕES AUXILIARES ===================
def buscar_jogos_do_dia(time_nome):
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"season": "2024", "date": hoje}
    headers = {
        "X-RapidAPI-Key": API_FOOTBALL_KEY,
        "X-RapidAPI-Host": API_FOOTBALL_HOST
    }
    response = requests.get(url, headers=headers, params=params)
    
    try:
        res_json = response.json()
    except Exception as e:
        st.error(f"Erro ao interpretar resposta da API: {e}")
        st.stop()

    if "response" not in res_json:
        st.error("❌ A API-Football não retornou dados. Verifique se sua chave está correta e se o plano gratuito não foi ultrapassado.")
        st.stop()

    jogos = res_json["response"]

    for jogo in jogos:
        time_casa = jogo["teams"]["home"]["name"].lower()
        time_fora = jogo["teams"]["away"]["name"].lower()
        if time_nome.lower() in time_casa or time_nome.lower() in time_fora:
            return jogo
    return None


def buscar_odds(fixture_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    params = {"fixture": fixture_id, "bookmaker": "6", "bet": "1"}
    headers = {
        "X-RapidAPI-Key": API_FOOTBALL_KEY,
        "X-RapidAPI-Host": API_FOOTBALL_HOST
    }
    response = requests.get(url, headers=headers, params=params)
    odds = {}
    try:
        valores = response.json()["response"][0]["bookmakers"][0]["bets"][0]["values"]
        for v in valores:
            odds[v["value"]] = float(v["odd"])
    except:
        odds = {"Home": None, "Draw": None, "Away": None}
    return odds

def buscar_estatisticas(time_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams/statistics"
    params = {"season": "2024", "league": "71", "team": time_id}
    headers = {
        "X-RapidAPI-Key": API_FOOTBALL_KEY,
        "X-RapidAPI-Host": API_FOOTBALL_HOST
    }
    response = requests.get(url, headers=headers, params=params)
    dados = response.json()["response"]
    media_gols = float(dados["goals"]["for"]["average"]["total"])
    return media_gols

def calcular_odd_justa(prob):
    if prob > 0:
        return round(1 / prob, 2)
    return None

def gerar_resposta_ia(pergunta, jogo, odds, odd_justa, valor_esperado):
    prompt = f"""
    Usuário perguntou: {pergunta}
    
    Jogo: {jogo['teams']['home']['name']} x {jogo['teams']['away']['name']}
    Odds atuais (1X2): Casa: {odds.get('Home')}, Empate: {odds.get('Draw')}, Fora: {odds.get('Away')}
    Odd justa estimada: {odd_justa}
    Valor esperado: {valor_esperado}
    
    Responda como um consultor de apostas esportivas: a aposta tem valor? Explique em linguagem natural, clara e objetiva.
    """
    resposta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return resposta.choices[0].message.content

# =================== INTERFACE STREAMLIT ===================
st.set_page_config(page_title="Assistente de Apostas IA", layout="centered")
st.title("🤖 Assistente de Apostas com IA")

pergunta = st.text_input("Digite sua pergunta sobre apostas:", placeholder="Ex: Vale apostar no Flamengo hoje?")

if pergunta:
    with st.spinner("Analisando jogo e calculando probabilidades..."):
        # Extrair time da pergunta (bem simples para MVP)
        palavras = pergunta.lower().split()
        times_citados = [p for p in palavras if len(p) > 3]

        jogo_encontrado = None
        for t in times_citados:
            jogo_encontrado = buscar_jogos_do_dia(t)
            if jogo_encontrado:
                break

        if not jogo_encontrado:
            st.error("Nenhum jogo encontrado para hoje com os times citados.")
        else:
            fixture_id = jogo_encontrado["fixture"]["id"]
            odds = buscar_odds(fixture_id)

            time_casa = jogo_encontrado["teams"]["home"]
            time_fora = jogo_encontrado["teams"]["away"]

            gols_casa = buscar_estatisticas(time_casa["id"])
            gols_fora = buscar_estatisticas(time_fora["id"])

            # Estimar probabilidade simplificada com base na média de gols
            prob_casa = gols_casa / (gols_casa + gols_fora)
            odd_justa = calcular_odd_justa(prob_casa)

            odd_real = odds.get("Home")
            if odd_justa and odd_real:
                valor_esperado = round((prob_casa * odd_real) - 1, 2)
            else:
                valor_esperado = "N/D"

            resposta = gerar_resposta_ia(pergunta, jogo_encontrado, odds, odd_justa, valor_esperado)
            st.success(resposta)
