import csv
import requests
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from urllib.parse import urlparse
from selenium.webdriver.common.by import By


class RottenTomatoesCrawler:
    def __init__(self) -> None:
        self.url = "https://www.rottentomatoes.com/browse/movies_at_home/?page=1"
        self.cast = []
        self.movies = []

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

        self.get_cast_and_crew(soup=soup, movie_url=url)
        self.get_metadata(soup=soup)

    def get_cast_and_crew(self, soup, movie_url):
        try:
            cast_elems = soup.find("div", attrs={"class": "cast-wrap"}).find_all("div")

            for i in cast_elems:
                meta = i.find("div", attrs={"class": "metadata"})

                if meta is not None:
                    profile_url = "N/A"
                    name = "N/A"
                    role = "N/A"

                    profile_path_elem = i.find_all("a")
                    profile_url = (
                        urlparse(movie_url).netloc + profile_path_elem[0].get("href")
                        if len(profile_path_elem) > 0
                        else ""
                    )

                    name = i.find_all("img")[0].get("alt").strip()
                    role = meta.find("p", attrs={"class": "p--small"}).text.strip()

                    self.cast.append((movie_url, profile_url, name, role))

            with open("data/cast_and_crew.csv", "w") as cast_csv:
                writer = csv.writer(cast_csv)

                writer.writerow(["movie_url", "actor_profile_url", "name", "role"])
                writer.writerows(self.cast)
        except Exception as e:
            print("Error: ", e)

    def get_reviews(self):
        pass

    def get_metadata(self, soup):
        info_labels = [
            "Rating:",
            "Genre:",
            "Original Language:",
            "Director:",
            "Producer:",
            "Writer:",
            "Release Date (Theaters):",
            "Release Date (Streaming):",
            "Box Office (Gross USA):",
            "Runtime:",
            "Distributor:",
            "Production Co:",
            "Sound Mix:",
        ]

        try:
            thumbnail_elem = soup.find_all("tile-dynamic", attrs={"class": "thumbnail"})
            thumbnail = (
                thumbnail_elem[0].find("img").get("src")
                if len(thumbnail_elem) > 0
                else ""
            )

            title_elem = soup.find_all("h1", attrs={"data-qa": "score-panel-title"})
            title = title_elem[0].text.strip() if len(title_elem) > 0 else ""

            synopsis_elem = soup.find_all("p", attrs={"data-qa": "movie-info-synopsis"})
            synopsis = synopsis_elem[0].text.strip() if len(synopsis_elem) > 0 else ""

            score_board = soup.find("score-board", attrs={"id": "scoreboard"})

            audience_score = score_board.get("audiencescore")
            tomatometer_score = score_board.get("tomatometerscore")

            list_item_elems = soup.find_all("li", attrs={"class": "info-item"})

            rating = "N/A"
            genre = "N/A"
            language = "N/A"
            director = "N/A"
            producer = "N/A"
            writer = "N/A"
            theater_release_date = "N/A"
            streaming_release_date = "N/A"
            usa_box_office_gross = "N/A"
            runtime = "N/A"
            distributor = "N/A"
            production_company = "N/A"
            sound_mix = "N/A"

            for item in list_item_elems:
                p_elem = item.find("p")
                label = p_elem.find("b").text.strip()

                if label in info_labels:
                    value = p_elem.find("span").text.strip()
                    label_index = info_labels.index(label)

                    if label_index == 0:
                        rating = value
                    if label_index == 1:
                        genre = [word.strip() for word in value.split(",")]
                    if label_index == 2:
                        language = value
                    if label_index == 3:
                        director = [word.strip() for word in value.split(",")]
                    if label_index == 4:
                        producer = [word.strip() for word in value.split(",")]
                    if label_index == 5:
                        writer = [word.strip() for word in value.split(",")]
                    if label_index == 6:
                        theater_release_date = value
                    if label_index == 7:
                        streaming_release_date = value
                    if label_index == 8:
                        usa_box_office_gross = value
                    if label_index == 9:
                        runtime = value
                    if label_index == 10:
                        distributor = value
                    if label_index == 11:
                        production_company = [word.strip() for word in value.split(",")]
                    if label_index == 12:
                        sound_mix = [word.strip() for word in value.split(",")]

            self.movies.append(
                [
                    thumbnail,
                    title,
                    synopsis,
                    rating,
                    genre,
                    audience_score,
                    tomatometer_score,
                    language,
                    director,
                    writer,
                    producer,
                    theater_release_date,
                    streaming_release_date,
                    usa_box_office_gross,
                    runtime,
                    distributor,
                    production_company,
                    sound_mix,
                ]
            )

            with open("data/movies.csv", "w") as movies_csv:
                writer = csv.writer(movies_csv)
                writer.writerow(
                    [
                        "thumbnail_url",
                        "title",
                        "synopsis",
                        "rating",
                        "genre",
                        "audience_score",
                        "tomatometer_score",
                        "language",
                        "director",
                        "writer",
                        "producer",
                        "theater_release_date",
                        "streaming_release_date",
                        "usa_box_office_gross",
                        "runtime",
                        "distributor",
                        "production_company",
                        "soundmix",
                    ]
                )
                writer.writerows(self.movies)
        except Exception as e:
            print("Error: ", e)

    def store_data(self):
        pass
