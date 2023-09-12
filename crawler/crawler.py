from __future__ import print_function

import os
import csv
import json
import requests
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv, find_dotenv
from selenium.webdriver.chrome.service import Service


dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


class RottenTomatoesCrawler:
    def __init__(self) -> None:
        self.url = "https://www.rottentomatoes.com/browse/movies_at_home/?page=1"
        self.cast = []
        self.movies = []
        self.reviews = []
        self.domain = urlparse(self.url).netloc
        self.driver = None
        self.last_review_row = 0
        self.last_cast_row = 0
        self.last_movie_row = 0

    def get_page(
        self,
    ):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        chrome_path = os.getenv("GOOGLE_CHROME_PATH")
        driver_path = os.getenv("CHROMEDRIVER_PATH")
        debug = os.getenv("DEBUG")

        self.driver = None

        if debug is True:
            self.driver = webdriver.Chrome(options=options)
        else:
            options.binary_location = chrome_path
            self.driver = webdriver.Chrome(
                service=Service(executable_path=driver_path), options=options
            )

        self.driver.get(self.url)

        sleep(5)
        self.driver.execute_script("window.stop();")

        more_btn = self.driver.find_elements(
            By.CSS_SELECTOR, "button[data-qa='dlp-load-more-button']"
        )

        while len(more_btn) > 0:
            last_index = -1
            temp_index = 0
            movie_cards = self.driver.find_elements(By.CLASS_NAME, ("js-tile-link"))

            for i in range(len(movie_cards) - 1, last_index, -1):
                elem = movie_cards[i]
                url = None

                if elem.tag_name == "a":
                    url = elem.get_attribute("href")
                else:
                    inner_elem = elem.find_element(By.XPATH, ("./tile-dynamic//a"))
                    url = inner_elem.get_attribute("href")

                self.extract_data(url)
                temp_index = i

            last_index = temp_index
            more_btn[0].click()
            sleep(5)

        self.driver.quit()

    def extract_data(self, url):
        print(f"Crawling {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0"
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")

        self.get_cast_and_crew(soup=soup, movie_url=url)
        self.get_metadata(soup=soup)
        self.get_reviews(soup=soup)

    def get_cast_and_crew(self, soup, movie_url):
        try:
            print(f"Getting cast and crew from {movie_url}")

            cast_elems = soup.find("div", attrs={"class": "cast-wrap"}).find_all("div")

            for i in cast_elems:
                meta = i.find("div", attrs={"class": "metadata"})

                if meta is not None:
                    profile_url = "N/A"
                    name = "N/A"
                    role = "N/A"

                    profile_path_elem = i.find_all("a")
                    profile_url = (
                        self.domain + profile_path_elem[0].get("href")
                        if len(profile_path_elem) > 0
                        else ""
                    )

                    name = i.find_all("img")[0].get("alt").strip()
                    raw_role = meta.find("p", attrs={"class": "p--small"}).text.strip()

                    role = " ".join([x.strip() for x in raw_role.split(" ")])

                    self.cast.append((movie_url, profile_url, name, role))

            index = (
                self.last_cast_row
                if self.last_cast_row == 0
                else self.last_cast_row - 1
            )

            new_cast = self.cast[index:]

            columns = (
                None
                if self.last_cast_row > 0
                else ["movie_url", "actor_profile_url", "name", "role"]
            )

            start = self.last_cast_row + 1
            end = (
                len(new_cast) + 1
                if self.last_cast_row == 0
                else len(new_cast) + self.last_cast_row
            )

            self.write_to_google_sheet(
                new_cast,
                columns,
                worksheet="Cast",
                start=start,
                end=end,
                last_column_letter="D",
            )

            self.last_cast_row = end

            with open("data/cast_and_crew.csv", "w") as cast_csv:
                writer = csv.writer(cast_csv)

                writer.writerow(["movie_url", "actor_profile_url", "name", "role"])
                writer.writerows(self.cast)

            print(f"Successfully extracted and saved cast and crew from {movie_url}")
        except Exception as e:
            print("Error: ", e)

    def get_reviews(self, soup):
        critics_reviews_url_elems = soup.find_all(
            "a", attrs={"data-qa": "tomatometer-review-count"}
        )
        audience_reviews_url_elems = soup.find_all(
            "a", attrs={"data-qa": "audience-rating-count"}
        )

        title_elem = soup.find_all("h1", attrs={"data-qa": "score-panel-title"})
        title = title_elem[0].text.strip() if len(title_elem) > 0 else ""

        print(f"Getting movie reviews for {title}")

        # TODO: Consider implementing parallelism to improve the speed of getting the reviews
        if len(critics_reviews_url_elems) > 0:
            self.get_critics_reviews(title, critics_reviews_url_elems[0].get("href"))

        if len(audience_reviews_url_elems) > 0:
            self.get_audience_reviews(title, audience_reviews_url_elems[0].get("href"))

        index = (
            self.last_review_row
            if self.last_review_row == 0
            else self.last_review_row - 1
        )

        new_reviews = self.reviews[index:]

        columns = (
            None
            if self.last_review_row > 0
            else ["movie", "posted_by", "text", "date_posted", "review_type"]
        )

        start = self.last_review_row + 1
        end = (
            len(new_reviews) + 1
            if self.last_review_row == 0
            else len(new_reviews) + self.last_review_row
        )

        self.write_to_google_sheet(
            new_reviews,
            columns,
            worksheet="Reviews",
            start=start,
            end=end,
            last_column_letter="E",
        )

        self.last_review_row = end

        with open("data/reviews.csv", "w") as reviews_csv:
            writer = csv.writer(reviews_csv)
            writer.writerow(
                ["movie", "posted_by", "text", "date_posted", "review_type"]
            )
            writer.writerows(self.reviews)

        print(f"Successfully extracted and saved movie reviews for {title}")

    def get_critics_reviews(self, title, url_chunk):
        self.driver.execute_script("window.open('');")

        new_window = self.driver.window_handles[1]
        self.driver.switch_to.window(new_window)

        complete_url = "https://" + self.domain + url_chunk
        self.driver.get(complete_url)

        sleep(3)
        self.driver.execute_script("window.stop();")

        has_more = True
        page = 1
        max_pages = 10

        while has_more:
            print(f"Getting page {page} of {max_pages} from '{title}' critic reviews")

            review_rows = self.driver.find_elements(By.CLASS_NAME, ("review-row"))

            for i in review_rows:
                posted_by = i.find_element(
                    By.XPATH,
                    "./div[@class='review-data']//div[@class='reviewer-name-and-publication']//a[@class='display-name']",
                ).text.strip()
                date_posted = i.find_element(
                    By.XPATH,
                    "./div[@class='review-text-container']//p[@class='original-score-and-url']//span[@data-qa='review-date']",
                ).text.strip()
                review = i.find_element(
                    By.XPATH,
                    "./div[@class='review-text-container']//p[@class='review-text']",
                ).text.strip()

                self.reviews.append(
                    [title, posted_by, review, date_posted, "critic_review"]
                )

            next_btn = self.driver.find_elements(By.CLASS_NAME, "next")

            if (
                len(next_btn) != 0
                and next_btn[0].get_attribute("class") == "next"
                and page < max_pages
            ):
                cookie_popups = self.driver.find_elements(By.ID, "onetrust-policy")

                if len(cookie_popups) > 0:
                    cookie_popup = cookie_popups[0]
                    btn = cookie_popup.find_elements(By.CLASS_NAME, "ot-link-btn")

                    if len(btn) > 0:
                        btn[0].click()

                sections_popups = self.driver.find_elements(By.ID, "ot-lst-cnt")

                print("Sections: ", sections_popups)

                if len(sections_popups) > 0:
                    print(cookie_popup.get_attribute("outerHTML"))

                next_btn[0].click()
                sleep(3)
            else:
                has_more = False

            page += 1

        self.driver.close()

        old_window = self.driver.window_handles[0]
        self.driver.switch_to.window(old_window)
        print(f"Successfully extracted all critic reviews")

    def get_audience_reviews(self, title, url_chunk):
        self.driver.execute_script("window.open('');")

        new_window = self.driver.window_handles[1]
        self.driver.switch_to.window(new_window)

        complete_url = "https://" + self.domain + url_chunk
        self.driver.get(complete_url)

        sleep(3)
        self.driver.execute_script("window.stop();")

        has_more = True
        page = 1
        max_pages = 10

        while has_more:
            print(f"Getting page {page} of {max_pages} from '{title}' audience reviews")

            review_rows = self.driver.find_elements(
                By.CLASS_NAME, ("audience-review-row")
            )

            for row in review_rows:
                posted_by_elems = row.find_elements(
                    By.CLASS_NAME, "audience-reviews__name"
                )
                posted_by = (
                    posted_by_elems[0].text.strip()
                    if len(posted_by_elems) > 0
                    else "N/A"
                )

                review_elems = row.find_elements(
                    By.CSS_SELECTOR, "p[data-qa='review-text']"
                )
                review = (
                    review_elems[0].text.strip() if len(review_elems) > 0 else "N/A"
                )

                date_posted_elems = row.find_elements(
                    By.CSS_SELECTOR, "span[class='audience-reviews__duration']"
                )
                date_posted = (
                    date_posted_elems[0].text.strip()
                    if len(date_posted_elems) > 0
                    else "N/A"
                )

                self.reviews.append(
                    [title, posted_by, review, date_posted, "audience_review"]
                )

            next_btn = self.driver.find_elements(By.CLASS_NAME, "next")

            if (
                len(next_btn) != 0
                and next_btn[0].get_attribute("class") == "next"
                and page < max_pages
            ):
                next_btn[0].click()
                sleep(3)
            else:
                has_more = False

            page += 1

        self.driver.close()

        old_window = self.driver.window_handles[0]
        self.driver.switch_to.window(old_window)

        print(f"Successfully extracted all audience reviews")

    def get_metadata(self, soup):
        try:
            title_elem = soup.find_all("h1", attrs={"data-qa": "score-panel-title"})
            title = title_elem[0].text.strip() if len(title_elem) > 0 else ""

            print(f"Getting metadata for {title}")

            thumbnail_elem = soup.find_all("tile-dynamic", attrs={"class": "thumbnail"})
            thumbnail = (
                thumbnail_elem[0].find("img").get("src")
                if len(thumbnail_elem) > 0
                else ""
            )

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
                value = p_elem.find("span").text.strip()

                if label == "Rating:":
                    rating = value
                if label == "Genre:":
                    # genre = [word.strip() for word in value.split(",")]
                    genre = f"{','.join([word.strip() for word in value.split(',')])}"
                if label == "Original Language:":
                    language = value
                if label == "Director:":
                    # director = [word.strip() for word in value.split(",")]
                    director = (
                        f"{','.join([word.strip() for word in value.split(',')])}"
                    )
                if label == "Producer:":
                    # producer = [word.strip() for word in value.split(",")]
                    producer = (
                        f"{','.join([word.strip() for word in value.split(',')])}"
                    )
                if label == "Writer:":
                    # writer_list = [word.strip() for word in value.split(",")]
                    writer = f"{','.join([word.strip() for word in value.split(',')])}"
                if label == "Release Date (Theaters):":
                    theater_release_date = value
                if label == "Release Date (Streaming):":
                    streaming_release_date = value
                if label == "Box Office (Gross USA):":
                    usa_box_office_gross = value
                if label == "Runtime:":
                    runtime = value
                if label == "Distributor:":
                    distributor = value
                if label == "Production Co:":
                    # production_company = [word.strip() for word in value.split(",")]
                    production_company = (
                        f"{','.join([word.strip() for word in value.split(',')])}"
                    )
                if label == "Sound Mix:":
                    # sound_mix = [word.strip() for word in value.split(",")]
                    sound_mix = (
                        f"{','.join([word.strip() for word in value.split(',')])}"
                    )

            self.movies.append(
                [
                    title,
                    genre,
                    thumbnail,
                    synopsis,
                    rating,
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

            index = (
                self.last_movie_row
                if self.last_movie_row == 0
                else self.last_movie_row - 1
            )

            new_movies = self.movies[index:]

            columns = (
                None
                if self.last_movie_row > 0
                else [
                    "title",
                    "genre",
                    "thumbnail_url",
                    "synopsis",
                    "rating",
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

            start = self.last_movie_row + 1
            end = (
                len(new_movies) + 1
                if self.last_movie_row == 0
                else len(new_movies) + self.last_movie_row
            )

            print("End: ", end)

            self.write_to_google_sheet(
                new_movies,
                columns,
                worksheet="Movies",
                start=start,
                end=end,
                last_column_letter="R",
            )

            self.last_movie_row = end

            with open("data/movies.csv", "w") as movies_csv:
                writer = csv.writer(movies_csv)
                writer.writerow(
                    [
                        "title",
                        "genre",
                        "thumbnail_url",
                        "synopsis",
                        "rating",
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

                print(f"Successfully extracted and saved metadata for {title}")
        except Exception as e:
            print("Error: ", e)

    def store_data(self):
        pass

    def write_to_google_sheet(
        self, data, columns, worksheet, start, end, last_column_letter
    ):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            # "https://www.googleapis.com/auth/drive",
        ]

        # path = os.path.join(os.getcwd(), "credentials.json")
        info_str = os.getenv("CREDENTIALS")
        info_json = json.loads(info_str)

        credentials = service_account.Credentials.from_service_account_info(
            info_json, scopes=scopes
        )
        spreadsheet_service = build("sheets", "v4", credentials=credentials)
        # drive_service = build("drive", "v3", credentials=credentials)

        values = data

        if columns is not None:
            values.insert(0, columns)

        range = f"{worksheet}!A{start}:{last_column_letter}{end}"

        body = {"values": values}

        result = (
            spreadsheet_service.spreadsheets()
            .values()
            .update(
                spreadsheetId="11ZDCJ0_1oAkAcvXUQkQx95uAt_eeO9h5XNxtwJ5eeDc",
                range=range,
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )

        print(result)

        print("\n--- Writing from Google Sheets------")
        print("------------------------------------")
        print("\t{0} cells updated.".format(result.get("updatedCells")))
        print("\t{0} rows updated.".format(result.get("updatedRows")))
        print("------------------------------------")
