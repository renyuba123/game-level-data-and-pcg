from pathlib import Path
import json,re,hashlib
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1]; W=R/'evolution'; O=W/'paper'
doc=Document(); sec=doc.sections[0];sec.page_height=Cm(29.7);sec.page_width=Cm(21)
sec.top_margin=Cm(1.9);sec.bottom_margin=Cm(1.9);sec.left_margin=Cm(2.1);sec.right_margin=Cm(2.1)
sec.header_distance=Cm(.8);sec.footer_distance=Cm(.8)
for name,size in [('Normal',10.5),('Title',18),('Subtitle',12),('Heading 1',14),('Heading 2',11.5),('Caption',9)]:
    s=doc.styles[name];s.font.name='Times New Roman';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0);s.element.rPr.rFonts.set(qn('w:eastAsia'),'宋体' if name in ['Normal','Caption'] else '黑体')
    s.paragraph_format.space_after=Pt(6);s.paragraph_format.line_spacing=1.2
for st in doc.styles:
    for bd in list(st.element.iter(qn('w:pBdr'))): bd.getparent().remove(bd)
for name in ['Normal','Caption','Subtitle','Title']:
    doc.styles[name].font.bold=False;doc.styles[name].font.italic=False
for name in ['Title','Subtitle','Heading 1','Heading 2']:
    doc.styles[name].paragraph_format.first_line_indent=Cm(0)
doc.styles['Normal'].paragraph_format.first_line_indent=Cm(.74)
doc.styles['Heading 1'].paragraph_format.space_before=Pt(6)
doc.styles['Caption'].paragraph_format.first_line_indent=Cm(0)
header=sec.header.paragraphs[0];header.text='鼠王关 PCG 实验研究报告';header.style='Caption'
foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');foot._p.append(fld)
texts=[]
def p(t,style=None):
    t=t.replace('78 个混合变量','77 个混合变量')
    texts.append(t);x=doc.add_paragraph(t,style);return x
def h(t):p(t,'Heading 1')
def eq(t):
    x=doc.add_paragraph();x.alignment=WD_ALIGN_PARAGRAPH.CENTER;x.paragraph_format.first_line_indent=Cm(0)
    om=OxmlElement('m:oMath');rr=OxmlElement('m:r');tt=OxmlElement('m:t');tt.text=t;rr.append(tt);om.append(rr);x._p.append(om);texts.append(t)
def fig(n,w,caption):
    x=doc.add_paragraph();x.paragraph_format.first_line_indent=Cm(0);x.alignment=WD_ALIGN_PARAGRAPH.CENTER;x.paragraph_format.keep_with_next=True
    x.add_run().add_picture(str(O/'figures'/f'{n}.png'),width=Cm(w));p(caption,'Caption')
def table(headers,rows,widths):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
    for c,w in zip(t.columns,widths):c.width=Cm(w)
    for c,txt in zip(t.rows[0].cells,headers):c.text=txt
    for row in rows:
        for c,txt in zip(t.add_row().cells,row):c.text=str(txt)
    for i,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr();no=OxmlElement('w:cantSplit');trpr.append(no)
        if i==0:trpr.append(OxmlElement('w:tblHeader'))
        for c,w in zip(row.cells,widths):
            c.width=Cm(w);pr=c._tc.get_or_add_tcPr();bd=OxmlElement('w:tcBorders')
            for side in ['top','bottom','left','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');bd.append(e)
            pr.append(bd)
            if i==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E6EBEF');pr.append(sh)
            for pp in c.paragraphs:
                pp.paragraph_format.first_line_indent=Cm(0);pp.paragraph_format.space_after=Pt(3);pp.paragraph_format.space_before=Pt(3);pp.paragraph_format.line_spacing=1.05
                for run in pp.runs:run.font.size=Pt(9);run.bold=i==0
    return t
def page():doc.add_page_break()
p('基于空间句法反馈的 Boss 关卡多目标进化生成','Title')
p('以鼠王关重建模型为例','Subtitle')
p('精简研究报告  ·  实验版本 search_v1  ·  2026 年 11 月 19 日','Caption')
h('摘要')
p('本研究将鼠王关的重建几何与空间分析数据转化为关卡生成的评价依据，构建了“参数生成—空间分析—追逐评价—进化筛选”的闭环。系统以 Godot 生成三维白模，使用 Depthmap 计算空间指标，并通过混合变量遗传算法搜索不同布局。三组进化实验与等预算随机对照共完成 3840 次评价。进化搜索满足约束的比例为 24.7%，随机对照为 11.2%；三个种子的最佳结构匹配均由进化获得，但压力与路线多样性的最佳值仍由随机对照取得。两份不同候选通过精网格和技术验收。结果支持该方法辅助筛选与结构匹配的作用，尚不足以证明游戏体验优于官方关卡。')
p('关键词：搜索式程序化生成；空间句法；混合变量遗传算法；Boss 追逐；Godot','Caption')
h('1 研究问题与系统分工')
p('研究问题并非让算法复刻整张地图，而是在保持原关卡空间组织特征的同时，寻找可通行、可追逐且具有替代路线的布局。搜索式程序化内容生成将内容表示、生成和适应度评价结合起来[1]。本项目把这些环节连接为可重复执行的流水线，而不是只靠更换随机种子挑选外观。')
p('原始 DXF 提供墙体、连接和障碍语义，shuwang.graph 提供历史空间分析参照。Godot 解码候选参数并产生统一几何；Depthmap 负责真实空间计算；Python 负责评价、缓存和进化。优化基准是相同开口状态下重新计算的 DXF 模型，不能直接称为官方游戏的原始测量。')
fig('fig1_workflow',16.6,'图 1  系统闭环与最终复核。作者依据当前生成器和评价代码绘制；最终复核不参与当前轮次的进化反馈。')
page()
h('2 生成与评价方法')
p('布局固定为 11 个空间、6 个 through、3 个 break 和 2 个障碍，保留中心大厅、长廊、绕障碍房和削角端部房等类型。78 个混合变量控制房间长宽、斜边与削角、支房交换、开口宽度与偏移、连接类别优先级、可选普通通路、障碍偏移和双方出生房间。长宽缩放限定为模板的 0.88–1.12；房型与连接骨架并未开放为任意拓扑。')
p('through 初始为可见窄缝，玩家交互 0.65 秒后挤过，Boss 需 2 秒撞开；break 初始封闭，玩家不能破坏，Boss 需 3 秒撞开，之后双方可通行。block 参与碰撞、绕行和视线检查。角色速度和尺寸保持固定，避免算法通过弱化 Boss 获得好成绩。')
p('实现采用 pymoo 0.6.2 的 MixedVariableGA，配置 NSGA-II 的非支配排序与拥挤度生存选择[2–3]。混合变量交配按实数、整数、布尔和类别变量处理交叉与变异。每轮保留在不同目标上具有优势且分布较分散的候选，因此结果是一组权衡方案，而非单一总分冠军。')
p('空间距离 S 比较视觉整合度、VGA 连接度和平均度量最短路径距离。对初始及全开两种状态，取每项指标的 5%、25%、50%、75%、95% 分位点；同时比较大厅、障碍房、廊道、支房和端部房内的分布与高值比例。设 G 为全局分位差，R 为分区分位差及高值比例差的平均值，则：')
eq('S = mean [0.5G + 0.5R]')
p('分位差除以对应基准的固定尺度，即 max（基准 P95−P05，0.01×|基准 P50|，10⁻⁹）；高值比例指各图自身前 10% 数值在分区内的占比。缺失分区按代码罚值处理。该设计同时约束总体分布和高值空间角色，但不能保证高值点的具体坐标一致。')
eq('min f(x) = [S(x), F(x), P(x), −D(x)]')
eq('F = e + s + max(0, 0.5−a) + 0.5t')
eq('P = |n−0.4| + max(0, 0.1−n)；D = 0.5c + 0.5j')
p('其中 a 为逃脱比例，e 为 3 秒内被捕比例，s 为卡住比例，t 为超时比例；n 为距离小于 5 模型米且互相可见的时间占比，c 为房间覆盖率，j 为路线有向边集合的平均 Jaccard 差异。0.4 是人为设定的压力目标，尚非玩家实测阈值。训练约束另要求 e+s+max(0,1/6−a)≤0；几何或分析无效者先淘汰。')
p('行为评价采用直奔出口、远离 Boss、寻找遮挡三种二维策略，每种两次扰动，共六次模拟。它测量的是代理表现；Godot 实际穿门测试用于另外验证碰撞与状态切换，两者不等价。')
page()
h('3 实验设计与对照结果')
p('进化与随机方法共享参数范围、评价实现和固定基准。每组使用种子 11、29、47，种群 32，计 20 个评价批次，各 640 次，合计 3840 次。首批计入总代数；缓存命中与提前淘汰均占评价预算，因此不意味着 3840 张独立地图或 3840 次完整 Depthmap 运算。原文件及评价实现以哈希锁定，支持断点恢复。')
p('表 1  实验设置与指标定义','Caption')
table(['项目','设置与含义'],[
('软件','Godot 4.7.2；DepthmapX CLI 0.9.1；pymoo 0.6.2'),('网格与尺度','搜索 400，复核 200 图纸单位；图纸坐标÷1000 进入 Godot，物理尺度待核实'),('真实空间指标','Visual Integration [HH]；Connectivity；Metric Mean Shortest-Path Distance'),('行为目标','公平性损失 F、压力损失 P 越低越好；路线多样性 D 越高越好'),('未纳入优化','Gate Counts 参数未核实；Convex Choice 重算一致性未建立')],[3,13.7])
fig('fig2_search',16.6,'图 2  等预算对照。曲线来自完整历史记录；实线、虚线、点线分别为种子 11、29、47。结构距离取累计可行候选的最佳值，比例按评价次数累计，含重复评价。')
p('表 2A  完整搜索结果（400 网格；各列极值可来自不同候选）','Caption')
data=json.loads((W/'runs/search_v1/final_experiment.json').read_text(encoding='utf-8'))
table(['方法／种子','满足约束','最小 S','最小 P','最大 D'],[[('进化' if g['method']=='evolution' else '随机')+'/'+str(g['seed']),f"{g['fairness_feasible']}/640",f"{g['best_structure']:.4f}",f"{g['best_pressure_loss']:.4f}",f"{g['maximum_diversity']:.4f}"] for g in data['groups']],[3.2,3.2,3.4,3.4,3.5])
page()
h('4 最终候选与技术验收')
p('进化搜索共得到 475/1920 次满足约束的评价，随机对照为 215/1920 次。三个种子的结构最优值均由进化获得，而随机方法取得更低的压力损失和更高的多样性极值。固定参考点 [1,1,1,0] 内计算的最终超体积也均由随机对照领先。超体积是事后统计，以上结果不能拼接为一张全目标最优地图。')
fig('fig3_layouts',14.5,'图 3  最终两份候选的几何分区与连接。来源为精网格复核对应的解码布局。比例尺为模型尺度，未经真实物理尺度确认；灰色分区边界不一定是实体墙，出生标注表示所在房间。')
p('表 2B  最终候选复核（200 网格；独立逃脱为六次代理模拟）','Caption')
table(['候选','S','P','D','独立逃脱'],[['均衡','0.114805','0.294574','0.409524','4/6'],['探索','0.167928','0.428571','0.421818','6/6']],[3.2,3.3,3.3,3.3,3.6])
p('两份候选共 18 个特殊通道通过初始阻挡、Boss 撞开及实际穿越测试。全部撞开后，双方导航均覆盖 11 个空间。另检查了按门 ID 逐个开放的代表性过程，但该顺序不是 Boss 行为录像。压力预设与均衡预设是同一候选，只计两份独立布局。')
page()
h('5 空间指标与设计解释')
fig('fig4_metrics',16.6,'图 4  200 单位网格下的指标分位数。初始和全部撞开均使用对应重建基准；横轴为分位点，纵轴保留原指标与单位，未分别归一化。HH 为指数，Connectivity 为可见点数，Metric 为图纸单位。')
p('图 4 显示，两份候选并非在所有指标上以相同方式接近原图。均衡候选全开后的视觉整合度与连接度总体更贴近基准；探索候选全开后的高分位整合度和连接度更高。这表示其可见联系分布发生变化，但不能仅据高值增加就断言更好玩或更有压力。初始与全开的差异也说明，破坏连接应作为状态变量评价，而非只分析一张静态地图。')
p('结构距离还包含按空间角色计算的误差，因此图中的全局曲线不能完全替代 S。保留这些分解指标有助于设计者定位偏差：问题究竟来自大范围视线暴露、长距离绕行，还是高值过度集中于某一类空间。修改相应房间尺寸、门洞与障碍后，可在同一基准下再次测量。')
p('本轮算法的实际作用是扩大可检查候选的数量，并把结构匹配与追逐权衡显式呈现。候选保留参数、几何、指标 CSV、评价日志与种子，可以返回 Godot 继续编辑。它适合作为设计筛选工具，而不是取代设计者判断的自动关卡裁判。')
page()
h('6 局限与结论')
p('本研究有四方面限制。第一，生成器仍受固定房型库与连接骨架约束，搜索得到的是这一设计空间内的改进，不能推出任意 Boss 场景的普遍规律。第二，仅有三个独立种子，且评价次数包含重复候选，未进行总体显著性检验。可行产出优势反映当前预算利用率，不能等同于独立优秀地图数量的增长。')
p('第三，压力与公平性采用人工阈值和简化代理。部分中期候选利用了过短逃脱路径或捕获时间边界，最终增加的独立扰动筛查属于事后验收，不是预注册实验。最终候选经过该筛查，不能据此把六次代理模拟的逃脱率推广到真实玩家。后续应隔离评价版本，并以新策略、新起点及真人交叉顺序试玩检验泛化。')
p('第四，原 graph 的开口状态与 DXF 重算结果存在差异。精网格重建得到 3468 个对应点位，并不意味着指标完全复现。尺度、网格和开口状态均影响结果，尤其距离指标不能跨单位直接比较。Gate Counts 与 Convex Choice 因生成条件或一致性尚未核实，保留为参考而不进入适应度，也未用房间拓扑连接度冒充空间句法指标。')
p('综上，本轮完成了可复现的参数化生成、真实空间分析、多目标搜索与技术验收闭环。进化在结构匹配和满足约束的产出上取得优势，同时暴露了随机探索在部分体验代理目标上的竞争力。下一阶段应先校准代理与阈值，再比较基准白模和候选的死亡、卡住、路线选择、主观压力及公平性感受，才能讨论游戏体验是否得到改进。')
h('参考文献')
refs=[
'[1] Togelius J, Yannakakis G N, Stanley K O, Browne C. Search-Based Procedural Content Generation: A Taxonomy and Survey[J]. IEEE Transactions on Computational Intelligence and AI in Games, 2011. DOI: 10.1109/TCIAIG.2011.2148116.',
'[2] Deb K, Pratap A, Agarwal S, Meyarivan T. A fast and elitist multiobjective genetic algorithm: NSGA-II[J]. IEEE Transactions on Evolutionary Computation, 2002, 6(2): 182–197. DOI: 10.1109/4235.996017.',
'[3] Blank J, Deb K. pymoo: Multi-Objective Optimization in Python[J]. IEEE Access, 2020, 8: 89497–89509. DOI: 10.1109/ACCESS.2020.2990567.',
'[4] Turner A, Doxa M, O’Sullivan D, Penn A. From Isovists to Visibility Graphs: A Methodology for the Analysis of Architectural Space[J]. Environment and Planning B, 2001. DOI: 10.1068/b2684.',
'[5] depthmapX. Command-line interface documentation[EB/OL]. https://github.com/varoudis/depthmapX/blob/master/docs/commandline.md. 访问日期：2026-11-19.'
]
for r in refs:
    x=p(r,'Caption');x.paragraph_format.space_after=Pt(5)
p('复现与数据说明：本报告图表读取 search_v1 的最终记录及精网格缓存，没有重新运行优化。详细路径、哈希与图表来源见同目录 source_manifest.json。报告未使用玩家路线 CSV 训练行为模型，亦未进行真人试玩。','Caption')
# Cite spatial methodology where introduced, without confusing software citation with measurements.
for x in doc.paragraphs:
    if x.text.startswith('空间距离 S 比较'):x.runs[0].text=x.runs[0].text.replace('空间距离 S 比较','可见性图方法用于表征空间联系[4–5]。空间距离 S 比较')
doc.core_properties.title='基于空间句法反馈的 Boss 关卡多目标进化生成——以鼠王关重建模型为例'
doc.core_properties.author='';doc.core_properties.subject='search_v1 已完成实验的精简研究报告'
doc.save(O/'鼠王关遗传算法研究报告.docx')
(O/'正文.txt').write_text('\n\n'.join(texts),encoding='utf-8')
paths=[W/'search.py',W/'genome.py',W/'metrics.py',W/'simulation.py',W/'evaluator.py',W/'runs/search_v1/final_experiment.json',W/'runs/search_v1/delivery_acceptance.json',W/'acceptance.json',W/'candidate_navigation.json']
manifest={'created':'2026-11-19','run':'search_v1','new_optimization_run':False,'source_files':[{'path':str(x),'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in paths],'figures':['fig1_workflow','fig2_search','fig3_layouts','fig4_metrics'],'chinese_character_count':len(re.findall(r'[\u4e00-\u9fff]',''.join(texts))),'references':refs}
(O/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Chinese character count',manifest['chinese_character_count'])
