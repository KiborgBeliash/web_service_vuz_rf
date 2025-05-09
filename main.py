import requests
from bs4 import BeautifulSoup
import zipfile
import os
import hashlib

def download_and_extract(url, extract_to="data"):
    archive_name = url.split("/")[-1]
    response = requests.get(url)

    with open(archive_name, "wb") as file:
        file.write(response.content)

    with zipfile.ZipFile(archive_name, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Архив {archive_name} распакован в {extract_to}")

    os.remove(archive_name)


from datetime import datetime, timedelta

yesterday = datetime.now() - timedelta(days=1)
data_time = str(yesterday.date()).replace("-", "")
zip_url = "https://islod.obrnadzor.gov.ru/opendata/data-" + data_time + "-structure-20160713.zip"
# print(zip_url)
download_and_extract(zip_url)

