from flask import Flask, send_file

app = Flask(__name__)

@app.route("/")
def show_map():
    return send_file("campgrounds_map.html")

if __name__ == "__main__":
    app.run(debug=True, port=5050) 