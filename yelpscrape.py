from lxml import html
import unicodecsv as csv
import requests
from time import sleep
import re
import argparse
import json
from  jsonmerge import merge

def geturls(query, loc, pages):
    urls = []
    for page in range(pages):
        yelp_url = "https://www.yelp.com/search?find_desc=Restaurants&find_loc=Mission%20Bay%2C%20San%20Francisco%2C%20CA&l=p%3ACA%3ASan_Francisco%3A%3AFinancial_District&start={}0".format(page * 3)
        #yelp_url = "https://www.yelp.com/search?find_desc=%s&find_loc=%s&ns=1&l=p%3ACA%3ASan_Francisco%3A%3AChinatown&start=%s0" % (query,loc,page)
        urls.append(yelp_url)
    return urls

def parse(urls):
    headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chrome/70.0.3538.77 Safari/537.36'}
    success = False
    scraped_datas = []

    for url in urls:
        print("Retrieving :", url)
        for _ in range(10):
            response = requests.get(url, verify=False, headers=headers)
            if response.status_code == 200:
                success = True
                break
            else:
                print("Response received: %s. Retrying : %s"%(response.status_code, url))
                success = False

        if success == False:
            print("Failed to process the URL: ", url)

        parser = html.fromstring(response.text)
        listing = parser.xpath("//li[@class='regular-search-result']")
        raw_json = parser.xpath("//script[contains(@data-hypernova-key,'yelp_main__SearchApp')]//text()")

        # Case 1: Getting data from new UI
        if raw_json:
            print('Grabbing data from new UI')
            cleaned_json = raw_json[0].replace('<!--', '').replace('-->', '').strip()
            json_loaded = json.loads(cleaned_json)
            search_results = json_loaded['searchPageProps']['searchResultsProps']['searchResults']

            for results in search_results:
                # Ad pages doesn't have this key.
                result = results.get('searchResultBusiness')
                if result:
                    is_ad = result.get('isAd')
                    price_range = result.get('priceRange')
                    position = result.get('ranking')
                    name = result.get('name')
                    ratings = result.get('rating')
                    reviews = result.get('reviewCount')
                    address = result.get('formattedAddress')
                    neighborhood = result.get('neighborhoods')
                    category_list = result.get('categories')
                    full_address = address+' '+''.join(neighborhood)
                    url = "https://www.yelp.com"+result.get('businessUrl')

                    category = []
                    for categories in category_list:
                        category.append(categories['title'])
                    business_category = ','.join(category)

                    # Filtering out ads
                    if not(is_ad):
                        data = {
                            'business_name': name,
                            'rank': position,
                            'review_count': reviews,
                            'categories': business_category,
                            'rating': ratings,
                            'address': full_address,
                            'price_range': price_range,
                            'url': url
                        }
                        scraped_datas.append(data)
    return scraped_datas

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('place', help='Location/ Address/ zip code')
    search_query_help = """Available search queries are:\n
                            Restaurants,\n
                            Breakfast & Brunch,\n
                            Coffee & Tea,\n
                            Delivery,
                            Reservations"""
    argparser.add_argument('search_query', help=search_query_help)
    args = argparser.parse_args()
    place = args.place
    search_query = args.search_query
    urls = geturls(search_query, place, 18)
    scraped_data = parse(urls)
    with open("scraped_yelp_results_for_%s.csv" % (place), "wb") as fp:
        fieldnames = ['rank', 'business_name', 'review_count', 'categories', 'rating', 'address', 'price_range', 'url']
        writer = csv.DictWriter(fp, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        if scraped_data:
            print ("Writing data to output file")
            for data in scraped_data:
                writer.writerow(data)
