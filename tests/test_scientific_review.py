import copy
import math
import pytest

from libs_repro_audit.audit import (
    convert_composition, inverse_rounding_interval, mcwhirter_threshold,
    voigt_lorentzian_fwhm, quadrature_corrected_fwhm, stark_ne,
    signed_relative_deviation, LinearEquation,
)
from libs_repro_audit.cases import load_cases, recompute, boltzmann_fit
from libs_repro_audit.engine import run_audit, render_markdown, INFO, NOT_ASSESSED
from libs_repro_audit.htmlreport import render_html
from libs_repro_audit.cli import main


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf'), True])
def test_reject_nonfinite_and_boolean_measurements(bad):
    with pytest.raises(ValueError): signed_relative_deviation(bad, 1)
    with pytest.raises(ValueError): stark_ne(bad, .01)
    with pytest.raises(ValueError): LinearEquation(0,bad)


def test_profile_models_are_not_interchangeable():
    observed, gaussian=.13493, 646.257/75000
    q=quadrature_corrected_fwhm(observed,gaussian)
    l=voigt_lorentzian_fwhm(observed,gaussian)
    # The old claim that quadrature is an upper correction bound is false.
    assert observed-l > observed-q
    reconstructed=.5346*l+math.sqrt(.2166*l*l+gaussian*gaussian)
    assert reconstructed == pytest.approx(observed, rel=1e-12)
    assert voigt_lorentzian_fwhm(.06,.06) == 0
    with pytest.raises(ValueError): voigt_lorentzian_fwhm(.05,.06)


def test_kelvin_and_ev_give_same_mcwhirter_result():
    assert mcwhirter_threshold(.69,3.04,'eV') == pytest.approx(
        mcwhirter_threshold(.69/8.617333262145e-5,3.04))
    assert mcwhirter_threshold(.69,3.04,'eV') == pytest.approx(4.0223405e15,rel=1e-7)


def test_rounding_envelope_and_singular_slope():
    lo,hi=inverse_rounding_interval(1.317,.003488,1.54382,.0005,.0000005,.000005)
    assert lo < 65.02 < hi
    with pytest.raises(ValueError): inverse_rounding_interval(1,.0001,2,b_halfwidth=.001)


def test_no_implicit_five_percent_pass():
    record={'paper':{},'stark_checks':[{'fwhm_nm':.2,'w_s_nm':.1,'ne_comparison_mantissa':1.02}]}
    r=run_audit(record)
    assert r.results[0].status == INFO
    assert any(x.status == NOT_ASSESSED for x in r.results)


def test_zero_expected_inversion_and_unknown_flags():
    record={'paper':{},'equations':[{'a':1,'b':2,'operative_value':1,
                                  'printed_estimate':0,'tolerance_absolute':.001}]}
    assert run_audit(record).results[0].status == 'PASS'
    record['qualitative']={'lte_check_reported':'false'}
    with pytest.raises(ValueError): run_audit(record)


def test_saved_reports_preserve_verification_and_evidence():
    r=run_audit({'paper':{},'verification':'DRAFT UNVERIFIED',
                 'missing':['width'], 'conflicts':['density scale']})
    for rendered in (render_markdown(r),render_html(r)):
        assert 'DRAFT UNVERIFIED' in rendered
        assert 'density scale' in rendered
        assert 'width' in rendered


def test_strict_empty_record_cannot_pass(tmp_path):
    p=tmp_path/'empty.json';p.write_text('{"paper":{}}')
    assert main([str(p),'--strict','--no-color']) == 1


def test_case_recalculations_and_positive_controls():
    r=recompute(load_cases())
    assert r['plant_summary']['counts_over_1_5_10_percent']==[17,6,3]
    assert r['plant_summary']['ra_fraction_excluded_count']==17
    assert r['plant_summary']['concentration_total_mg_kg']==pytest.approx(31893.26)
    assert r['plant_plasma']['temperature_K']==pytest.approx(7525.4261,abs=.001)
    assert r['plant_plasma']['scenario_density_cm3']==pytest.approx(9.115519e15,rel=1e-6)
    assert [x['distance_percentage_points'] for x in r['mesbp']]==[22,6]
    alnico=next(x for x in r['mass_mole'] if x['material']=='Alnico')
    assert max(abs(x['mole_percentage_point_difference']) for x in alnico['elements']) < .005
    assert all(m['round_trip_max_fraction_error'] < 1e-14 for m in r['mass_mole'])


def test_boltzmann_temperature_invariant_to_common_intensity_scale():
    lines=load_cases()['plant_lines']; scaled=copy.deepcopy(lines)
    for row in scaled: row['intensity']*=1e6
    a,b=boltzmann_fit(lines),boltzmann_fit(scaled)
    assert a['temperature_K']==pytest.approx(b['temperature_K'],rel=1e-12)
    assert b['intercept_scaled']-a['intercept_scaled']==pytest.approx(math.log(1e6))


def test_invalid_composition_inputs():
    with pytest.raises(ValueError): convert_composition([0,0],[1,2],'mass')
    with pytest.raises(ValueError): convert_composition([1],[1,2],'mass')
    with pytest.raises(ValueError): convert_composition([1,-1],[1,2],'mass')
