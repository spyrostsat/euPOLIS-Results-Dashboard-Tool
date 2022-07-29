from flask import Flask, render_template, url_for, flash, redirect, request


app = Flask(__name__)
app.config['SECRET_KEY'] = '61eeaaa0602a3b02cf95cedfed635601'


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', title="Home")

@app.route("/baseline-scenario")
def baseline_scenario():
    return render_template('baseline_scenario.html', title="Baseline Scenario")


@app.route("/scenario-1")
def scenario_1():
    return render_template('scenario_1.html', title="Scenario 1")


@app.route("/scenario-2")
def scenario_2():
    return render_template('scenario_2.html', title="Scenario 2")


@app.route("/scenario-3")
def scenario_3():
    return render_template('scenario_3.html', title="Scenario 3")


@app.route("/scenario-4")
def scenario_4():
    return render_template('scenario_4.html', title="Scenario 4")


@app.route("/scenarios-comparisons")
def comparisons():
    return render_template('comparisons.html', title="Scenarios Comparisons")


if __name__ == "__main__":
    app.run(debug=True)
