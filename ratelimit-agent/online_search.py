import requests
import json



def wocha_web_search(query:str)->dict:
    url = "https://api.bocha.cn/v1/web-search"
    payload = json.dumps({
        "query": query,
        "summary": True,
        "count": 10
    })

    headers = {
        'Authorization': 'Bearer sk-4621566066cb4f6c9587fc341d89bc8a',
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()

if __name__ == "__main__":
    print(wocha_web_search("宋朝为什么灭亡"))