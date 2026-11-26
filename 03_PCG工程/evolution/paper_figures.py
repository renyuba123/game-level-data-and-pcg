import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle,FancyBboxPatch
R=Path(__file__).resolve().parents[1]; W=R/'evolution'; O=W/'paper'; F=O/'figures'; F.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':10,'axes.unicode_minus':False,'svg.fonttype':'path'})
def save(fig,n):
    for ext in ('png','svg'):fig.savefig(F/f'{n}.{ext}',dpi=240,bbox_inches='tight',facecolor='white')
    plt.close(fig)
fig,ax=plt.subplots(figsize=(10,3.3));ax.set(xlim=(0,10),ylim=(-.15,3.4));ax.axis('off')
def box(x,y,t,w=2.1):
    ax.add_patch(FancyBboxPatch((x,y),w,.65,boxstyle='round,pad=0.05',fc='#edf2f5',ec='#526875'));ax.text(x+w/2,y+.325,t,ha='center',va='center',fontsize=10)
def arr(a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#526875','lw':1.4})
for x,t in [(0.1,'混合参数编码\n房型／通道／障碍／出生'),(2.65,'Godot 解码几何\n墙体与角色通路检查'),(5.2,'真实 Depthmap 指标\n＋二维追逐代理评价'),(7.75,'非支配排序＋拥挤度\n保留不同权衡的候选')]:box(x,2.3,t)
for x in [2.25,4.8,7.35]:arr((x,2.625),(x+.35,2.625))
box(2.65,.9,'混合变量交叉与变异');arr((8.8,2.25),(8.8,1.225));arr((8.8,1.225),(4.85,1.225));arr((2.6,1.225),(1.15,1.225));arr((1.15,1.225),(1.15,2.25));ax.text(6.7,1.4,'下一代',ha='center')
box(5.2,-.0,'最终筛选与独立复核\n200 网格／追逐／实际穿门',w=4.65);arr((8.8,1.18),(8.8,.7));ax.text(1.2,.25,'不合格候选淘汰\n不改变角色能力刷分',ha='center',fontsize=9,color='#555555')
save(fig,'fig1_workflow')
data=read(W/'runs/search_v1/final_experiment.json')
fig,axs=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
for g in data['groups']:
    c='#167f9b' if g['method']=='evolution' else '#c96b32'; lab=('进化' if g['method']=='evolution' else '随机')+f" {g['seed']}"; ls={11:'-',29:'--',47:':'}[g['seed']]
    for ax,field in zip(axs,['best_structure','feasible_fraction']):ax.plot([r['evaluations'] for r in g['curve']],[r[field] for r in g['curve']],color=c,ls=ls,label=lab,lw=1.8)
for ax in axs:ax.set_xlabel('累计评价次数');ax.grid(alpha=.2)
axs[0].set_ylabel('累计最佳可行结构距离 ↓');axs[1].set_ylabel('累计满足约束的比例 ↑');axs[1].legend(fontsize=8,ncol=2)
save(fig,'fig2_search')
cs={k:read(R/f'data/evolution/{k}.json') for k in ['balanced','exploration']}
recs={k:read(W/'cache'/c['evaluation']['fine_review']['key']/'evaluation.json') for k,c in cs.items()}
layouts={k:read(W/'cache'/c['evaluation']['fine_review']['key']/'layout.json') for k,c in cs.items()}
fig,axs=plt.subplots(1,2,figsize=(9,7.5),layout='constrained')
for ax,(k,l) in zip(axs,layouts.items()):
    for r in l['rooms']:
        ax.add_patch(Polygon(r['polygon'],facecolor='#e4ebef',edgecolor='#536775',lw=.9));ax.text(*r['center'],r['source_id'],ha='center',va='center',fontsize=8)
    for e in l['edges']:
        a,b=np.array(e['shared_segment']);t=(b-a)/np.linalg.norm(b-a);c=np.array(e['door_anchor']);p=np.array([c-t*e['door_width_m']/2,c+t*e['door_width_m']/2]);ax.plot(p[:,0],p[:,1],lw=3.5,color={'normal':'#57a16b','through':'#168db2','break':'#d47b3d'}[e['kind']])
    for b in l['blocks']:ax.add_patch(Circle(b['position'],b['radius'],fc='#79664c'))
    for field,txt,color in [('spawn_room','玩家出生','#007635'),('boss_room','Boss','#b12725')]:
        off=(34,-12) if k=='exploration' and field=='spawn_room' else ((0,-12) if k=='balanced' and field=='boss_room' else (0,11))
        ax.annotate(txt,l['rooms'][l[field]]['center'],xytext=off,textcoords='offset points',ha='center',color=color,fontsize=9,arrowprops={'arrowstyle':'-','color':color,'lw':.6} if off[0] else None)
    p=l['rooms'][-1]['center'];ax.annotate('出口房间',p,xytext=(0,12),textcoords='offset points',ha='center',fontsize=8)
    ax.autoscale_view();ax.set_aspect('equal');ax.invert_yaxis();ax.axis('off');ax.set_title('均衡候选' if k=='balanced' else '探索候选')
    xmin,xmax=ax.get_xlim();ymax,ymin=ax.get_ylim();x=xmin+.3;y=ymax-.5
    ax.plot([x,x+2],[y,y],c='black',lw=2);ax.text(x+1,y-.2,'2 模型米',ha='center',fontsize=8)
fig.supxlabel('绿色：普通通路   蓝色：through   橙色：break   棕色：障碍',fontsize=10)
save(fig,'fig3_layouts')
names=['Visual Integration [HH]','Connectivity','Metric Mean Shortest-Path Distance']; titles=['视觉整合度（HH）','VGA 连接度','平均度量最短路径距离']; units=['HH 指数','可见点数量','图纸单位']
fig,axs=plt.subplots(2,3,figsize=(10,7),layout='constrained')
for i,state in enumerate(['initial','all_open']):
    ps={'重建基准':read(W/f'baseline/grid_200/{state}/profile.json')}
    ps.update({('均衡' if k=='balanced' else '探索'):read(Path(r['states'][state]['directory'])/'profile.json') for k,r in recs.items()})
    for j,n in enumerate(names):
        ax=axs[i,j]
        for (lab,p),col in zip(ps.items(),['#333333','#167f9b','#c96b32']):ax.plot([5,25,50,75,95],p['metrics'][n]['quantiles'],color=col,marker='o',ms=3,label=lab)
        ax.set(title=('初始' if i==0 else '全部撞开')+'｜'+titles[j],xlabel='分位点（%）',ylabel=units[j]);ax.grid(alpha=.2)
        if i==0 and j==0:ax.legend(fontsize=8)
save(fig,'fig4_metrics')
print('4 figures written')
