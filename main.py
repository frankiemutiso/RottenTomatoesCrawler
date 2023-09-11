from crawler.crawler import RottenTomatoesCrawler


def main():
    crawler = RottenTomatoesCrawler()

    crawler.get_page()


if __name__ == "__main__":
    main()
