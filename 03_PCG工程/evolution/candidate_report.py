from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
import numpy as np

out=WORK/'runs/search_v1'
labels=['balanced','exploration']
candidates={label:read_json(ROOT/f'data/evolution/{label}.json') for label in labels}
records={label:read_json(WORK/'cache'/c['evaluation']['fine_review']['key']/'evaluation.json') for label,c in candidates.items()}
layouts={label:read_json(WORK/'cache'/c['evaluation']['fine_review']['key']/'layout.json') for label,c in candidates.items()}
colors={'baseline':'#252525','balanced':'#167f9b','exploration':'#c96b32'}
fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
for row,state in enumerate(['initial','all_open']):
    profiles={'baseline':read_json(WORK/f'baseline/grid_200/{state}/profile.json')}
    profiles.update({label:read_json(Path(rec['states'][state]['directory'])/'profile.json') for label,rec in records.items()})
    for col,metric in enumerate(METRICS):
        ax=axes[row,col]
        for label,p in profiles.items():
            ax.plot([5,25,50,75,95],p['metrics'][metric]['quantiles'],marker='o',label=label,color=colors[label])
        ax.set_title(state.replace('_',' ')+' | '+['Visual Integration [HH]','VGA Connectivity','Metric Mean Shortest-Path Distance'][col],fontsize=10)
        ax.set_xlabel('Percentile');ax.set_ylabel(['HH index','Visible point count','Drawing units'][col]);ax.grid(alpha=.2)
        if row==0 and col==0:ax.legend()
fig.suptitle('Final candidates vs reconstructed DXF baseline | grid 200 | same units and opening states')
for ext in ['png','svg']:fig.savefig(out/f'candidate_metrics.{ext}',dpi=180)
plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11,10),layout='constrained')
for ax,(label,layout) in zip(axes,layouts.items()):
    for room in layout['rooms']:
        ax.add_patch(Polygon(room['polygon'],facecolor='#e3e9ee',edgecolor='#52616b',linewidth=1))
        ax.text(*room['center'],room['source_id'],ha='center',va='center',fontsize=8)
    for edge in layout['edges']:
        a,b=np.array(edge['shared_segment']);t=(b-a)/np.linalg.norm(b-a);c=np.array(edge['door_anchor']);h=edge['door_width_m']/2
        points=np.array([c-t*h,c+t*h]);ax.plot(points[:,0],points[:,1],linewidth=4,color={'normal':'#54a46b','through':'#279ac0','break':'#de844b'}[edge['kind']])
    for block in layout['blocks']:ax.add_patch(Circle(block['position'],block['radius'],facecolor='#73634e'))
    for field,text,color in [('spawn_room','Spawn','#00883d'),('boss_room','Boss','#a32424')]:
        p=layout['rooms'][layout[field]]['center'];ax.annotate(text,p,xytext=(0,11),textcoords='offset points',ha='center',color=color,fontsize=9)
    ax.autoscale_view();ax.set_aspect('equal');ax.invert_yaxis();ax.set_title(label+' | '+candidates[label]['evaluation']['key'][:10]);ax.set_xlabel('Model metres (provisional DXF scale)');ax.set_ylabel('Model metres');ax.grid(alpha=.15)
fig.suptitle('Decoded geometry | green: normal, blue: through, orange: break\nRoom boundaries are analysis partitions; shared edges are not necessarily solid walls',fontsize=11)
for ext in ['png','svg']:fig.savefig(out/f'candidate_layouts.{ext}',dpi=180)
plt.close(fig)
gates=read_json(WORK/'acceptance.json');nav=read_json(WORK/'candidate_navigation.json')
assert not gates['failures'] and nav['passed']
states=read_json(out/'destruction_states.json')
from evaluator import Evaluator
Evaluator(200).assert_unchanged()
lines=['\n## 最终候选与验收（2026-11-19）','',
'最终交付 2 个不同布局。balanced 和 pressure 指向同一个候选；exploration 是另一个候选，不虚报为三个不同方案。',
'','|预设|候选 ID 前缀|精网格结构距离↓|压力损失↓|路线多样性↑|独立测试逃脱|',
'|---|---|---:|---:|---:|---:|']
for label,c in candidates.items():
    e=c['evaluation'];f=e['fine_review']['objectives'];h=e['heldout']
    lines.append(f"|{label}|{e['key'][:12]}|{f[0]:.6f}|{f[2]:.6f}|{-f[3]:.6f}|{h['escape_fraction']:.1%}|")
lines += ['',f"- 两个布局共 {len(gates['results'])} 个 through/break 通道均通过初始阻挡、Boss 撞开和实际穿越测试。",
'- Godot 全部撞开状态：玩家与 Boss 均可到达全部 11 个空间。初始玩家导航结果不包含显式挤身交互，不能误读为玩家不可达。',
f"- 破坏过程检查：{len(states['results'])} 个布局，每个检查初始状态及依门 ID 逐一开放的状态；这是构造的测试顺序，不是观测到的 Boss 行为。",
'- 200 单位精网格与独立追逐验收通过；5 项回归测试通过；原 DXF/graph 与评价实现哈希复核通过。',
'- Main 已重新从磁盘打开，最终预设可见，场景保存后脚本哈希不变，手动 seed 94 保留。',
'','![最终候选指标分布](candidate_metrics.png)','![候选几何分区](candidate_layouts.png)',
'','## 使用交付',
'打开 Godot 的 scenes/Main.tscn，在根节点选择 Evolution Preset：Balanced、Exploration 或 Pressure；F6 运行当前场景。Pressure 目前复用 Balanced。',
'候选参数保存在 data/evolution/*.json；完整评价在 evolution/cache；独立验收记录见 evolution/acceptance.json、candidate_navigation.json 与本目录 destruction_states.json。',
'','进化搜索的三组最佳结构距离均优于等预算随机对照，可行产出为 475/1920（24.7%），随机为 215/1920（11.2%）。但随机对照在压力、多样性极值及当前参考框下的最终超体积上更好，因此不能声称进化全面优于随机，更不能声称游戏体验已超过官方关卡。',
'','当前完成的是首轮搜索与白模技术验收。真人交叉试玩、完整战斗阶段，以及经验证后的 Gate Counts/Convex 适应度属于后续研究；历史指标仍保留，不用代理值冒充。','']
path=out/'FINAL_REPORT.md';old=path.read_text(encoding='utf-8').split('\n## 最终候选与验收')[0];path.write_text(old+'\n'.join(lines),encoding='utf-8')
write_json(out/'delivery_acceptance.json',{'status':'complete','unique_candidates':2,'gates_tested':len(gates['results']),'navigation_passed':nav['passed'],'source_hashes_rechecked':True,'candidate_keys':{k:v['evaluation']['key'] for k,v in candidates.items()}})
qa=WORK/'QA.md';qa.write_text(qa.read_text(encoding='utf-8')+'\n\n## Final delivery 2026-11-19\n120 batches / 3840 evaluations completed. Final fine-grid, heldout, 18 gate crossings, all-room Godot navigation and 5 regression checks passed. Two unique presets; pressure aliases balanced. See runs/search_v1/FINAL_REPORT.md for mixed results versus random control and metric exclusions. Main reopened from disk; script hash stable after saving.\n',encoding='utf-8')
print('Candidate figures and final delivery report written')
