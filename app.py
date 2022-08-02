from flask import Flask, render_template, url_for, flash, redirect, request
import json
from datetime import datetime
import numpy as np

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


annual_calculations_ei = ["EI-45 (ENV)", "EI-46b (ENV)", "EI-46a (ENV)", "EI-44 (ENV)", "EI-50 (ENV)", "EI-48b (ENV)",
                          "EI-48a (ENV)", "CI-55 (ENV)", "EI-67 (URB) / CI-66 (ENV)"]

annual_calculations_categories = ["Site NBS Water Autonomy (%)", "Water Reuse (%)", "Potable Water Savings (%)",
                                  "Energy Consumption (kWh/year)", "Runoff coefficient (%)", "Stormwater treated/managed locally (%)",
                                  "Wastewater treated/managed locally (%)", "Impervious Surfaces (%)", "Green Surfaces/Spaces (%)"]


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
    impervious_surface = baseline_scenario_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    site_surface = baseline_scenario_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = baseline_scenario_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = baseline_scenario_data["general_params"]["imp_surf_baseline"]["param_val"]

    dates_ts = baseline_scenario_data["Output_TS"]["date"]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)


    gw_ts = np.array(baseline_scenario_data["Output_TS"]["total_gw_logger_id_108"], dtype=np.float64)
    roofs_runoff_ts = np.array(baseline_scenario_data["Output_TS"]["imprv_roofs_runoff_logger_id_215"], dtype=np.float64)
    runoff_ts = np.array(baseline_scenario_data["Output_TS"]["total_runoff_logger_id_129"], dtype=np.float64)
    demand_ts = np.array(baseline_scenario_data["Output_TS"]["total_demand_logger_id_54"], dtype=np.float64)
    wastewater_ts = np.array(baseline_scenario_data["Output_TS"]["total_wastewater_logger_id_55"], dtype=np.float64)

    rainfall_ts_mm = np.array(baseline_scenario_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface / 1000)

    demand_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_demand_logger_id_54"], dtype=np.float64)
    runoff_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_runoff_logger_id_129"], dtype=np.float64)
    wastewater_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_wastewater_logger_id_55"], dtype=np.float64)

    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    sums_gw = np.zeros((total_months, total_years)) # (12, 8)
    sums_roofs_runoff = np.zeros((total_months, total_years)) # (12, 8)
    sums_runoff = np.zeros((total_months, total_years)) # (12, 8)
    sums_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_wastewater = np.zeros((total_months, total_years)) # (12, 8)

    for i in range(len(dates_ts)):
        sums_gw[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_ts[i]
        sums_roofs_runoff[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += roofs_runoff_ts[i]
        sums_runoff[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += runoff_ts[i]
        sums_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += demand_ts[i]
        sums_wastewater[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += wastewater_ts[i]

    averages_monthly = np.zeros((total_months, 5)) # (12, 5) Column 0 --> gw averages... Column 4 wastewater averages

    for i in range(sums_gw.shape[0]):
        counter_gw = 0
        conter_roofs_runoff = 0
        counter_runoff = 0
        counter_demand = 0
        counter_wastewater = 0
        for j in range(sums_gw.shape[1]):
            if sums_gw[i, j] != 0:
                counter_gw += 1
                averages_monthly[i, 0] += sums_gw[i, j]
            if sums_roofs_runoff[i, j] != 0:
                conter_roofs_runoff += 1
                averages_monthly[i, 1] += sums_roofs_runoff[i, j]
            if sums_runoff[i, j] != 0:
                counter_runoff += 1
                averages_monthly[i, 2] += sums_runoff[i, j]
            if sums_demand[i, j] != 0:
                counter_demand += 1
                averages_monthly[i, 3] += sums_demand[i, j]
            if sums_wastewater[i, j] != 0:
                counter_wastewater += 1
                averages_monthly[i, 4] += sums_wastewater[i, j]

        averages_monthly[i, 0] /= (counter_gw * 1000) # we also divide by 1000 to turn L into m3
        averages_monthly[i, 1] /= (conter_roofs_runoff * 1000)
        averages_monthly[i, 2] /= (counter_runoff * 1000)
        averages_monthly[i, 3] /= (counter_demand * 1000)
        averages_monthly[i, 4] /= (counter_wastewater * 1000)

    # from Calculations_annual workseet, table with columns from 'Sum of total_demand_logger_id_54' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 8)) # (8, 8)

    days_years = np.array([])
    for i in range(8):
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += runoff_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364:
            sums_annualy[i, :] = 0

    # Final annual calculations to produce the final table of the Baseline Scenario

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 8)

    average_annual_demand = np.mean(sums_annualy[:, 0]) / 1000 # L to m3

    average_annual_green_water = baseline_scenario_data["general_params"]["green_water_baseline"]["param_val"]

    water_reuse = (average_annual_green_water / average_annual_demand) * 100 # %

    average_annual_demand_baseline = np.mean(sums_annualy[:, -3]) / 1000 # L to m3

    potable_water_savings = - (average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline

    energy_consumption = baseline_scenario_data["general_params"]["energy_baseline"]["param_val"]

    average_annual_rainfall_m3 = np.mean(sums_annualy[:, 4])

    average_annual_runoff = np.mean(sums_annualy[:, 1]) / 1000

    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100 # %

    average_annual_runoff_baseline = np.mean(sums_annualy[:, -2]) / 1000

    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100 # %

    average_annual_wastewater = np.mean(sums_annualy[:, 2]) / 1000

    average_annual_wastewater_baseline = np.mean(sums_annualy[:, -1]) / 1000

    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100

    impervious_surface_percentage = (impervious_surface / site_surface) * 100

    total_nbs_surface = baseline_scenario_data["general_params"]["NBS_surface"]["param_val"]

    total_green_surface = existing_green_surface + total_nbs_surface

    total_green_surface_percentage = (total_green_surface / site_surface) * 100

    nbs_water_autonomy = 0 # there are no NBS in the baseline scenario

    annual_calculations_values = [nbs_water_autonomy, water_reuse, potable_water_savings, energy_consumption, runoff_coeff,
                                  stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  total_green_surface_percentage]

    return render_template('baseline_scenario.html', title="Baseline Scenario", baseline_scenario_data=baseline_scenario_data,
                        annual_calculations_ei=annual_calculations_ei, annual_calculations_categories=annual_calculations_categories,
                        annual_calculations_values=annual_calculations_values)


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
