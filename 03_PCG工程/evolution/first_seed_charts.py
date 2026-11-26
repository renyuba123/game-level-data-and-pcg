import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import WORK,read_json,write_json

history=read_json(WORK/'runs/search_v1/history.json')
fig,axes=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
summary={}
for method,color in [('evolution','#167d9a'),('random','#c47b35')]:
    batches=sorted((h for h in history if h['seed']==11 and h['method']==method),key=lambda h:h['generation'])
    assert len(batches)==20
    records=[read_json(WORK/'cache'/k/'evaluation.json') for h in batches for k in h['keys']]
    best=float('inf'); x=[]; y=[]; feasible=[]
    for i,r in enumerate(records,1):
        if r['valid'] and r['constraint']<=0:
            feasible.append(r); best=min(best,r['objectives'][0])
        if np.isfinite(best): x.append(i); y.append(best)
    axes[0].plot(x,y,label=method.title(),color=color,lw=2)
    axes[1].scatter([r['objectives'][0] for r in feasible],[r['objectives'][2] for r in feasible],
        s=17,alpha=.5,color=color,label=f'{method.title()} ({len(feasible)}/640 feasible)')
    summary[method]={'evaluations':len(records),'feasible':len(feasible),'best_structure':best}
selected=read_json(WORK/'runs/search_v1/seed11_review/selection.json')
axes[1].scatter(selected['coarse_objectives'][0],selected['coarse_objectives'][2],s=160,marker='*',color='#202a32',label='Candidate under review',zorder=5)
axes[0].set(title='Structural convergence: feasible candidates only',xlabel='Candidate evaluations',ylabel='Best structural distance (lower is better)')
axes[1].set(title='Trade-off between structure and pressure',xlabel='Structural distance (lower is better)',ylabel='Pressure-target loss (lower is better)')
for ax in axes: ax.grid(alpha=.18); ax.legend(fontsize=8)
fig.suptitle('Completed seed 11: equal evaluation budget; interim results',fontsize=12)
out=WORK/'runs/search_v1'
fig.savefig(out/'first_seed_comparison.png',dpi=180)
fig.savefig(out/'first_seed_comparison.svg')
plt.close(fig)
write_json(out/'first_seed_chart_sources.json',{'scope':'seed 11 only; all 20 generations per method; distinct objective extrema do not imply dominance','summary':summary,'selected':selected})
print(summary)
