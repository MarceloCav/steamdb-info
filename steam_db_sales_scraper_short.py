import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
import random
import logging
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
PROJECT_ID = os.getenv('PROJECT_ID')
DATASET_ID = os.getenv('DATASET_ID')
TABLE_ID = os.getenv('TABLE_ID')
SCRAPEDO_API_KEY = os.getenv('SCRAPEDO_API_KEY')


credentials = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS)
client = bigquery.Client(credentials=credentials, project=PROJECT_ID)


def atualizar_cookies(url="https://steamdb.info/cloudflare"):
    logging.info("Iniciando atualização de cookies.")
    tentativas = 0
    max_tentativas = 5
    cookies_necessarios = {}

    while tentativas < max_tentativas:
        logging.info(f"Tentativa {tentativas + 1} de {max_tentativas}.")
        options = ChromiumOptions()
        options.incognito(True)
        driver = ChromiumPage(options)
        
        try:
            driver.get(url)
            time.sleep(random.randint(5, 10))
            cf_bypasser = CloudflareBypasser(driver)
            cf_bypasser.click_verification_button()
            time.sleep(3)

            cookies = driver.cookies()
            logging.info(f"Cookies coletados: {cookies}")
            for cookie in cookies:
                if cookie['name'] == 'cf_clearance':
                    cookies_necessarios['cf_clearance'] = cookie['value']
                elif cookie['name'] == '__cf_bm':
                    cookies_necessarios['__cf_bm'] = cookie['value']

            if 'cf_clearance' in cookies_necessarios and '__cf_bm' in cookies_necessarios:
                #logging.info(f"Cookies necessários obtidos: {cookies_necessarios}")
                return cookies_necessarios

        except Exception as e:
            logging.error(f"Erro durante a tentativa de obter cookies: {e}")

        finally:
            driver.close()

        tentativas += 1
        logging.warning(f"Tentativa {tentativas}: Cookie cf_clearance não encontrado, tentando novamente...")

    logging.error("Não foi possível obter o cookie cf_clearance após 5 tentativas.")
    raise Exception("Não foi possível obter o cookie cf_clearance após 5 tentativas.")

def obter_dados_steam_sales():
    url = "https://steamdb.info/sales/"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "priority": "u=0, i",
        "sec-ch-ua": "\"Google Chrome\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
        "sec-ch-ua-arch": "\"x86\"",
        "sec-ch-ua-bitness": "\"64\"",
        "sec-ch-ua-full-version": "\"129.0.6668.100\"",
        "sec-ch-ua-full-version-list": "\"Google Chrome\";v=\"129.0.6668.100\", \"Not=A?Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"129.0.6668.100\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-model": "\"\"",
        "sec-ch-ua-platform": "\"Linux\"",
        "sec-ch-ua-platform-version": "\"6.8.0\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1"
    }

    cookies = atualizar_cookies()

    logging.info("Iniciando obtenção de dados de vendas do Steam.")
    scrape_do_url = f"https://api.scrape.do?token={SCRAPEDO_API_KEY}&url={url}"
    response = requests.get(scrape_do_url, headers=headers, cookies=cookies)
    logging.info(f"Status da requisição: {response.status_code}")

    if response.status_code == 200:
        logging.info("Requisição bem-sucedida!")

        soup = BeautifulSoup(response.text, 'html.parser')
        names, discounts, prices, ratings, releases, ends, starts, game_links, image_links, ids = [], [], [], [], [], [], [], [], [], []

        table_rows = soup.select('tr.app')

        for row in table_rows:
            name = row.select_one('.b')
            discount = row.select_one('.price-discount')
            price = row.select('td')[4]
            rating = row.select('td')[5]
            release = row.select('td')[6]
            end_timestamp = row.select('td')[7].get('data-sort')
            end_datetime = datetime.fromtimestamp(int(end_timestamp))
            end = end_datetime.strftime('%d %b %Y')
            start_timestamp = row.select('td')[8].get('data-sort')
            start_datetime = datetime.fromtimestamp(int(start_timestamp))
            start = start_datetime.strftime('%d %b %Y')
            game_link = row.select_one('.info-icon')['href']
            regex = r"\/app\/(\d+)"
            id = (re.search(regex, game_link)).group(1)
            img_link = f"https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{id}/capsule_231x87.jpg"

            names.append(name.text.strip() if name else '')
            discounts.append(discount.text.strip() if discount else '')
            prices.append(price.text.strip() if price else '')
            ratings.append(rating.text.strip() if rating else '')
            releases.append(release.text.strip() if release else '')
            ends.append(end if end else '')
            starts.append(start if start else '')
            game_links.append(game_link if game_link else '')
            ids.append(id)
            image_links.append(img_link)


        sales_data = pd.DataFrame({
            'Name': names,
            'Discount': discounts,
            'Price': prices,
            'Rating': ratings,
            'Release_Date': releases,
            'Ends': ends,
            'Starts': starts,
            'Game_Link': game_links,
            'Image_Link': image_links,
            'ID': ids
        })
        
        # def fetch_additional_info(app_id):
        #     url = f"https://steamdb.info/api/RenderAppHover/?appid={app_id}"

        #     scrape_do_url = f"https://api.scrape.do?token={SCRAPEDO_API_KEY}&url={url}"
            
        #     response = requests.get(scrape_do_url, headers=headers, cookies=cookies)
        #     if response.status_code == 200:
        #         soup = BeautifulSoup(response.text, "html.parser")

        #         developer = soup.select_one(".hover_body.hover_meta a.b").text if soup.select_one(".hover_body.hover_meta a.b") else ''
        #         release_date = soup.select(".hover_body.hover_meta b")[0].text if soup.select(".hover_body.hover_meta b") else ''
        #         player_peak = soup.select(".hover_body.hover_meta b")[1].text if len(soup.select(".hover_body.hover_meta b")) > 1 else ''
        #         followers = soup.select(".hover_body.hover_meta b")[2].text if len(soup.select(".hover_body.hover_meta b")) > 2 else ''
                
        #         return {
        #             "Developer": developer,
        #             "Release Date": release_date,
        #             "24h Player Peak": player_peak,
        #             "Followers": followers
        #         }
        #     else:
        #         print(f"Failed to fetch data for appid {app_id}")
        #         return None
        
        # additional_info = []
        # for app_id in ids:
        #     additional_info.append(fetch_additional_info(app_id))
        
        # additional_info_df = pd.DataFrame(additional_info)
        # sales_data = pd.concat([sales_data, additional_info_df], axis=1)
        
        with open('steam_sales_bq.csv', 'w') as f:
            sales_data.to_csv(f, index=False)

        return sales_data
    else:
        logging.error("Erro na obtenção de dados. Código de status:", response.status_code)
        return None


def criar_tabela_se_nao_existir(schema):
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    try:
        client.get_table(table_ref)
        logging.info(f"Tabela {table_ref} já existe.")
    except Exception as e:
        logging.info(f"Tabela {table_ref} não encontrada. Criando tabela...")
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)  
        logging.info(f"Tabela {table_ref} criada com sucesso.")

def enviar_para_bigquery(dataframe):
    schema = [
        bigquery.SchemaField("Name", "STRING"),
        bigquery.SchemaField("Discount", "STRING"),
        bigquery.SchemaField("Price", "STRING"),
        bigquery.SchemaField("Rating", "STRING"),
        bigquery.SchemaField("Release_Date", "STRING"),
        bigquery.SchemaField("Ends", "STRING"),
        bigquery.SchemaField("Starts", "STRING"),
        bigquery.SchemaField("Game_Link", "STRING"),
        bigquery.SchemaField("Image_Link", "STRING"),
        bigquery.SchemaField("ID", "STRING"),
    ]

    criar_tabela_se_nao_existir(schema)

    if dataframe.empty:
        logging.warning("DataFrame está vazio. Operação abortada.")
        return

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    logging.info("Excluindo dados existentes na tabela.")
    client.query(f"DELETE FROM `{table_ref}` WHERE TRUE").result()
    logging.info("Dados antigos excluídos com sucesso.")

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    job = client.load_table_from_dataframe(dataframe, table_ref, job_config=job_config)
    job.result()
    logging.info("Dados carregados com sucesso no BigQuery!")

if __name__ == '__main__':
    data = obter_dados_steam_sales()
    if data is not None:
        enviar_para_bigquery(data)
    else:
        logging.error("Erro ao obter dados de vendas do Steam.")
