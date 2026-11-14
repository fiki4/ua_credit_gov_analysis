from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import textwrap
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed'
FIG=ROOT/'reports/figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
monthly=pd.read_csv(DATA/'monthly_42_by_size.csv',parse_dates=['date'])
p=monthly.pivot(index='date',columns='size',values='total_mn').rename(columns={'large':'Великі підприємства','medium':'Середні підприємства'})
ax=p.plot(figsize=(12,5.5),marker='o',color=['#2563EB','#D97706'])
ax.set_title('Будівництво споруд: кредитні залишки за розміром підприємств',loc='left')
ax.set_ylabel('млн грн, усі валюти'); ax.set_xlabel('Звітна дата'); ax.set_ylim(bottom=0); ax.grid(axis='y',alpha=.2)
fig=ax.get_figure()
fig.text(.02,.02,'НБУ; КВЕД 42; усі валюти у гривневому еквіваленті. Склад груп може змінюватися.\nЗміна залишків не є окремим показником нових видач або погашення.',fontsize=9)
fig.tight_layout(rect=[0,.1,1,1]); fig.savefig(FIG/'monthly_construction.png',dpi=170); plt.close(fig)
contrib=pd.read_csv(DATA/'division_contributions.csv')
contrib=contrib[contrib.period.eq('2024-2025')]
names={'C':'Переробна промисловість','G':'Торгівля','F':'Будівництво','H':'Транспорт'}
for codes,filename in [(['C','G'],'division_industry_trade'),(['F','H'],'division_construction_transport')]:
    fig,axes=plt.subplots(1,2,figsize=(17,9 if codes[0]=='C' else 7))
    for ax,sector in zip(axes,codes):
        q=contrib[contrib.sector_code.eq(sector)].copy()
        q['label']=q.division.astype(int).astype(str)+' — '+q.division_name.str.strip()
        q.loc[q.division.eq(-1),'label']='Непорівнянне охоплення: розділ 12'
        if sector=='C':
            matched=q[q.division.ne(-1)]
            keep=matched.total_mn_change.abs().nlargest(6).index
            other=matched.loc[~matched.index.isin(keep),'total_mn_change'].sum()
            q=pd.concat([q.loc[keep],q[q.division.eq(-1)],pd.DataFrame([{'division':0,'label':'Решта порівнюваних розділів','total_mn_change':other}])],ignore_index=True)
        q=q.sort_values('total_mn_change',ascending=False)
        v=q.total_mn_change/1000
        colors=['#94A3B8' if code==-1 else '#2563EB' if value>=0 else '#D97706' for code,value in zip(q.division,v)]
        bars=ax.barh(range(len(q)),v,color=colors)
        ax.bar_label(bars,fmt='%+.2f',padding=4)
        ax.set_yticks(range(len(q)),[textwrap.fill(s,36) for s in q.label]); ax.invert_yaxis()
        ax.set_title(names[sector],loc='left'); ax.axvline(0,color='#777777',lw=.8)
        ax.set_xlabel('Зміна загальних залишків, млрд грн'); ax.margins(x=.3); ax.grid(axis='x',alpha=.2); ax.set_axisbelow(True)
    fig.suptitle('Внески підгалузей у зміну кредитних залишків: 2025 проти 2024',fontsize=16)
    fig.text(.03,.025,'НБУ; великі та середні суб’єкти; на 1 жовтня; усі валюти у гривневому еквіваленті. Шкали різні.\nСірий — різниця непорівнянного охоплення, а не підтверджене погашення. Залишки не дорівнюють новим видачам.',fontsize=9)
    fig.tight_layout(rect=[0,.12,1,.94],w_pad=4)
    fig.savefig(FIG/(filename+'.png'),dpi=170); plt.close(fig)
