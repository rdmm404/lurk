from curl_cffi import requests
from rich import print

# Define the endpoint
url = "https://www.bestbuy.ca/api/v2/json/search"

# Define the query parameters
search_params = {
    "currentRegion": "ON",
    "lang": "en-CA",
    "query": "nvidia 4070",
    "sortBy": "relevance",
    "sortDir": "desc",
    "path": "category:Computers & Tablets;category:PC Components;currentPrice:[* TO 1500]",
}

# Define the headers
headers = {
    "Cache-Control": "no-cache",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36",
}

# Make the GET request
response = requests.get(url, params=search_params, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    try:
        # If the response is JSON, parse it
        data = response.json()
        skus: list[str] = [p["sku"] for p in data["products"]]
        print(skus)
    except ValueError:
        print(response.text)
        skus = []
else:
    skus = []
    print(f"Request failed with status code {response.status_code}")


products_params = {
    # "accept": "application/vnd.bestbuy.simpleproduct.v1+json",
    # "accept-language": "en-CA",
    "locations": (
        "199|203|259|977|198|197|617|193|195|931|196|927|938|164|194|192|965|233|163|180|"
        "179|237|202|176|932|188|943|926|200|260|956|187|175|930|764|795|916|161|207|954|"
        "1016|319|544|910|622|937|181|245|160|223|990|925|985|942|178|949|959"
    ),
    "postalCode": "M6K1Y5",
    "skus": "|".join(skus),
}


print(products_params)
url = "https://www.bestbuy.ca/ecomm-api/availability/products"
response = requests.get(url, params=products_params, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    try:
        # If the response is JSON, parse it
        data = response.json()
        print(data)
    except ValueError:
        # If response is not JSON, print the raw text
        print(response.text)
else:
    print(f"Request failed with status code {response.status_code}")
