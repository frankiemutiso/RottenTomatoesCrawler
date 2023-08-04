from selenium import webdriver
from selenium.webdriver.common.by import By
import os
from time import sleep
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import csv


class RottenTomatoesCrawler:
    def __init__(self) -> None:
        self.url = "https://www.rottentomatoes.com/browse/movies_at_home/?page=1"
        self.cast = []

    def get_page(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driver.get(self.url)

        sleep(5)
        driver.execute_script("window.stop();")

        movie_cards = driver.find_elements(By.CLASS_NAME, ("js-tile-link"))

        for i in range(len(movie_cards) - 1, -1, -1):
            elem = movie_cards[i]
            url = None

            if elem.tag_name == "a":
                url = elem.get_attribute("href")
            else:
                inner_elem = elem.find_element(By.XPATH, ("./tile-dynamic//a"))
                url = inner_elem.get_attribute("href")

            self.extract_data(url)

    def extract_data(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0"
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")

        cast_elems = soup.find("div", attrs={"class": "cast-wrap"}).find_all("div")

        self.get_cast_and_crew(cast_elems=cast_elems, movie_url=url)

    def get_cast_and_crew(self, cast_elems, movie_url):
        for i in cast_elems:
            meta = i.find("div", attrs={"class": "metadata"})

            if meta is not None:
                profile_url = "N/A"
                name = "N/A"
                role = "N/A"

                try:
                    profile_path = i.find("a").get("href")
                    profile_url = urlparse(movie_url).netloc + profile_path
                    name = i.find_all("img")[0].get("alt").strip()
                    role = meta.find_all("p", attrs={"class": "p--small"})[
                        0
                    ].text.strip()
                except Exception as e:
                    print(e)

                self.cast.append((movie_url, profile_url, name, role))

        with open("data/cast_and_crew.csv", "w") as cast_csv:
            writer = csv.writer(cast_csv)

            writer.writerow(["movie_url", "actor_profile_url", "name", "role"])
            writer.writerows(self.cast)

    def get_reviews(self):
        pass

    def get_metadata(self):
        pass

    def store_data(self):
        pass
