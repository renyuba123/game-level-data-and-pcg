"""Audit complete budgets and produce research figures without changing selection or fitness."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pymoo.indicators.hv import HV
from common import WORK, ROOT, SOURCE_DXF, SOURCE_GRAPH, read_json, write_json, digest

def main():
    directory=WORK/'runs/search_v1'
    history=read_json(directory/'history.json')
    spec=read_json(directory/'spec.json')
    expected={(seed,method,g) for seed in spec['seeds'] for method in ('evolution','random') for g in range(1,21)}
    actual=[(h['seed'],h['method'],h['generation']) for h in history]
    assert len(actual)==len(set(actual))==120 and set(actual)==expected, 'Incomplete or duplicate experiment batches'
    assert all(h['evaluations']==32 and len(h['keys'])==32 for h in history)
    fig,axes=plt.subplots(1,3,figsize=(16,4.7),constrained_layout=True)
    rows=[]
    hv=HV(ref_point=np.array([1.,1.,1.,0.]))
    for method,color in [('evolution','#167d9a'),('random','#c47b35')]:
        for seed in spec['seeds']:
            batches=sorted((h for h in history if h['seed']==seed and h['method']==method),key=lambda h:h['generation'])
            records=[]; curve=[]; best=float('inf'); count=0; feasible=[]
            for batch in batches:
                for key in batch['keys']:
                    record=read_json(WORK/'cache'/key/'evaluation.json')
                    assert record['recipe']==spec['recipe'], 'Mixed analysis recipe'
                    records.append(record); count+=1
                    if record['valid'] and record['constraint']<=0:
                        feasible.append(record); best=min(best,record['objectives'][0])
                f=np.array([r['objectives'] for r in feasible])
                bounded=f[np.all(f<np.array([1,1,1,0]),axis=1)] if len(f) else np.empty((0,4))
                curve.append({'evaluations':count,'best_structure':None if not np.isfinite(best) else best,
                    'feasible_fraction':len(feasible)/count,'hypervolume':float(hv(bounded)) if len(bounded) else 0.})
            label=f'{method.title()} seed {seed}'
            x=[c['evaluations'] for c in curve]
            axes[0].plot(x,[c['best_structure'] for c in curve],label=label,color=color,alpha=.8,ls={11:'-',29:'--',47:':'}[seed])
            axes[1].plot(x,[c['hypervolume'] for c in curve],label=label,color=color,alpha=.8,ls={11:'-',29:'--',47:':'}[seed])
            axes[2].plot(x,[c['feasible_fraction'] for c in curve],label=label,color=color,alpha=.8,ls={11:'-',29:'--',47:':'}[seed])
            rows.append({'method':method,'seed':seed,'evaluations':len(records),'unique_candidates':len({r['key'] for r in records}),
                'geometry_analysis_valid':sum(r['valid'] for r in records),'fairness_feasible':len(feasible),
                'best_structure':min((r['objectives'][0] for r in feasible),default=None),
                'best_pressure_loss':min((r['objectives'][2] for r in feasible),default=None),
                'maximum_diversity':max((-r['objectives'][3] for r in feasible),default=None),
                'hypervolume':curve[-1]['hypervolume'],'curve':curve})
    titles=['Best feasible structural distance (lower better)','Feasible hypervolume (higher better)','Fairness-feasible fraction (higher better)']
    for ax,title in zip(axes,titles):
        ax.set(title=title,xlabel='Candidate evaluations'); ax.grid(alpha=.2)
    axes[2].legend(fontsize=7)
    fig.suptitle('Three seeds, 640 evaluations per method per seed; fixed-baseline fitness')
    fig.savefig(directory/'final_comparison.png',dpi=180); fig.savefig(directory/'final_comparison.svg'); plt.close(fig)
    source=read_json(ROOT/'data/source_profile.json')
    hashes={'graph_unchanged':digest(SOURCE_GRAPH)==source['source_graph_sha256'],
            'dxf_unchanged':digest(SOURCE_DXF)==source['source_dxf_sha256']}
    assert all(hashes.values())
    write_json(directory/'final_experiment.json',{'complete':True,'total_evaluations':3840,'groups':rows,'source_checks':hashes,
        'hypervolume_reference':[1,1,1,0],'hypervolume_note':'Post-hoc reporting statistic, not optimized. Only feasible points strictly inside the fixed reference box contribute.',
        'comparison_note':'Three paired seeds only; objective extrema can belong to different candidates. No claim of better human experience.'})
    lines=['# 鼠王关搜索式 PCG：完整实验结果','',
        '三组进化与三组等预算随机对照均已完成，每组 640 次评价，共 3840 次。所有评价使用同一配准、尺度、网格和实现版本；原 graph/DXF 哈希未变。','',
        '|方法|种子|满足公平性约束|最佳结构距离↓|最佳压力损失↓|最大路线多样性↑|',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"|{r['method']}|{r['seed']}|{r['fairness_feasible']}/640|{r['best_structure']:.6f}|{r['best_pressure_loss']:.6f}|{r['maximum_diversity']:.6f}|")
    lines+=['','各列极值可能来自不同候选，不能拼成一张同时达到全部最优的关卡。仅三组随机种子，不作总体显著性或全局最优结论。',
        '', '![完整收敛与对照](final_comparison.png)', '',
        '## 指标与验收边界','',
        '- 结构分数对照的是统一初始/全开条件下重算的鼠王关 DXF 模型。历史 graph 与重算值存在差异，详见 ../../baseline/calibration_200.json。',
        '- Gate Counts 与 Convex Choice 没有进入适应度：前者生成参数未核实，后者重算一致性未建立。',
        '- 体验分数来自三种二维追逐代理。独立扰动、200 单位精网格和 Godot 真实穿门分别复核，不能替代真人试玩。',
        '- 中期发现了短时间逃脱/接近捕获阈值的候选。新增独立公平性验收属于事后筛查，完整记录见 heldout_export_review.json；未通过者不作为推荐预设。',
        '- 图中的超体积是事后汇报统计，固定参考点为 [1,1,1,0]，只计入框内的可行点，不是搜索评分。',
        '', '## 下一步游戏设计验证','',
        '以同一角色参数让玩家交叉顺序试玩基准白模与通过最终验收的候选，记录死亡、卡住、逃生选择、压力和公平性感受。对过短逃脱路线、过早捕获阈值和绕圈策略先校准，再建立版本隔离的新评价规则；不要在当前实验中途改分后混排。']
    (directory/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Complete experiment report written',flush=True)

if __name__=='__main__': main()
