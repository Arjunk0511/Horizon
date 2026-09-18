FACTORS={'HFO':3.114,'MDO':3.206,'LNG':2.750}
def calculate_co2(fuel,fuel_type,factors=None): return fuel*(factors or FACTORS)[fuel_type]
