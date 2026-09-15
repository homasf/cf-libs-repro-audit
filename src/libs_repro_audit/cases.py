"""Recompute the manuscript's five bounded literature demonstrations.

Run: python -m libs_repro_audit.cases --output output/case_results.json
These operations reconstruct printed arithmetic, not original experiments.
"""
from __future__ import annotations

import argparse
import json
import math
from importlib import resources
from pathlib import Path

from .audit import (KB_EV_K, convert_composition, mcwhirter_threshold,
                    signed_relative_deviation, stark_ne, voigt_lorentzian_fwhm,
                    finite_number)


def boltzmann_fit(lines: list[dict]) -> dict:
    """Unweighted OLS of ln[(I/I0)(lambda/lambda0)/(g A/A0)] vs E in eV.

    References are 1 arbitrary intensity unit, 1 nm, 1e8 s^-1.
    A common rescaling of y changes the intercept but not temperature.
    No experimental uncertainty or radiometric correction is inferred.
    """
    if len(lines) < 3:
        raise ValueError('at least three lines are required for this fit')
    x, y = [], []
    for line in lines:
        for key in ('wavelength_nm', 'intensity', 'g', 'A_1e8_s', 'energy_ev'):
            finite_number(line[key], key)
        if any(line[k] <= 0 for k in ('wavelength_nm', 'intensity', 'g', 'A_1e8_s')):
            raise ValueError('line wavelengths, intensities, weights and A must be positive')
        x.append(line['energy_ev'])
        y.append(math.log(line['intensity'] * line['wavelength_nm'] /
                          (line['g'] * line['A_1e8_s'])))
    xm, ym = math.fsum(x)/len(x), math.fsum(y)/len(y)
    sxx = math.fsum((a-xm)**2 for a in x)
    if not sxx:
        raise ValueError('upper-level energies must span a nonzero range')
    m = math.fsum((a-xm)*(b-ym) for a, b in zip(x, y))/sxx
    if m >= 0:
        raise ValueError('a nonnegative Boltzmann slope gives no positive temperature')
    intercept = ym-m*xm
    residual = math.fsum((b-(intercept+m*a))**2 for a, b in zip(x, y))
    total = math.fsum((b-ym)**2 for b in y)
    return {'temperature_K': -1/(KB_EV_K*m), 'slope_ev_inverse': m,
            'intercept_scaled': intercept, 'r_squared': 1-residual/total}


def recompute(data: dict) -> dict:
    result = {'verification': data['verification'], 'scope': data['scope'],
              'sources': data['sources']}
    result['soil_validation'] = [dict(row,
        delta_ne_percent=signed_relative_deviation(row['ne_estimate'], row['reference']),
        delta_te_percent=signed_relative_deviation(row['te_estimate'], row['reference']))
        for row in data['soil_validation']]
    result['alloy_validation'] = [dict(row,
        delta_cu_percent=signed_relative_deviation(row['cu_wt_percent'], 20),
        delta_fe_percent=signed_relative_deviation(row['fe_wt_percent'], 80))
        for row in data['alloy_validation']]
    ratios = []
    for pair in data['alloy_ratios']:
        a, b = pair['lines']
        measured = a['intensity']/b['intensity']
        theory = (a['A_s']*a['g']*b['wavelength_nm'] /
                  (b['A_s']*b['g']*a['wavelength_nm']) *
                  math.exp(-(a['energy_ev']-b['energy_ev'])/pair['kT_ev']))
        ratios.append({'element': pair['element'], 'measured_ratio': measured,
                       'theoretical_ratio': theory,
                       'difference_percent': signed_relative_deviation(measured, theory)})
    result['alloy_ratios'] = ratios
    result['alloy_plasma'] = {
        'mcwhirter_cm3': mcwhirter_threshold(.69, 3.04, 'eV'),
        'literal_unit_inconsistent_substitution': 1.6e12*math.sqrt(.69)*3.04**3,
        'density_relative_difference_percent': signed_relative_deviation(3.9e16, 2.73e16)}
    plant = []
    for row in data['plant_validation']:
        delta = signed_relative_deviation(row['cf_libs'], row['reference'])
        required = row['ra_printed']*row['reference'] - abs(row['cf_libs']-row['reference'])
        max_term = row['sd_printed']*12.7062047364321/math.sqrt(2)
        plant.append(dict(row, delta_percent=delta,
            rsd_percent_conditional=100*row['sd_printed']/row['cf_libs'],
            ra_percent_below_floor=row['ra_printed'] < abs(delta),
            fraction_required_confidence=required,
            fraction_upper_bound=max_term,
            fraction_not_excluded_by_bound=(0 <= required <= max_term)))
    result['plant_validation'] = plant
    result['plant_summary'] = {
        'counts_over_1_5_10_percent': [sum(abs(r['delta_percent']) > t+1e-10 for r in plant) for t in (1,5,10)],
        'ra_percent_below_floor_count': sum(r['ra_percent_below_floor'] for r in plant),
        'ra_fraction_excluded_count': sum(not r['fraction_not_excluded_by_bound'] for r in plant),
        'concentration_total_mg_kg': math.fsum(r['cf_libs'] for r in plant)}
    scenario_width = voigt_lorentzian_fwhm(.06575, .06)
    result['plant_plasma'] = dict(boltzmann_fit(data['plant_lines']),
        mcwhirter_cm3=mcwhirter_threshold(7615, 3.91-1.879),
        total_width_density_cm3=stark_ne(.06575,.0057),
        scenario_lorentzian_width_nm=scenario_width,
        scenario_density_cm3=stark_ne(scenario_width,.0057))
    result['mesbp'] = [dict(row,
        distance_percentage_points=math.fsum(abs(a-b) for a,b in zip(row['composition'],[65,30,5])),
        element_relative_deviations_percent=[signed_relative_deviation(a,b) for a,b in zip(row['composition'],[65,30,5])])
        for row in data['mesbp']]
    conversion = []
    for material in data['mass_mole']:
        rows = material['elements']
        mass = [r['mass_percent'] for r in rows]
        molar = [r['molar_mass_g_mol'] for r in rows]
        mole = convert_composition(mass, molar, 'mass')
        recovered = convert_composition(mole, molar, 'mole')
        conversion.append({'material': material['material'],
            'input_mass_total_percent': math.fsum(mass),
            'round_trip_max_fraction_error': max(abs(a/math.fsum(mass)-b) for a,b in zip(mass,recovered)),
            'elements': [dict(row,mole_percent_calculated=x*100,
                            mole_percentage_point_difference=x*100-row['mole_percent_printed'])
                         for row,x in zip(rows,mole)]})
    result['mass_mole'] = conversion
    return result


def load_cases(path=None):
    if path:
        return json.loads(Path(path).read_text())
    return json.loads(resources.files('libs_repro_audit').joinpath('case_studies.json').read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input')
    parser.add_argument('--output', default='output/case_results.json')
    args=parser.parse_args()
    result=recompute(load_cases(args.input))
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Literature calculations written to {target}')


if __name__ == '__main__':
    main()
