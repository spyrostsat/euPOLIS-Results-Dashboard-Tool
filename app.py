from flask import Flask, render_template, url_for, flash, redirect, request
import json
from datetime import datetime

with open("json_files/baseline_json.json", "r") as f:
    baseline_scenario_data = json.load(f)

with open("json_files/scen1_json.json", "r") as f:
    scenario_1_data = json.load(f)

with open("json_files/scen2_json.json", "r") as f:
    scenario_2_data = json.load(f)

with open("json_files/scen3_json.json", "r") as f:
    scenario_3_data = json.load(f)

with open("json_files/scen4_json.json", "r") as f:
    scenario_4_data = json.load(f)


app = Flask(__name__)
app.config['SECRET_KEY'] = '61eeaaa0602a3b02cf95cedfed635601'


@app.route("/")
@app.route("/home")
def home():
    # in the Home Page i will just use the basic site's information received from the baseline_scenario json file

    general_info = baseline_scenario_data["general_info"]
    general_parameters = baseline_scenario_data["general_params"]


    return render_template('home.html', title="Home", baseline_scenario_data=baseline_scenario_data,
                           baseline_scenario_data_js=json.dumps(baseline_scenario_data), general_info=general_info,
                           general_parameters=general_parameters)


@app.route("/baseline-scenario")
def baseline_scenario():
    dates_ts = baseline_scenario_data["Output_TS"]["date"]
    dates_years_ts = [datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts]
    dates_months_ts = [datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts]


    total_gw_ts = baseline_scenario_data["Output_TS"]["total_gw_logger_id_108"]
    imprv_roofs_runoff_ts = baseline_scenario_data["Output_TS"]["imprv_roofs_runoff_logger_id_215"]
    total_runoff_ts = baseline_scenario_data["Output_TS"]["total_runoff_logger_id_129"]
    total_demand_ts = baseline_scenario_data["Output_TS"]["total_demand_logger_id_54"]
    total_wastewater_ts = baseline_scenario_data["Output_TS"]["total_wastewater_logger_id_55"]
    rainfall_ts = baseline_scenario_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"]
    impervious_surface = baseline_scenario_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    total_site_surface = baseline_scenario_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surfaces = baseline_scenario_data["general_params"]["existing_green_surfaces"]["param_val"]

    total_demand_baseline_ts = baseline_scenario_data["Output_TS_baseline"]["total_demand_logger_id_54"]
    total_runoff_baseline_ts = baseline_scenario_data["Output_TS_baseline"]["total_runoff_logger_id_129"]
    total_wastewater_baseline_ts = baseline_scenario_data["Output_TS_baseline"]["total_wastewater_logger_id_55"]


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
