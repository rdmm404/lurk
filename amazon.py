from curl_cffi import requests

resp = requests.get(
    "https://www.amazon.ca/s?k=nvidia+5080&i=electronics&rh=n%3A2404990011%2Cn%3A677243011%2Cp_36%3A-150000&dc&qid=1738300499&rnid=12035759011",
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    },
)

with open("page.html", "w") as f:
    f.write(resp.text)
