from flask import Flask
import time
app = Flask(__name__)

@app.route("/")
def main():
    t1 = time.time()
    while True:
        x = 213456789 ** 12
        if time.time() - t1 > .0999:
            break

    print(time.time() - t1)
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run(host="localhost", port=8081, threaded=False, debug=False)