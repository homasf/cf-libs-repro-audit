"""Generate the revised manuscript figure directly from printed case inputs."""
from pathlib import Path
import argparse
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from libs_repro_audit.cases import load_cases, recompute

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='figures/validation_differences.pdf')
    args = parser.parse_args()
    data = recompute(load_cases())
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,
                         'pdf.fonttype':42,'axes.titleweight':'bold'})
    fig = plt.figure(figsize=(9.0,6.5), layout='constrained')
    grid=fig.add_gridspec(2,2,width_ratios=[1.1,1],hspace=.16,wspace=.12)
    soil=fig.add_subplot(grid[0,0]);alloy=fig.add_subplot(grid[1,0]);plant=fig.add_subplot(grid[:,1])
    blue,orange='#24577D','#BD642A'
    y=np.arange(4)
    rows=data['soil_validation']
    soil.barh(y-.17,[r['delta_ne_percent'] for r in rows],height=.3,color=blue,label='Density route')
    soil.barh(y+.17,[r['delta_te_percent'] for r in rows],height=.3,color=orange,label='Temperature route')
    soil.set_yticks(y,[r['element'] for r in rows]);soil.invert_yaxis()
    soil.set_title('(a) Soil: comparison with ICP-OES',loc='left',fontsize=10)
    soil.set_xlim(-10,12);soil.legend(loc='lower right',fontsize=8,frameon=False)
    rows=data['alloy_validation'];v=[r['delta_cu_percent'] for r in rows]
    alloy.barh(y,v,height=.5,color=[blue if x<0 else orange for x in v])
    alloy.set_yticks(y,[r['method'] for r in rows]);alloy.invert_yaxis()
    alloy.set_title('(b) Alloy Cu: comparison with nominal',loc='left',fontsize=10)
    alloy.set_xlim(-13,15)
    for i,x in enumerate(v):alloy.text(x+(.4 if x>=0 else -.4),i,f'{x:+.2f}',va='center',ha='left' if x>=0 else 'right',fontsize=8)
    rows=data['plant_validation'];v=[r['delta_percent'] for r in rows]
    plant.barh(np.arange(len(v)),v,height=.65,color=[blue if x<0 else orange for x in v])
    plant.set_yticks(np.arange(len(v)),[r['element'] for r in rows]);plant.invert_yaxis()
    plant.set_title('(c) Plant: comparison with ICP-OES',loc='left',fontsize=10)
    plant.set_xlim(-28,27)
    for i,x in enumerate(v):
        if abs(x)>10:plant.text(x+(.6 if x>=0 else -.6),i,f'{x:+.2f}',va='center',ha='left' if x>=0 else 'right',fontsize=8)
    for ax in (soil,alloy,plant):
        ax.axvline(0,color='#303030',lw=.7)
        ax.set_xlabel('Signed relative difference (%)')
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='x',alpha=.18);ax.set_axisbelow(True)
        ax.tick_params(axis='y',length=0)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(out);fig.savefig(out.with_suffix('.png'),dpi=240)
    print(f'Wrote {out}')

if __name__=='__main__':main()
