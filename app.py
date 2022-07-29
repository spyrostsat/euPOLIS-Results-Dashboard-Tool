from flask import Flask, render_template, url_for, flash, redirect, request


app = Flask(__name__)
app.config['SECRET_KEY'] = '61eeaaa0602a3b02cf95cedfed635601'

@app.route("/")
@app.route("/home")
def home_page():
    return render_template('home.html', title="Home")


if __name__ == "__main__":
    app.run(debug=True)
