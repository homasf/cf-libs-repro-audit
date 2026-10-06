#!/usr/bin/env python3
"""Check the packaged constructed numerical outputs and LaTeX table bodies.

Run after run_all.py. The 105 numerical and table checks use the supplied
record, outputs and tables. A separate integrity check verifies ten fixed
figure assets and five restored PDF copies. It checks numerical relationships,
printed table values and file identity. It does not read or verify manuscript prose, citation records or
item numbering, and does not validate an experiment or a plasma model.
The calculation scripts retain their separate 76 numerical checks.
Standard library only.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path
import restore_figures

HERE=Path(__file__).resolve().parent
SUPP_DIR=HERE.parent
OUT=SUPP_DIR/'outputs'
REC=SUPP_DIR/'record'
RESULTS=[]

def check(name, condition):
    RESULTS.append((bool(condition),name))

def read(path):
    return path.read_text(encoding='utf-8')

def numbers(text):
    text=re.sub(r'\\(?:ref|eqref|cite|label|includegraphics)\{[^}]*\}','',text)
    text=text.replace(',', '').replace('{,}', '').replace('--',' to ')
    return re.findall(r'(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?(?![A-Za-z_])',text)

def table_path(name):
    return SUPP_DIR/'tables'/name

def table_rows(name):
    path=table_path(name)
    if not any(label==f'printed table source exists: {name}' for _,label in RESULTS):check(f'printed table source exists: {name}',path.exists())
    if not path.exists():return []
    return [[v.strip() for v in line[:-2].split('&')] for line in read(path).splitlines() if line.endswith('\\') and '&' in line]

def cell_values(cell):
    cleaned=cell.strip().strip('$')
    sci=re.fullmatch(r'([+-]?[\d.]+)\\times10\^\{([+-]?\d+)\}',cleaned)
    if sci:return [float(sci[1])*10**int(sci[2])]
    return [float(x) for x in numbers(cleaned)]

def same_numeric_cells(actual,expected):
    try:
        pairs=[(cell_values(a),cell_values(e)) for a,e in zip(actual,expected)]
        return len(actual)==len(expected) and all(len(a)==len(e) and all(math.isclose(x,y,rel_tol=1e-13,abs_tol=1e-12) for x,y in zip(a,e)) for a,e in pairs)
    except (ValueError,TypeError):return False

def all_table_checks(summ,seeded,record):
    rows=table_rows('tableS1_linewidth.tex');source=list(csv.DictReader((OUT/'table_linewidth.csv').open(newline='')))
    check('Table S1: nine rows',len(rows)==len(source)==9)
    for row,data in zip(rows,source):check(f"Table S1 all cells at G/W {data['G_over_W']}",same_numeric_cells(row,list(data.values())))
    rows=table_rows('tableS2_lines.tex');ints={x['line_id']:x for x in csv.DictReader((REC/'line_intensities.csv').open(newline=''))}
    check('Table S2: 21 line rows and 105 replicate intensities',len(rows)==len(record['lines'])==21 and all(len(x)==12 for x in rows))
    for row,line in zip(rows,record['lines']):
        ident=row[0].replace('\\_','_')
        expected=[f"{line['wavelength_nm']:.2f}",f"{line['E_i_eV']:.2f}",f"{line['E_k_eV']:.2f}",str(line['g_k']),str(line['A_ki_s-1'])]+[ints[line['id']][f'replicate_{i}'] for i in range(1,6)]
        check(f"Table S2 {line['id']}: species, atomic values and all five intensities",ident==line['id'] and row[1]==line['species'] and same_numeric_cells(row[2:],expected))
    rows=table_rows('tableS3_summary.tex');check('Table S3: three element rows',len(rows)==3)
    for row in rows:
        e=row[0];v=summ['A5'][e]
        expected=[f"{v['reference']*100:.3f}",f"{summ['A4']['mole_fraction_mean'][e]*100:.3f}",f"{v['mean']*100:.3f}",f"{v['signed_deviation_percent']:.1f}",f"{v['rsd_percent']:.1f}",f"{v['u_repeatability_of_mean']*100:.3f}",f"{v['u_inputs_monte_carlo']*100:.3f}",f"{v['u_combined']*100:.2g}",f"{v['mc_p025']*100:.2f} to {v['mc_p975']*100:.2f}",f"{v['zeta']:.2f}"]
        check(f'Table S3 {e}: all displayed numeric cells',same_numeric_cells(row[1:],expected))
    rows=table_rows('tableS4_seeded.tex');check('Table S4: baseline, interval and 13 perturbation rows',len(rows)==15)
    if len(rows)>=2:
        check('Table S4 baseline ratios',same_numeric_cells(rows[0][-5:],['1.000']*5))
        check('Table S4 95 percent interval endpoints',same_numeric_cells(rows[1][-3:],[f'{lo:.3f} to {hi:.3f}' for lo,hi in seeded['monte_carlo_95_interval_ratio'].values()]))
    rows=table_rows('tableS5_indicators.tex');check('Table S5: baseline, interval and 13 perturbation rows',len(rows)==15)
    if len(rows)>=2:
        b=seeded['baseline'];expected=[f"{b['saha_stark_ratio']:.2f}",f"{b['residual_sd']:.3f}"]+[f"{b['zeta_vs_reference'][e]:.2f}" for e in summ['elements']]
        check('Table S5 baseline numeric cells',same_numeric_cells(rows[0][2:7],expected))
        lo,hi=seeded['saha_stark_ratio_95_range'];sl,sh=seeded['residual_sd_95_range']
        check('Table S5 density and scatter interval endpoints',same_numeric_cells(rows[1][2:4],[f'{lo:.2f} to {hi:.2f}',f'{sl:.3f} to {sh:.3f}']))

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    RESULTS.clear()
    summ=json.loads(read(OUT/'summary.json'));seeded=json.loads(read(OUT/'seeded_defects.json'))
    record=json.loads(read(REC/'record.json'));reported=json.loads(read(REC/'reported_values.json'))
    check('record: 21 lines and five replicates',len(record['lines'])==21 and record['n_replicates']==5)
    check('record: assigned 3 percent intensity noise',record['generation']['intensity_rel_sd']==0.03)
    count=lambda d:sum(1 if 'value' in v else len(v) for v in d.values())
    check('reported record: 18 deterministic and seven Monte Carlo values',count(reported['deterministic'])==18 and count(reported['monte_carlo_based'])==7)
    for element in summ['elements']:
        vals=summ['A4']['mass_fraction_replicates'][element]
        check(f'{element}: JSON mean agrees with replicates',abs(statistics.mean(vals)-summ['A5'][element]['mean'])<1e-14)
        check(f'{element}: JSON sample deviation agrees with replicates',abs(statistics.stdev(vals)-summ['A5'][element]['sd'])<1e-14)
    for i in range(summ['n_replicates']):
        check(f'replicate {i+1}: mass fractions close',abs(sum(summ['A4']['mass_fraction_replicates'][e][i] for e in summ['elements'])-1)<1e-14)
    all_table_checks(summ,seeded,record)
    scenarios={x['id']:x for x in seeded['scenarios']}
    for key,v in scenarios.items():
        row=next((row for row in table_rows('tableS4_seeded.tex') if row[0]==key),[])
        check(f'Table S4 {key}: parameter and composition ratios',len(row)==8 and same_numeric_cells(row[-5:],[f"{v['n_e_ratio']:.3f}",f"{v['temperature_ratio']:.3f}"]+[f"{v['ratio_to_baseline'][e]:.3f}" for e in summ['elements']]))
        row=next((row for row in table_rows('tableS5_indicators.tex') if row[0]==key),[])
        check(f'Table S5 {key}: density ratio, scatter and normalized deviations',len(row)==8 and same_numeric_cells(row[2:7],[f"{v['saha_stark_ratio']:.2f}",f"{v['residual_sd']:.3f}"]+[f"{v['zeta_vs_reference'][e]:.1f}" for e in summ['elements']]))
        flags=', '.join(k[-1] for k in ['flag_D','flag_S','flag_R'] if v[k]) or 'none'
        check(f'Table S5 {key}: detection flags',len(row)==8 and row[7]==flags)
    slips=[v for v in seeded['scenarios'] if v['family']=='slip']
    check('six of nine slips move X outside input interval',[v['id'] for v in slips if v['outside_95_interval']['X']]==['C3','C4','C5','C6','C8','C9'])
    check('all 13 scenario compositions close',all(abs(sum(v['mass_percent'].values())-100)<1e-10 for v in seeded['scenarios']))
    check('density indicator flags C3 to C6',[v['id'] for v in slips if v['flag_D']]==['C3','C4','C5','C6'])
    check('scatter indicator flags C7',[v['id'] for v in slips if v['flag_S']]==['C7'])
    check('reference indicator flags C3 C5 C6 C8 C9',[v['id'] for v in slips if v['flag_R']]==['C3','C5','C6','C8','C9'])
    n_ok=sum(ok for ok,_ in RESULTS)
    text=f'{n_ok} of {len(RESULTS)} numerical and table consistency checks passed.\n\n'
    text+='Scope: supplied constructed inputs, numerical outputs and table bodies.\n'
    text+='These checks do not assess manuscript prose, citations, experiments or published studies.\n\n'
    text+='\n'.join(('PASS' if ok else 'FAIL')+': '+name for ok,name in RESULTS)+'\n'
    (OUT/'check_log_release.txt').write_text(text,encoding='utf-8');print(text)
    try:
        asset_status = restore_figures.verify(log_path=OUT/'check_log_assets.txt')
    except (OSError, ValueError, KeyError, TypeError) as error:
        asset_text = f'FAIL: cannot verify required figure assets: {error}\n'
        (OUT/'check_log_assets.txt').write_text(asset_text, encoding='utf-8')
        print(asset_text)
        asset_status = 1
    passed = n_ok==len(RESULTS) and asset_status == 0
    print('RELEASE CONSISTENCY CHECKS PASSED' if passed else 'RELEASE CONSISTENCY CHECKS FAILED')
    return 0 if passed else 1

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        message = f'FAIL: cannot verify required release files: {error}\n'
        if OUT.is_dir():
            (OUT/'check_log_release.txt').write_text(message, encoding='utf-8')
        print(message)
        raise SystemExit(1)
