import urllib.request
import urllib.parse
import json

url = 'http://127.0.0.1:8000/api/ask'
data = json.dumps({"question": "How often should a centrifugal pump be lubricated?"}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
req = urllib.request.Request(url, data=data, headers=headers, method='POST')

try:
    response = urllib.request.urlopen(req)
    print(response.read().decode('utf-8'))
except Exception as e:
    print(e)
