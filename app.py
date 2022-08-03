from flask import Flask, render_template, url_for, flash, redirect, request
import json
from datetime import datetime
import numpy as np
import copy


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
    # General Parameters
    site_surface = baseline_scenario_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = baseline_scenario_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = baseline_scenario_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = baseline_scenario_data["model_params"]["imprv_roofs_id_8"]["param_val"]

    # Output TS
    # IN ALL FUTURE JSON FILES FIRST A JOB SHOULD BE DONE TO KEEP ONLY THE VALUES OF THE DAYS THAT CORRESPOND TO FULL MONTHS
    # i.e. if i have 20 values for 20 days of one month I should get manually rid of these 20 values from the dataset

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = baseline_scenario_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    gw_ts = np.array(baseline_scenario_data["Output_TS"]["total_gw_logger_id_108"][:-12], dtype=np.float64)
    roofs_runoff_ts = np.array(baseline_scenario_data["Output_TS"]["imprv_roofs_runoff_logger_id_215"][:-12], dtype=np.float64)
    runoff_ts = np.array(baseline_scenario_data["Output_TS"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    demand_ts = np.array(baseline_scenario_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(baseline_scenario_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(baseline_scenario_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)

    # Calculations Monthly
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

    counter_years = np.zeros(total_months)

    for i in dates_months_ts_normalized:
        counter_years[i] += 1 # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 5)) # (12, 5) Column 0 --> gw averages... Column 4 wastewater averages

    for i in range(sums_gw.shape[0]):
        for j in range(sums_gw.shape[1]):
            averages_monthly[i, 0] += sums_gw[i, j]
            averages_monthly[i, 1] += sums_roofs_runoff[i, j]
            averages_monthly[i, 2] += sums_runoff[i, j]
            averages_monthly[i, 3] += sums_demand[i, j]
            averages_monthly[i, 4] += sums_wastewater[i, j]

        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)


    # Calculations Annualy

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

    # Final annual calculations for output Table

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
    # General Parameters
    site_surface = scenario_1_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_1_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_1_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_1_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_1_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_1_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_1_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_1_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_1_data["model_params"]["bg_planters_id_150"]["param_val"]
    rwh_tank_capacity = scenario_1_data["model_params"]["rwh_tank_capacity"]["param_val"]

    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_1_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    green_roof_demand_ts = np.array(scenario_1_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_1_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_1_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_1_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_1_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_1_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_1_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_1_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)
    drainage_ts = np.array(scenario_1_data["Output_TS"]["total_drainage_logger_id_148"][:-12], dtype=np.float64)
    demand_ts = np.array(scenario_1_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_1_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_1_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_1_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_1_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_1_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_1_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)
    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts
    green_water_total_nbs_ts = copy.deepcopy(rainwater_green_roof_ts)

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)
    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]
        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months)

    for i in dates_months_ts_normalized:
        counter_years[i] += 1 # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 11)) # (12, 9) Column 0 --> green_roof_demand averages... Column 8 rwh_tank_spill averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 6] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 7] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 8] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)

    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 9] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 10] = (averages_monthly[i, 7] / (averages_monthly[i, 5] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY


    # Calculations Annualy

    total_green_water_used_ts = copy.deepcopy(green_water_total_nbs_ts)
    total_energy_consumption_ts = copy.deepcopy(rwh_pump_energy_ts)


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 18)) # (8, 18)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += drainage_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 18)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 7]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, -7]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, -3]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, -6]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, -4]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, -9]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, -2]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, -8]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, -1]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]

    # Charts data to pass on the frontend

    # numpy arrays are not json supported, so i turn the arrays back to python lists
    chart_1_data_1 = averages_monthly[:, 6].tolist()
    chart_1_data_2 = averages_monthly[:, 7].tolist()
    chart_2_data_1 = averages_monthly[:, 8].tolist()
    chart_3_data_1 = total_nbs_demand_ts.tolist()
    chart_3_data_2 = rainfall_ts_mm.tolist()

    return render_template('scenario_1.html', title="Scenario 1", scenario_1_data=scenario_1_data,
                        annual_calculations_ei=annual_calculations_ei, annual_calculations_categories=annual_calculations_categories,
                        annual_calculations_values=annual_calculations_values, averages_monthly=averages_monthly,
                        chart_1_data_1=json.dumps(chart_1_data_1), chart_1_data_2=json.dumps(chart_1_data_2),
                        chart_2_data_1=json.dumps(chart_2_data_1), chart_3_data_1=json.dumps(chart_3_data_1),
                        chart_3_data_2=json.dumps(chart_3_data_2), dates_ts=json.dumps(dates_ts))


@app.route("/scenario-2")
def scenario_2():
    # Scenario 2 is exactly the same as Scenario 1. Only difference is that some of the model parameters take different
    # values, but the 2 Excels are identical. So I just copy and paste the code from Scenario 1 and just change the
    # names of the json files

    # General Parameters
    site_surface = scenario_2_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_2_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_2_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_2_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_2_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_2_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_2_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_2_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_2_data["model_params"]["bg_planters_id_150"]["param_val"]
    rwh_tank_capacity = scenario_2_data["model_params"]["rwh_tank_capacity"]["param_val"]

    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_2_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    green_roof_demand_ts = np.array(scenario_2_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_2_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_2_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_2_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_2_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_2_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_2_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_2_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)
    drainage_ts = np.array(scenario_2_data["Output_TS"]["total_drainage_logger_id_148"][:-12], dtype=np.float64)
    demand_ts = np.array(scenario_2_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_2_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_2_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_2_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_2_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_2_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_2_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)
    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts
    green_water_total_nbs_ts = copy.deepcopy(rainwater_green_roof_ts)

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)
    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]
        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months)

    for i in dates_months_ts_normalized:
        counter_years[i] += 1 # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 11)) # (12, 9) Column 0 --> green_roof_demand averages... Column 8 rwh_tank_spill averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 6] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 7] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 8] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)

    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 9] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 10] = (averages_monthly[i, 7] / (averages_monthly[i, 5] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY


    # Calculations Annualy

    total_green_water_used_ts = copy.deepcopy(green_water_total_nbs_ts)
    total_energy_consumption_ts = copy.deepcopy(rwh_pump_energy_ts)


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 18)) # (8, 18)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += drainage_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 18)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 7]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, -7]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, -3]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, -6]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, -4]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, -9]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, -2]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, -8]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, -1]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]

    # Charts data to pass on the frontend

    # numpy arrays are not json supported, so i turn the arrays back to python lists
    chart_1_data_1 = averages_monthly[:, 6].tolist()
    chart_1_data_2 = averages_monthly[:, 7].tolist()
    chart_2_data_1 = averages_monthly[:, 8].tolist()
    chart_3_data_1 = total_nbs_demand_ts.tolist()
    chart_3_data_2 = rainfall_ts_mm.tolist()

    return render_template('scenario_2.html', title="Scenario 2", scenario_2_data=scenario_2_data,
                        annual_calculations_ei=annual_calculations_ei, annual_calculations_categories=annual_calculations_categories,
                        annual_calculations_values=annual_calculations_values, averages_monthly=averages_monthly,
                        chart_1_data_1=json.dumps(chart_1_data_1), chart_1_data_2=json.dumps(chart_1_data_2),
                        chart_2_data_1=json.dumps(chart_2_data_1), chart_3_data_1=json.dumps(chart_3_data_1),
                        chart_3_data_2=json.dumps(chart_3_data_2), dates_ts=json.dumps(dates_ts))



@app.route("/scenario-3")
def scenario_3():
    # General Parameters
    site_surface = scenario_3_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_3_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_3_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_3_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_3_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_3_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_3_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_3_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_3_data["model_params"]["bg_planters_id_150"]["param_val"]
    shelter_surface = scenario_3_data["model_params"]["bg_shelter_id_200"]["param_val"]
    rwh_tank_capacity = scenario_3_data["model_params"]["rwh_tank_capacity"]["param_val"]
    gw_tank_capacity = scenario_3_data["model_params"]["gw_tank_capacity"]["param_val"]


    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_3_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    # Fist some new columns for Scenario 3 as opposed to Scenarios 1, 2

    shelter_demand_ts = np.array(scenario_3_data["Output_TS"]["bg_shelter_demand_logger_id_204"][:-12], dtype=np.float64)
    gw_ts = np.array(scenario_3_data["Output_TS"]["total_gw_logger_id_108"][:-12], dtype=np.float64)
    gw_treated_ts = np.array(scenario_3_data["Output_TS"]["gw_treated_logger_id_206"][:-12], dtype=np.float64)
    gw_treatment_spill_ts = np.array(scenario_3_data["Output_TS"]["gw_treatment_spill_id_212"][:-12], dtype=np.float64)
    gw_tank_spill_ts = np.array(scenario_3_data["Output_TS"]["gw_tank_spill_id_208"][:-12], dtype=np.float64)
    gw_water_from_system_ts = np.array(scenario_3_data["Output_TS"]["gw_water_from_system_logger_id_210"][:-12], dtype=np.float64)
    gw_tank_water_storage_ts = np.array(scenario_3_data["Output_TS"]["gw_tank_water_storage_id_202"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    green_roof_demand_ts = np.array(scenario_3_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_3_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_3_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_3_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_3_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_3_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_3_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_3_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)

    # Again some new columns as opposed to Scenarios 1,2
    runoff_ts = np.array(scenario_3_data["Output_TS"]["total_runoff_logger_id_183"][:-12], dtype=np.float64)
    gw_treatment_energy_ts = np.array(scenario_3_data["Output_TS"]["gw_treatm_energy_pot_id_18"][:-12], dtype=np.float64)
    gw_pump_energy_ts = np.array(scenario_3_data["Output_TS"]["gw_pump_energy_pot_id_19"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    demand_ts = np.array(scenario_3_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_3_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_3_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_3_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_3_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_3_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_3_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)

    # Shelter new columns
    potable_water_shelter_ts = copy.deepcopy(gw_water_from_system_ts)
    gw_shelter_ts = shelter_demand_ts - potable_water_shelter_ts

    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts + shelter_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts + potable_water_shelter_ts
    green_water_total_nbs_ts = rainwater_green_roof_ts + gw_shelter_ts

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)

    sums_shelter_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_shelter = np.zeros((total_months, total_years)) # (12, 8)
    sums_gw_shelter = np.zeros((total_months, total_years)) # (12, 8)

    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))

    sums_gw_tank_spill = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]

        sums_shelter_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += shelter_demand_ts[i]
        sums_potable_water_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_shelter_ts[i]
        sums_gw_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_shelter_ts[i]

        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]

        sums_gw_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_tank_spill_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months) # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    for i in dates_months_ts_normalized:
        counter_years[i] += 1

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 16)) # (12, 16) Column 0 --> green_roof_demand averages... Column 15 --> total_nbs_autonomy averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_shelter_demand[i, j]

            averages_monthly[i, 6] += sums_potable_water_shelter[i, j]

            averages_monthly[i, 7] += sums_gw_shelter[i, j]

            averages_monthly[i, 8] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 9] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 10] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 11] += sums_gw_tank_spill[i, j]

            averages_monthly[i, 12] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)
            averages_monthly[i, 9] /= (counter_years[i] * 1000)
            averages_monthly[i, 10] /= (counter_years[i] * 1000)
            averages_monthly[i, 11] /= (counter_years[i] * 1000)
            averages_monthly[i, 12] /= (counter_years[i] * 1000)


    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 13] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 14] = (averages_monthly[i, 7] / averages_monthly[i, 5]) * 100 # NBS3 WATER AUTONOMY
        averages_monthly[i, 15] = (averages_monthly[i, 10] / (averages_monthly[i, 8] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY

    # Calculations Annualy

    total_green_water_used_ts = copy.deepcopy(green_water_total_nbs_ts)
    total_energy_consumption_ts = gw_treatment_energy_ts + gw_pump_energy_ts + rwh_pump_energy_ts


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 21)) # (8, 21)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += shelter_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += gw_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += runoff_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 18] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 19] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 20] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 21)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_shelter = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_shelter = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_gw_shelter = np.mean(sums_annualy[:, 7]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 9]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 10]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    nbs3_water_autonomy = (average_annual_gw_shelter / average_annual_demand_shelter) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 11]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, 14]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, 18]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, 15]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, 17]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, 12]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, 19]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, 13]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, 20]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface + shelter_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]


    # Charts data to pass on the frontend
    # numpy arrays are not json supported, so i turn the arrays back to python lists
    chart_1_data_1 = averages_monthly[:, 9].tolist()
    chart_1_data_2 = averages_monthly[:, 10].tolist()
    chart_2_data_1 = averages_monthly[:, 11].tolist()
    chart_2_data_2 = averages_monthly[:, 12].tolist()
    chart_3_data_1 = total_nbs_demand_ts.tolist()
    chart_3_data_2 = rainfall_ts_mm.tolist()

    return render_template('scenario_3.html', title="Scenario 3", scenario_3_data=scenario_3_data,
                        annual_calculations_ei=annual_calculations_ei, annual_calculations_categories=annual_calculations_categories,
                        annual_calculations_values=annual_calculations_values, averages_monthly=averages_monthly,
                        chart_1_data_1=json.dumps(chart_1_data_1), chart_1_data_2=json.dumps(chart_1_data_2),
                        chart_2_data_1=json.dumps(chart_2_data_1), chart_2_data_2=json.dumps(chart_2_data_2),
                        chart_3_data_1=json.dumps(chart_3_data_1), chart_3_data_2=json.dumps(chart_3_data_2),
                        dates_ts=json.dumps(dates_ts))


@app.route("/scenario-4")
def scenario_4():
    # Scenario 4 is similar to Scenario 3 there some minor addings due to the Shelter WC being installed

    # General Parameters
    site_surface = scenario_4_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_4_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_4_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_4_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_4_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_4_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_4_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_4_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_4_data["model_params"]["bg_planters_id_150"]["param_val"]
    shelter_surface = scenario_4_data["model_params"]["bg_shelter_id_200"]["param_val"]
    rwh_tank_capacity = scenario_4_data["model_params"]["rwh_tank_capacity"]["param_val"]
    gw_tank_capacity = scenario_4_data["model_params"]["gw_tank_capacity"]["param_val"]


    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_4_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    # There two new columns in Scenario 4 as opposed to Scenario 3 which are wc_students_demand_logger_id_65 and
    # total_shelter_wc_demand_logger_id_204

    shelter_demand_ts = np.array(scenario_4_data["Output_TS"]["bg_shelter_demand_logger_id_223"][:-12], dtype=np.float64)
    wc_demand_ts = np.array(scenario_4_data["Output_TS"]["wc_students_demand_logger_id_65"][:-12], dtype=np.float64)
    shelter_wc_demand_ts = np.array(scenario_4_data["Output_TS"]["total_shelter_wc_demand_logger_id_204"][:-12], dtype=np.float64)
    gw_ts = np.array(scenario_4_data["Output_TS"]["total_gw_logger_id_108"][:-12], dtype=np.float64)
    gw_treated_ts = np.array(scenario_4_data["Output_TS"]["gw_treated_logger_id_206"][:-12], dtype=np.float64)
    gw_treatment_spill_ts = np.array(scenario_4_data["Output_TS"]["gw_treatment_spill_id_212"][:-12], dtype=np.float64)
    gw_tank_spill_ts = np.array(scenario_4_data["Output_TS"]["gw_tank_spill_id_208"][:-12], dtype=np.float64)
    gw_water_from_system_ts = np.array(scenario_4_data["Output_TS"]["gw_water_from_system_logger_id_210"][:-12], dtype=np.float64)
    gw_tank_water_storage_ts = np.array(scenario_4_data["Output_TS"]["gw_tank_water_storage_id_202"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    green_roof_demand_ts = np.array(scenario_4_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_4_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_4_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_4_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_4_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_4_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_4_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_4_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)

    # Again some new columns as opposed to Scenarios 1,2
    runoff_ts = np.array(scenario_4_data["Output_TS"]["total_runoff_logger_id_183"][:-12], dtype=np.float64)
    gw_treatment_energy_ts = np.array(scenario_4_data["Output_TS"]["gw_treatm_energy_pot_id_18"][:-12], dtype=np.float64)
    gw_pump_energy_ts = np.array(scenario_4_data["Output_TS"]["gw_pump_energy_pot_id_19"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    demand_ts = np.array(scenario_4_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_4_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_4_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_4_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_4_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_4_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_4_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)

    # New Columns
    potable_water_gw_tank_ts = copy.deepcopy(gw_water_from_system_ts)
    gw_shelter_wc_ts = shelter_wc_demand_ts - potable_water_gw_tank_ts

    gw_shelter_ts = np.array([])
    for i in range(len(gw_shelter_wc_ts)):
        if shelter_demand_ts[i] > gw_shelter_wc_ts[i]:
            gw_shelter_ts = np.append(gw_shelter_ts, gw_shelter_wc_ts[i])
        else:
            gw_shelter_ts = np.append(gw_shelter_ts, shelter_demand_ts[i])

    potable_water_shelter_ts = shelter_demand_ts - gw_shelter_ts
    gw_wc_ts = gw_shelter_wc_ts - gw_shelter_ts
    potable_water_wc_ts = wc_demand_ts - gw_wc_ts

    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts + shelter_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts + potable_water_shelter_ts
    green_water_total_nbs_ts = rainwater_green_roof_ts + gw_shelter_ts

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)

    sums_shelter_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_shelter = np.zeros((total_months, total_years)) # (12, 8)
    sums_gw_shelter = np.zeros((total_months, total_years)) # (12, 8)

    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))

    # 6 new Columns from Scenario 3
    sums_wc_demand = np.zeros((total_months, total_years))
    sums_gw_wc = np.zeros((total_months, total_years))
    sums_potable_water_wc = np.zeros((total_months, total_years))
    sums_shelter_wc_demand = np.zeros((total_months, total_years))
    sums_gw_shelter_wc = np.zeros((total_months, total_years))
    sums_potable_water_gw_tank = np.zeros((total_months, total_years))

    sums_gw_tank_spill = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]

        sums_shelter_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += shelter_demand_ts[i]
        sums_potable_water_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_shelter_ts[i]
        sums_gw_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_shelter_ts[i]

        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]

        # 6 new Columns from Scenario 3
        sums_wc_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += wc_demand_ts[i]
        sums_gw_wc[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_wc_ts[i]
        sums_potable_water_wc[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_wc_ts[i]
        sums_shelter_wc_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += shelter_wc_demand_ts[i]
        sums_gw_shelter_wc[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_shelter_wc_ts[i]
        sums_potable_water_gw_tank[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_gw_tank_ts[i]

        sums_gw_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_tank_spill_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months) # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    for i in dates_months_ts_normalized:
        counter_years[i] += 1

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 22)) # (12, 22) Column 0 --> green_roof_demand averages... Column 21 --> total_nbs_autonomy averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_shelter_demand[i, j]

            averages_monthly[i, 6] += sums_potable_water_shelter[i, j]

            averages_monthly[i, 7] += sums_gw_shelter[i, j]

            averages_monthly[i, 8] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 9] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 10] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 11] += sums_wc_demand[i, j]
            averages_monthly[i, 12] += sums_gw_wc[i, j]
            averages_monthly[i, 13] += sums_potable_water_wc[i, j]
            averages_monthly[i, 14] += sums_shelter_wc_demand[i, j]
            averages_monthly[i, 15] += sums_gw_shelter_wc[i, j]
            averages_monthly[i, 16] += sums_potable_water_gw_tank[i, j]

            averages_monthly[i, 17] += sums_gw_tank_spill[i, j]
            averages_monthly[i, 18] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)
            averages_monthly[i, 9] /= (counter_years[i] * 1000)
            averages_monthly[i, 10] /= (counter_years[i] * 1000)
            averages_monthly[i, 11] /= (counter_years[i] * 1000)
            averages_monthly[i, 12] /= (counter_years[i] * 1000)
            averages_monthly[i, 13] /= (counter_years[i] * 1000)
            averages_monthly[i, 14] /= (counter_years[i] * 1000)
            averages_monthly[i, 15] /= (counter_years[i] * 1000)
            averages_monthly[i, 16] /= (counter_years[i] * 1000)
            averages_monthly[i, 17] /= (counter_years[i] * 1000)
            averages_monthly[i, 18] /= (counter_years[i] * 1000)



    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 19] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 20] = (averages_monthly[i, 7] / averages_monthly[i, 5]) * 100 # NBS3 WATER AUTONOMY
        averages_monthly[i, 21] = (averages_monthly[i, 10] / (averages_monthly[i, 8] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY


    # Calculations Annualy

    total_green_water_used_ts = green_water_total_nbs_ts + gw_wc_ts
    total_energy_consumption_ts = gw_treatment_energy_ts + gw_pump_energy_ts + rwh_pump_energy_ts


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 21)) # (8, 21)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += shelter_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += gw_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += runoff_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 18] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 19] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 20] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 21)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_shelter = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_shelter = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_gw_shelter = np.mean(sums_annualy[:, 7]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 9]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 10]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    nbs3_water_autonomy = (average_annual_gw_shelter / average_annual_demand_shelter) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 11]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, 14]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, 18]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, 15]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, 17]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, 12]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, 19]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, 13]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, 20]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface + shelter_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]


    # Charts data to pass on the frontend
    # numpy arrays are not json supported, so i turn the arrays back to python lists
    chart_1_data_1 = averages_monthly[:, 9].tolist()
    chart_1_data_2 = averages_monthly[:, 10].tolist()
    chart_2_data_1 = averages_monthly[:, 17].tolist()
    chart_2_data_2 = averages_monthly[:, 18].tolist()
    chart_3_data_1 = total_nbs_demand_ts.tolist()
    chart_3_data_2 = rainfall_ts_mm.tolist()

    return render_template('scenario_4.html', title="Scenario 4", scenario_4_data=scenario_4_data,
                        annual_calculations_ei=annual_calculations_ei, annual_calculations_categories=annual_calculations_categories,
                        annual_calculations_values=annual_calculations_values, averages_monthly=averages_monthly,
                        chart_1_data_1=json.dumps(chart_1_data_1), chart_1_data_2=json.dumps(chart_1_data_2),
                        chart_2_data_1=json.dumps(chart_2_data_1), chart_2_data_2=json.dumps(chart_2_data_2),
                        chart_3_data_1=json.dumps(chart_3_data_1), chart_3_data_2=json.dumps(chart_3_data_2),
                        dates_ts=json.dumps(dates_ts))


@app.route("/scenarios-comparisons")
def comparisons():
    # The Scenarios comparison page requires to have the outputs of all the 5 different scenarios. So, all functions from
    # baseline_scenario() to scenario_4() need to be executed before rendering the comparisons.html page in order to
    # be able to draw the final tables and graphs in the frontend. So I'm just going to copy and paster the codes inside
    # all these functions in here.

    # This is a temporary solution just to get the page finished. If i want to have a more sophisticated solution then
    # i need to think a better way of executing the code inside the other functions.

    # If the code runs slowly, I can consider Just manually typing the required values for the tables/graphs to be drawn.

    # ==================================================================================================================

    # BASELINE SCENARIO SECTION

    # General Parameters
    site_surface = baseline_scenario_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = baseline_scenario_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = baseline_scenario_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = baseline_scenario_data["model_params"]["imprv_roofs_id_8"]["param_val"]

    # Output TS
    # IN ALL FUTURE JSON FILES FIRST A JOB SHOULD BE DONE TO KEEP ONLY THE VALUES OF THE DAYS THAT CORRESPOND TO FULL MONTHS
    # i.e. if i have 20 values for 20 days of one month I should get manually rid of these 20 values from the dataset

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = baseline_scenario_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    gw_ts = np.array(baseline_scenario_data["Output_TS"]["total_gw_logger_id_108"][:-12], dtype=np.float64)
    roofs_runoff_ts = np.array(baseline_scenario_data["Output_TS"]["imprv_roofs_runoff_logger_id_215"][:-12], dtype=np.float64)
    runoff_ts = np.array(baseline_scenario_data["Output_TS"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    demand_ts = np.array(baseline_scenario_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(baseline_scenario_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(baseline_scenario_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(baseline_scenario_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)

    # Calculations Monthly
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

    counter_years = np.zeros(total_months)

    for i in dates_months_ts_normalized:
        counter_years[i] += 1 # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 5)) # (12, 5) Column 0 --> gw averages... Column 4 wastewater averages

    for i in range(sums_gw.shape[0]):
        for j in range(sums_gw.shape[1]):
            averages_monthly[i, 0] += sums_gw[i, j]
            averages_monthly[i, 1] += sums_roofs_runoff[i, j]
            averages_monthly[i, 2] += sums_runoff[i, j]
            averages_monthly[i, 3] += sums_demand[i, j]
            averages_monthly[i, 4] += sums_wastewater[i, j]

        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)


    # Calculations Annualy

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

    # Final annual calculations for output Table

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


    # Let's put what we want from the Baseline Scenario into new variables
    annual_calculations_values_baseline = copy.deepcopy(annual_calculations_values)
    averages_monthly_baseline = copy.deepcopy(averages_monthly)
    sums_annualy_baseline = copy.deepcopy(sums_annualy)

    # ==================================================================================================================


    # SCENARIO 1 SECTION
    # General Parameters
    site_surface = scenario_1_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_1_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_1_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_1_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_1_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_1_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_1_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_1_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_1_data["model_params"]["bg_planters_id_150"]["param_val"]
    rwh_tank_capacity = scenario_1_data["model_params"]["rwh_tank_capacity"]["param_val"]

    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_1_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    green_roof_demand_ts = np.array(scenario_1_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_1_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_1_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_1_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_1_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_1_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_1_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_1_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)
    drainage_ts = np.array(scenario_1_data["Output_TS"]["total_drainage_logger_id_148"][:-12], dtype=np.float64)
    demand_ts = np.array(scenario_1_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_1_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_1_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_1_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_1_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_1_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_1_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)
    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts
    green_water_total_nbs_ts = copy.deepcopy(rainwater_green_roof_ts)

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)
    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]
        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months)

    for i in dates_months_ts_normalized:
        counter_years[i] += 1 # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 11)) # (12, 9) Column 0 --> green_roof_demand averages... Column 8 rwh_tank_spill averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 6] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 7] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 8] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)

    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 9] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 10] = (averages_monthly[i, 7] / (averages_monthly[i, 5] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY


    # Calculations Annualy

    total_green_water_used_ts = copy.deepcopy(green_water_total_nbs_ts)
    total_energy_consumption_ts = copy.deepcopy(rwh_pump_energy_ts)


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 18)) # (8, 18)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += drainage_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 18)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 7]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, -7]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, -3]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, -6]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, -4]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, -9]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, -2]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, -8]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, -1]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]


    # Let's put what we want from Scenario 1 into new variables
    annual_calculations_values_1 = copy.deepcopy(annual_calculations_values)
    averages_monthly_1 = copy.deepcopy(averages_monthly)
    sums_annualy_1 = copy.deepcopy(sums_annualy)

    # ==================================================================================================================


    # SCENARIO 2 SECTION

    # Scenario 2 is exactly the same as Scenario 1. Only difference is that some of the model parameters take different
    # values, but the 2 Excels are identical. So I just copy and paste the code from Scenario 1 and just change the
    # names of the json files

    # General Parameters
    site_surface = scenario_2_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_2_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_2_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_2_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_2_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_2_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_2_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_2_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_2_data["model_params"]["bg_planters_id_150"]["param_val"]
    rwh_tank_capacity = scenario_2_data["model_params"]["rwh_tank_capacity"]["param_val"]

    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_2_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    green_roof_demand_ts = np.array(scenario_2_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_2_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_2_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_2_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_2_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_2_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_2_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_2_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)
    drainage_ts = np.array(scenario_2_data["Output_TS"]["total_drainage_logger_id_148"][:-12], dtype=np.float64)
    demand_ts = np.array(scenario_2_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_2_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_2_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_2_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_2_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_2_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_2_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)
    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts
    green_water_total_nbs_ts = copy.deepcopy(rainwater_green_roof_ts)

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)
    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]
        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months)

    for i in dates_months_ts_normalized:
        counter_years[i] += 1 # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 11)) # (12, 9) Column 0 --> green_roof_demand averages... Column 8 rwh_tank_spill averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 6] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 7] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 8] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)

    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 9] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 10] = (averages_monthly[i, 7] / (averages_monthly[i, 5] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY


    # Calculations Annualy

    total_green_water_used_ts = copy.deepcopy(green_water_total_nbs_ts)
    total_energy_consumption_ts = copy.deepcopy(rwh_pump_energy_ts)


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 18)) # (8, 18)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += drainage_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 18)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 7]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, -7]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, -3]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, -6]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, -4]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, -9]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, -2]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, -8]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, -1]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]

    # Let's transfer all the variables we need from Scenario 2 to the frontend
    annual_calculations_values_2 = copy.deepcopy(annual_calculations_values)
    averages_monthly_2 = copy.deepcopy(averages_monthly)
    sums_annualy_2 = copy.deepcopy(sums_annualy)



    #===================================================================================================================

    # SCENARIO 3 SECTION

    # General Parameters
    site_surface = scenario_3_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_3_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_3_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_3_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_3_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_3_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_3_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_3_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_3_data["model_params"]["bg_planters_id_150"]["param_val"]
    shelter_surface = scenario_3_data["model_params"]["bg_shelter_id_200"]["param_val"]
    rwh_tank_capacity = scenario_3_data["model_params"]["rwh_tank_capacity"]["param_val"]
    gw_tank_capacity = scenario_3_data["model_params"]["gw_tank_capacity"]["param_val"]


    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_3_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    # Fist some new columns for Scenario 3 as opposed to Scenarios 1, 2

    shelter_demand_ts = np.array(scenario_3_data["Output_TS"]["bg_shelter_demand_logger_id_204"][:-12], dtype=np.float64)
    gw_ts = np.array(scenario_3_data["Output_TS"]["total_gw_logger_id_108"][:-12], dtype=np.float64)
    gw_treated_ts = np.array(scenario_3_data["Output_TS"]["gw_treated_logger_id_206"][:-12], dtype=np.float64)
    gw_treatment_spill_ts = np.array(scenario_3_data["Output_TS"]["gw_treatment_spill_id_212"][:-12], dtype=np.float64)
    gw_tank_spill_ts = np.array(scenario_3_data["Output_TS"]["gw_tank_spill_id_208"][:-12], dtype=np.float64)
    gw_water_from_system_ts = np.array(scenario_3_data["Output_TS"]["gw_water_from_system_logger_id_210"][:-12], dtype=np.float64)
    gw_tank_water_storage_ts = np.array(scenario_3_data["Output_TS"]["gw_tank_water_storage_id_202"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    green_roof_demand_ts = np.array(scenario_3_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_3_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_3_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_3_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_3_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_3_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_3_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_3_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)

    # Again some new columns as opposed to Scenarios 1,2
    runoff_ts = np.array(scenario_3_data["Output_TS"]["total_runoff_logger_id_183"][:-12], dtype=np.float64)
    gw_treatment_energy_ts = np.array(scenario_3_data["Output_TS"]["gw_treatm_energy_pot_id_18"][:-12], dtype=np.float64)
    gw_pump_energy_ts = np.array(scenario_3_data["Output_TS"]["gw_pump_energy_pot_id_19"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    demand_ts = np.array(scenario_3_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_3_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_3_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_3_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_3_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_3_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_3_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)

    # Shelter new columns
    potable_water_shelter_ts = copy.deepcopy(gw_water_from_system_ts)
    gw_shelter_ts = shelter_demand_ts - potable_water_shelter_ts

    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts + shelter_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts + potable_water_shelter_ts
    green_water_total_nbs_ts = rainwater_green_roof_ts + gw_shelter_ts

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)

    sums_shelter_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_shelter = np.zeros((total_months, total_years)) # (12, 8)
    sums_gw_shelter = np.zeros((total_months, total_years)) # (12, 8)

    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))

    sums_gw_tank_spill = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]

        sums_shelter_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += shelter_demand_ts[i]
        sums_potable_water_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_shelter_ts[i]
        sums_gw_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_shelter_ts[i]

        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]

        sums_gw_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_tank_spill_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months) # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    for i in dates_months_ts_normalized:
        counter_years[i] += 1

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 16)) # (12, 16) Column 0 --> green_roof_demand averages... Column 15 --> total_nbs_autonomy averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_shelter_demand[i, j]

            averages_monthly[i, 6] += sums_potable_water_shelter[i, j]

            averages_monthly[i, 7] += sums_gw_shelter[i, j]

            averages_monthly[i, 8] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 9] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 10] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 11] += sums_gw_tank_spill[i, j]

            averages_monthly[i, 12] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)
            averages_monthly[i, 9] /= (counter_years[i] * 1000)
            averages_monthly[i, 10] /= (counter_years[i] * 1000)
            averages_monthly[i, 11] /= (counter_years[i] * 1000)
            averages_monthly[i, 12] /= (counter_years[i] * 1000)


    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 13] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 14] = (averages_monthly[i, 7] / averages_monthly[i, 5]) * 100 # NBS3 WATER AUTONOMY
        averages_monthly[i, 15] = (averages_monthly[i, 10] / (averages_monthly[i, 8] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY

    # Calculations Annualy

    total_green_water_used_ts = copy.deepcopy(green_water_total_nbs_ts)
    total_energy_consumption_ts = gw_treatment_energy_ts + gw_pump_energy_ts + rwh_pump_energy_ts


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 21)) # (8, 21)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += shelter_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += gw_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += runoff_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 18] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 19] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 20] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 21)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_shelter = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_shelter = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_gw_shelter = np.mean(sums_annualy[:, 7]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 9]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 10]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    nbs3_water_autonomy = (average_annual_gw_shelter / average_annual_demand_shelter) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 11]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, 14]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, 18]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, 15]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, 17]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, 12]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, 19]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, 13]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, 20]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface + shelter_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]


    # Let's copy all the variables we will need to the frontend

    annual_calculations_values_3 = copy.deepcopy(annual_calculations_values)
    averages_monthly_3 = copy.deepcopy(averages_monthly)
    sums_annualy_3 = copy.deepcopy(sums_annualy)



    #===================================================================================================================

    # SCENARIO 4 SECTION

    # Scenario 4 is similar to Scenario 3 there some minor addings due to the Shelter WC being installed

    # General Parameters
    site_surface = scenario_4_data["general_params"]["total_site_surface"]["param_val"]
    existing_green_surface = scenario_4_data["general_params"]["existing_green_surfaces"]["param_val"]
    impervious_surface_baseline = scenario_4_data["general_params"]["imp_surf_baseline"]["param_val"]

    # Model Parameters
    impervious_surface = scenario_4_data["model_params"]["imprv_roofs_id_8"]["param_val"]
    green_roof_pavement_surface = scenario_4_data["model_params"]["imprv_permeable_pavement_id_151"]["param_val"]
    rwh_roofs_area = scenario_4_data["model_params"]["imprv_rwh_roofs_id_158"]["param_val"]
    semi_intensive_green_roof_surface = scenario_4_data["model_params"]["bg_green_roof_semintensive_id_149"]["param_val"]
    extensive_green_roof_surface = scenario_4_data["model_params"]["bg_green_roof_extensive_id_120"]["param_val"]
    planters_surface = scenario_4_data["model_params"]["bg_planters_id_150"]["param_val"]
    shelter_surface = scenario_4_data["model_params"]["bg_shelter_id_200"]["param_val"]
    rwh_tank_capacity = scenario_4_data["model_params"]["rwh_tank_capacity"]["param_val"]
    gw_tank_capacity = scenario_4_data["model_params"]["gw_tank_capacity"]["param_val"]


    # Output TS

    # in all the arrays i take the values [:-12] because the last 12 values are for the July of 2021 which is not a full month
    # so it is excluded from all calculations

    dates_ts = scenario_4_data["Output_TS"]["date"][:-12]
    dates_years_ts = np.array([datetime.strptime(date, '%Y-%m-%d').year for date in dates_ts], dtype=np.int32)
    dates_months_ts = np.array([datetime.strptime(date, '%Y-%m-%d').month for date in dates_ts], dtype=np.int32)

    # There two new columns in Scenario 4 as opposed to Scenario 3 which are wc_students_demand_logger_id_65 and
    # total_shelter_wc_demand_logger_id_204

    shelter_demand_ts = np.array(scenario_4_data["Output_TS"]["bg_shelter_demand_logger_id_223"][:-12], dtype=np.float64)
    wc_demand_ts = np.array(scenario_4_data["Output_TS"]["wc_students_demand_logger_id_65"][:-12], dtype=np.float64)
    shelter_wc_demand_ts = np.array(scenario_4_data["Output_TS"]["total_shelter_wc_demand_logger_id_204"][:-12], dtype=np.float64)
    gw_ts = np.array(scenario_4_data["Output_TS"]["total_gw_logger_id_108"][:-12], dtype=np.float64)
    gw_treated_ts = np.array(scenario_4_data["Output_TS"]["gw_treated_logger_id_206"][:-12], dtype=np.float64)
    gw_treatment_spill_ts = np.array(scenario_4_data["Output_TS"]["gw_treatment_spill_id_212"][:-12], dtype=np.float64)
    gw_tank_spill_ts = np.array(scenario_4_data["Output_TS"]["gw_tank_spill_id_208"][:-12], dtype=np.float64)
    gw_water_from_system_ts = np.array(scenario_4_data["Output_TS"]["gw_water_from_system_logger_id_210"][:-12], dtype=np.float64)
    gw_tank_water_storage_ts = np.array(scenario_4_data["Output_TS"]["gw_tank_water_storage_id_202"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    green_roof_demand_ts = np.array(scenario_4_data["Output_TS"]["total_green_roof_demand_logger_id_153"][:-12], dtype=np.float64)
    planters_demand_ts = np.array(scenario_4_data["Output_TS"]["bg_planters_demand_logger_id_176"][:-12], dtype=np.float64)
    rwh_ts = np.array(scenario_4_data["Output_TS"]["rwh_logger_id_180"][:-12], dtype=np.float64)
    rwh_tank_spill_ts = np.array(scenario_4_data["Output_TS"]["rwh_tank_spill_id_163"][:-12], dtype=np.float64)
    rwh_water_from_system_ts = np.array(scenario_4_data["Output_TS"]["rwh_water_from_system_logger_id_170"][:-12], dtype=np.float64)
    rwh_tank_water_storage_ts = np.array(scenario_4_data["Output_TS"]["rwh_tank_water_storage_id_155"][:-12], dtype=np.float64)
    impervious_roofs_runoff_ts = np.array(scenario_4_data["Output_TS"]["imprv_roofs_runoff_logger_id_57"][:-12], dtype=np.float64)
    impervious_pavement_runoff_ts = np.array(scenario_4_data["Output_TS"]["imprv_permeable_pavement_runoff_logger_id_172"][:-12], dtype=np.float64)

    # Again some new columns as opposed to Scenarios 1,2
    runoff_ts = np.array(scenario_4_data["Output_TS"]["total_runoff_logger_id_183"][:-12], dtype=np.float64)
    gw_treatment_energy_ts = np.array(scenario_4_data["Output_TS"]["gw_treatm_energy_pot_id_18"][:-12], dtype=np.float64)
    gw_pump_energy_ts = np.array(scenario_4_data["Output_TS"]["gw_pump_energy_pot_id_19"][:-12], dtype=np.float64)

    # Then the same columns as Scenarios 1,2
    demand_ts = np.array(scenario_4_data["Output_TS"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    wastewater_ts = np.array(scenario_4_data["Output_TS"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)
    rwh_pump_energy_ts = np.array(scenario_4_data["Output_TS"]["rwh_pump_energy_pot_id_16"][:-12], dtype=np.float64)


    # Input TS
    rainfall_ts_mm = np.array(scenario_4_data["Input_TS"]["Rainfall_series_id_1633_group_id_15"][:-12], dtype=np.float64)
    rainfall_ts_m3 = rainfall_ts_mm * (impervious_surface_baseline / 1000)

    # Output TS Baseline
    demand_ts_baseline = np.array(scenario_4_data["Output_TS_baseline"]["total_demand_logger_id_54"][:-12], dtype=np.float64)
    runoff_ts_baseline = np.array(scenario_4_data["Output_TS_baseline"]["total_runoff_logger_id_129"][:-12], dtype=np.float64)
    wastewater_ts_baseline = np.array(scenario_4_data["Output_TS_baseline"]["total_wastewater_logger_id_55"][:-12], dtype=np.float64)


    # Calculations Monthly
    total_years = dates_years_ts[-1] - dates_years_ts[0] + 1 # 8 years
    total_months = max(dates_months_ts) - min(dates_months_ts) + 1 # 12 months

    dates_years_ts_normalized = dates_years_ts - 2014 # this array takes values from 0 to 7 (0-->2014 ... 7-->2021)
    dates_months_ts_normalized = dates_months_ts - 1 # this array takes values from 0 to 11 (0-->January ... 11-->December)

    potable_water_green_roof_ts = copy.deepcopy(rwh_water_from_system_ts)
    rainwater_green_roof_ts = green_roof_demand_ts - potable_water_green_roof_ts
    potable_water_planters_ts = copy.deepcopy(planters_demand_ts)

    # New Columns
    potable_water_gw_tank_ts = copy.deepcopy(gw_water_from_system_ts)
    gw_shelter_wc_ts = shelter_wc_demand_ts - potable_water_gw_tank_ts

    gw_shelter_ts = np.array([])
    for i in range(len(gw_shelter_wc_ts)):
        if shelter_demand_ts[i] > gw_shelter_wc_ts[i]:
            gw_shelter_ts = np.append(gw_shelter_ts, gw_shelter_wc_ts[i])
        else:
            gw_shelter_ts = np.append(gw_shelter_ts, shelter_demand_ts[i])

    potable_water_shelter_ts = shelter_demand_ts - gw_shelter_ts
    gw_wc_ts = gw_shelter_wc_ts - gw_shelter_ts
    potable_water_wc_ts = wc_demand_ts - gw_wc_ts

    total_nbs_demand_ts = green_roof_demand_ts + planters_demand_ts + shelter_demand_ts
    potable_water_total_nbs = potable_water_green_roof_ts + potable_water_planters_ts + potable_water_shelter_ts
    green_water_total_nbs_ts = rainwater_green_roof_ts + gw_shelter_ts

    sums_green_roof_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_rainwater_green_roof = np.zeros((total_months, total_years)) # (12, 8)
    sums_planters_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_planters = np.zeros((total_months, total_years)) # (12, 8)

    sums_shelter_demand = np.zeros((total_months, total_years)) # (12, 8)
    sums_potable_water_shelter = np.zeros((total_months, total_years)) # (12, 8)
    sums_gw_shelter = np.zeros((total_months, total_years)) # (12, 8)

    sums_total_nbs_demand = np.zeros((total_months, total_years))
    sums_total_nbs_potable_water = np.zeros((total_months, total_years))
    sums_green_water_total_nbs = np.zeros((total_months, total_years))

    # 6 new Columns from Scenario 3
    sums_wc_demand = np.zeros((total_months, total_years))
    sums_gw_wc = np.zeros((total_months, total_years))
    sums_potable_water_wc = np.zeros((total_months, total_years))
    sums_shelter_wc_demand = np.zeros((total_months, total_years))
    sums_gw_shelter_wc = np.zeros((total_months, total_years))
    sums_potable_water_gw_tank = np.zeros((total_months, total_years))

    sums_gw_tank_spill = np.zeros((total_months, total_years))
    sums_rwh_tank_spill = np.zeros((total_months, total_years))

    for i in range(len(dates_ts)):
        sums_green_roof_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_roof_demand_ts[i]
        sums_potable_water_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_green_roof_ts[i]
        sums_rainwater_green_roof[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rainwater_green_roof_ts[i]
        sums_planters_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += planters_demand_ts[i]
        sums_potable_water_planters[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_planters_ts[i]

        sums_shelter_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += shelter_demand_ts[i]
        sums_potable_water_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_shelter_ts[i]
        sums_gw_shelter[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_shelter_ts[i]

        sums_total_nbs_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += total_nbs_demand_ts[i]
        sums_total_nbs_potable_water[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_total_nbs[i]
        sums_green_water_total_nbs[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += green_water_total_nbs_ts[i]

        # 6 new Columns from Scenario 3
        sums_wc_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += wc_demand_ts[i]
        sums_gw_wc[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_wc_ts[i]
        sums_potable_water_wc[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_wc_ts[i]
        sums_shelter_wc_demand[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += shelter_wc_demand_ts[i]
        sums_gw_shelter_wc[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_shelter_wc_ts[i]
        sums_potable_water_gw_tank[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += potable_water_gw_tank_ts[i]

        sums_gw_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += gw_tank_spill_ts[i]
        sums_rwh_tank_spill[dates_months_ts_normalized[i], dates_years_ts_normalized[i]] += rwh_tank_spill_ts[i]

    counter_years = np.zeros(total_months) # this is a way to now how many FULL Januries, Februaries etc. exist in the dataset

    for i in dates_months_ts_normalized:
        counter_years[i] += 1

    counter_years[0] = int(counter_years[0] / 31) # January has 31 days
    counter_years[1] = int(counter_years[1] / 28) # February has 28 or 29 days
    counter_years[2] = int(counter_years[2] / 31) # March has 31 days
    counter_years[3] = int(counter_years[3] / 30) # April has 30 days
    counter_years[4] = int(counter_years[4] / 31)
    counter_years[5] = int(counter_years[5] / 30)
    counter_years[6] = int(counter_years[6] / 31)
    counter_years[7] = int(counter_years[7] / 31)
    counter_years[8] = int(counter_years[8] / 30)
    counter_years[9] = int(counter_years[9] / 31)
    counter_years[10] = int(counter_years[10] / 30)
    counter_years[11] = int(counter_years[11] / 31)

    counter_years = counter_years.astype('int')

    averages_monthly = np.zeros((total_months, 22)) # (12, 22) Column 0 --> green_roof_demand averages... Column 21 --> total_nbs_autonomy averages

    for i in range(sums_green_roof_demand.shape[0]):

        for j in range(sums_green_roof_demand.shape[1]):
            averages_monthly[i, 0] += sums_green_roof_demand[i, j]

            averages_monthly[i, 1] += sums_potable_water_green_roof[i, j]

            averages_monthly[i, 2] += sums_rainwater_green_roof[i, j]

            averages_monthly[i, 3] += sums_planters_demand[i, j]

            averages_monthly[i, 4] += sums_potable_water_planters[i, j]

            averages_monthly[i, 5] += sums_shelter_demand[i, j]

            averages_monthly[i, 6] += sums_potable_water_shelter[i, j]

            averages_monthly[i, 7] += sums_gw_shelter[i, j]

            averages_monthly[i, 8] += sums_total_nbs_demand[i, j]

            averages_monthly[i, 9] += sums_total_nbs_potable_water[i, j]

            averages_monthly[i, 10] += sums_green_water_total_nbs[i, j]

            averages_monthly[i, 11] += sums_wc_demand[i, j]
            averages_monthly[i, 12] += sums_gw_wc[i, j]
            averages_monthly[i, 13] += sums_potable_water_wc[i, j]
            averages_monthly[i, 14] += sums_shelter_wc_demand[i, j]
            averages_monthly[i, 15] += sums_gw_shelter_wc[i, j]
            averages_monthly[i, 16] += sums_potable_water_gw_tank[i, j]

            averages_monthly[i, 17] += sums_gw_tank_spill[i, j]
            averages_monthly[i, 18] += sums_rwh_tank_spill[i, j]


        if counter_years[i] != 0:
            averages_monthly[i, 0] /= (counter_years[i] * 1000) # we also divide by 1000 to turn L into m3
            averages_monthly[i, 1] /= (counter_years[i] * 1000)
            averages_monthly[i, 2] /= (counter_years[i] * 1000)
            averages_monthly[i, 3] /= (counter_years[i] * 1000)
            averages_monthly[i, 4] /= (counter_years[i] * 1000)
            averages_monthly[i, 5] /= (counter_years[i] * 1000)
            averages_monthly[i, 6] /= (counter_years[i] * 1000)
            averages_monthly[i, 7] /= (counter_years[i] * 1000)
            averages_monthly[i, 8] /= (counter_years[i] * 1000)
            averages_monthly[i, 9] /= (counter_years[i] * 1000)
            averages_monthly[i, 10] /= (counter_years[i] * 1000)
            averages_monthly[i, 11] /= (counter_years[i] * 1000)
            averages_monthly[i, 12] /= (counter_years[i] * 1000)
            averages_monthly[i, 13] /= (counter_years[i] * 1000)
            averages_monthly[i, 14] /= (counter_years[i] * 1000)
            averages_monthly[i, 15] /= (counter_years[i] * 1000)
            averages_monthly[i, 16] /= (counter_years[i] * 1000)
            averages_monthly[i, 17] /= (counter_years[i] * 1000)
            averages_monthly[i, 18] /= (counter_years[i] * 1000)



    for i in range(averages_monthly.shape[0]): # THERE ARE TWO MORE COLUMNS IN THE EXCEL
        averages_monthly[i, 19] = (averages_monthly[i, 2] / averages_monthly[i, 0]) * 100 # NBS1 WATER AUTONOMY
        averages_monthly[i, 20] = (averages_monthly[i, 7] / averages_monthly[i, 5]) * 100 # NBS3 WATER AUTONOMY
        averages_monthly[i, 21] = (averages_monthly[i, 10] / (averages_monthly[i, 8] - averages_monthly[i, 3])) * 100 # TOTAL NBS WATER AUTONOMY


    # Calculations Annualy

    total_green_water_used_ts = green_water_total_nbs_ts + gw_wc_ts
    total_energy_consumption_ts = gw_treatment_energy_ts + gw_pump_energy_ts + rwh_pump_energy_ts


    # from Calculations_annual workseet, table with columns from 'Sum of Water demand Green roof (NBS1) ' to 'Sum of Wastewater volume baseline scenario'
    sums_annualy = np.zeros((total_years, 21)) # (8, 21)

    days_years = np.array([])
    for i in range(8): # years go from 2014 to 2021 ~ 8 years
        days_years = np.append(days_years, len(dates_years_ts_normalized[dates_years_ts_normalized==i]))

    for i in range(len(dates_ts)):
        sums_annualy[dates_years_ts_normalized[i], 0] += green_roof_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 1] += potable_water_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 2] += rainwater_green_roof_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 3] += planters_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 4] += potable_water_planters_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 5] += shelter_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 6] += potable_water_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 7] += gw_shelter_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 8] += total_nbs_demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 9] += potable_water_total_nbs[i]
        sums_annualy[dates_years_ts_normalized[i], 10] += green_water_total_nbs_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 11] += demand_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 12] += runoff_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 13] += wastewater_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 14] += total_green_water_used_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 15] += total_energy_consumption_ts[i]
        sums_annualy[dates_years_ts_normalized[i], 16] += rainfall_ts_mm[i]
        sums_annualy[dates_years_ts_normalized[i], 17] += rainfall_ts_m3[i]
        sums_annualy[dates_years_ts_normalized[i], 18] += demand_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 19] += runoff_ts_baseline[i]
        sums_annualy[dates_years_ts_normalized[i], 20] += wastewater_ts_baseline[i]

    for i in range(8):
        if days_years[i] < 364: # if it's not a full year we dont want to output anything for the specific year
            sums_annualy[i, :] = 0

    sums_annualy = sums_annualy[sums_annualy != 0].reshape(-1, 21)

    # Final calculations to produce the final output table

    average_annual_demand_green_roof = np.mean(sums_annualy[:, 0]) / 1000  # m3
    average_annual_potable_water_green_roof = np.mean(sums_annualy[:, 1]) / 1000  # m3
    average_annual_rainwater_green_roof = np.mean(sums_annualy[:, 2]) / 1000  # m3
    average_annual_demand_planters = np.mean(sums_annualy[:, 3]) / 1000  # m3
    average_annual_potable_water_planters = np.mean(sums_annualy[:, 4]) / 1000  # m3
    average_annual_demand_shelter = np.mean(sums_annualy[:, 5]) / 1000  # m3
    average_annual_potable_water_shelter = np.mean(sums_annualy[:, 6]) / 1000  # m3
    average_annual_gw_shelter = np.mean(sums_annualy[:, 7]) / 1000  # m3
    average_annual_demand_total_nbs = np.mean(sums_annualy[:, 8]) / 1000  # m3
    average_annual_potable_water_total_nbs = np.mean(sums_annualy[:, 9]) / 1000  # m3
    average_annual_green_water_total_nbs = np.mean(sums_annualy[:, 10]) / 1000  # m3
    nbs1_water_autonomy = (average_annual_rainwater_green_roof / average_annual_demand_green_roof) * 100
    nbs3_water_autonomy = (average_annual_gw_shelter / average_annual_demand_shelter) * 100
    total_nbs_water_autonomy = (average_annual_green_water_total_nbs / (average_annual_demand_total_nbs - average_annual_demand_planters)) * 100
    average_annual_demand = np.mean(sums_annualy[:, 11]) / 1000  # m3
    average_annual_green_water_used = np.mean(sums_annualy[:, 14]) / 1000  # m3
    water_reuse = (average_annual_green_water_used / average_annual_demand) * 100
    average_annual_demand_baseline = np.mean(sums_annualy[:, 18]) / 1000  # m3
    potable_water_savings = -((average_annual_demand - average_annual_demand_baseline) / average_annual_demand_baseline) * 100
    average_annual_energy_consumption = np.mean(sums_annualy[:, 15]) # m3
    average_annual_rainfall_m3 = np.mean(sums_annualy[:, 17]) # m3
    average_annual_runoff = np.mean(sums_annualy[:, 12]) / 1000  # m3
    runoff_coeff = (average_annual_runoff / average_annual_rainfall_m3) * 100
    average_annual_runoff_baseline = np.mean(sums_annualy[:, 19]) / 1000  # m3
    stormwater_treated_locally = ((average_annual_runoff_baseline - average_annual_runoff) / average_annual_runoff_baseline) * 100
    average_annual_wastewater = np.mean(sums_annualy[:, 13]) / 1000  # m3
    average_annual_wastewater_baseline = np.mean(sums_annualy[:, 20]) / 1000  # m3
    wastewater_treated_locally = ((average_annual_wastewater_baseline - average_annual_wastewater) / average_annual_wastewater_baseline) * 100
    total_impervious_surface = impervious_surface + green_roof_pavement_surface + rwh_roofs_area
    impervious_surface_percentage = (total_impervious_surface / site_surface) * 100
    total_green_nbs_surface = semi_intensive_green_roof_surface + extensive_green_roof_surface + planters_surface + shelter_surface
    total_green_surface = existing_green_surface + total_green_nbs_surface
    green_surface_percentage = (total_green_surface / site_surface) * 100
    total_nbs_surface = total_green_nbs_surface + green_roof_pavement_surface - planters_surface

    annual_calculations_values = [total_nbs_water_autonomy, water_reuse, potable_water_savings, average_annual_energy_consumption,
                                  runoff_coeff, stormwater_treated_locally, wastewater_treated_locally, impervious_surface_percentage,
                                  green_surface_percentage]


    # Let's copy all the variables we will need to the frontend

    annual_calculations_values_4 = copy.deepcopy(annual_calculations_values)
    averages_monthly_4 = copy.deepcopy(averages_monthly)
    sums_annualy_4 = copy.deepcopy(sums_annualy)


    return render_template('comparisons.html', title="Scenarios Comparisons", baseline_scenario_data=baseline_scenario_data,
                           scenario_1_data=scenario_1_data, scenario_2_data=scenario_2_data, scenario_3_data=scenario_3_data,
                           scenario_4_data=scenario_4_data,


                           # BASELINE SCENARIO SECTION
                           annual_calculations_values_baseline=annual_calculations_values_baseline,
                           averages_monthly_baseline=averages_monthly_baseline,
                           sums_annualy_baseline=sums_annualy_baseline,


                           # SCENARIO 1 SECTION
                           annual_calculations_values_1=annual_calculations_values_1,
                           averages_monthly_1=averages_monthly_1, sums_annualy_1=sums_annualy_1,


                           # SCENARIO 2 SECTION
                           annual_calculations_values_2=annual_calculations_values_2,
                           averages_monthly_2=averages_monthly_2, sums_annualy_2=sums_annualy_2,


                           # SCENARIO 3 SECTION
                           annual_calculations_values_3=annual_calculations_values_3,
                           averages_monthly_3=averages_monthly_3, sums_annualy_3=sums_annualy_3,


                           # SCENARIO 4 SECTION
                           annual_calculations_values_4=annual_calculations_values_4,
                           averages_monthly_4=averages_monthly_4, sums_annualy_4=sums_annualy_4
                           )


if __name__ == "__main__":
    app.run(debug=True)
