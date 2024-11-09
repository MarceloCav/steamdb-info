import streamlit as st
import pandas as pd
import plotly.express as px
from google.oauth2 import service_account
from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Análise de Promoções Steam", layout="wide")
st.title("Dashboard de Análise de Promoções de Jogos da Steam")

credentials_json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
dataset_id = os.getenv("DATASET_ID")
table_id = os.getenv("TABLE_ID")

credentials = service_account.Credentials.from_service_account_file(credentials_json_path)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

query = f"""
    SELECT Name, Discount, Price, Rating, Release_Date, Ends, Starts, Game_Link, Image_Link, ID
    FROM `{dataset_id}.{table_id}`
"""

@st.cache_data
def load_data():
    return client.query(query).to_dataframe()

df = load_data()

df['Discount'] = df['Discount'].str.replace('%', '').replace('', '0').astype(float)
df['Rating'] = df['Rating'].str.replace('%', '').replace('', '0').astype(float)
df['Price'] = df['Price'].str.replace('₪', '').replace('', '0').astype(float)
df['Release_Date'] = pd.to_datetime(df['Release_Date'], errors='coerce')
df['Ends'] = pd.to_datetime(df['Ends'], errors='coerce')
df['Starts'] = pd.to_datetime(df['Starts'], errors='coerce')


# 1. Distribuição de Preços dos Jogos em Promoção
st.subheader("Distribuição de Preços dos Jogos em Promoção")
fig_price_dist = px.histogram(df, x="Price", nbins=100, title="Distribuição de Preços dos Jogos")
st.plotly_chart(fig_price_dist, use_container_width=True)

# 2. Top Jogos Mais Caros em Promoção
st.subheader("Top 10 Jogos Mais Caros em Promoção")
top_priced_games = df.nlargest(10, 'Price')[['Name', 'Price', 'Rating']]
st.dataframe(top_priced_games)

# 3. Jogos Mais Baratos em Promoção
st.subheader("Top 10 Jogos Mais Baratos em Promoção")
bottom_priced_games = df.nsmallest(10, 'Price')[['Name', 'Price', 'Rating']]
st.dataframe(bottom_priced_games)

# 4. Jogos Mais Bem Avaliados com Preço Abaixo de 20 Reais
st.subheader("Top Jogos com Avaliação Alta (Preço <= 20)")
high_rating_low_price = df[(df['Price'] <= 20) & (df['Rating'] > 0)].nlargest(10, 'Rating')[['Name', 'Price', 'Rating']]
st.dataframe(high_rating_low_price)

# 5. Relação entre Preço e Avaliação
st.subheader("Relação entre Preço e Avaliação")
fig_price_rating = px.scatter(df, x="Price", y="Rating", hover_name="Name", title="Preço x Avaliação dos Jogos")
st.plotly_chart(fig_price_rating, use_container_width=True)

# 6. Promoções ao Longo do Tempo
st.subheader("Promoções ao Longo do Tempo")
df['Promo_Duration'] = (df['Ends'] - df['Starts']).dt.days
df['Promo_Start_Month'] = df['Starts'].dt.to_period('M').dt.to_timestamp()
monthly_promotions = df.groupby('Promo_Start_Month').size().reset_index(name='Promo_Count')
fig_promo_time = px.bar(monthly_promotions, x="Promo_Start_Month", y="Promo_Count",
                        title="Quantidade de Promoções Iniciadas por Mês")
st.plotly_chart(fig_promo_time, use_container_width=True)

st.write("**Observações e Insights**:")
st.write("- A análise agora inclui os jogos mais baratos em promoção, oferecendo insights sobre títulos de baixo custo.")
st.write("- Jogos bem avaliados com preço abaixo de 20 reais destacam oportunidades de boas promoções para consumidores.")
st.write("- Relação entre preço e avaliação mostra se os jogos mais caros também recebem boas avaliações.")
st.write("- Quantidade de promoções ao longo do tempo ajuda a identificar padrões de sazonalidade.")

