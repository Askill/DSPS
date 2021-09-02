from flask import Flask
import requests
import time
app = Flask(__name__)

@app.route("/")
def main():
    t1 = time.time()
    x = requests.get("http://127.0.0.1:8081")
    print(time.time() - t1)
    return "yes"

if __name__ == '__main__':
    app.run(host="localhost", port=8080, threaded=True, debug=False)