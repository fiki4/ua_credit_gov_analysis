from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / 'reports/figures'
OUT.mkdir(exist_ok=True)
SOURCE = Path(__file__).resolve().parents[1] / 'data/processed/sector_metrics.csv'
d = pd.read_csv(SOURCE)
d = d.loc[d.sector_code.isin(['C','G'])].sort_values(['sector_code','year']).copy()
assert len(d)==6 and not d.duplicated(['sector_code','year']).any()
for col in ['revenue_uah_mn','loans_uah_mn']:
    base=d.groupby('sector_code')[col].transform('first')
    assert base.gt(0).all()
    d[col+'_index']=d[col]/base*100
d['profit_to_revenue_pct']=d.profit_before_tax_uah_mn/d.revenue_uah_mn*100
assert np.isfinite(d['profit_to_revenue_pct']).all()
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
names={'C':'Переробна промисловість','G':'Торгівля'}
fig,axes=plt.subplots(1,2,figsize=(13,6),sharey=True)
fig.suptitle('У промисловості гривневі кредитні залишки зростають\nзначно швидше за номінальний дохід',fontsize=17,x=.07,ha='left')
for ax,code in zip(axes,['C','G']):
    s=d[d.sector_code.eq(code)]
    for col,color,label,offset in [('revenue_uah_mn_index','#2563EB','Номінальний дохід',-17),('loans_uah_mn_index','#D97706','Гривневі кредитні залишки',10)]:
        ax.plot(s.year,s[col],color=color,marker='o',linewidth=2.5,label=label)
        for year,value in zip(s.year,s[col]):
            if year>2023: ax.annotate(f'{value:.1f}',(year,value),xytext=(0,offset),textcoords='offset points',ha='center',color=color)
    ax.set_title(names[code],loc='left',pad=14)
    ax.set_xticks([2023,2024,2025]); ax.set_xlim(2022.85,2025.15); ax.set_ylim(80,250)
    ax.axhline(100,color='#999999',linestyle=':',linewidth=1)
    ax.grid(axis='y',alpha=.2)
axes[0].set_ylabel('Індекс, 2023 рік = 100')
fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.14),ncol=2,frameon=False)
fig.text(.07,.035,'Джерела: Держстат і НБУ; власні розрахунки. Дохід — січень–вересень; кредити — на 1 жовтня.\nОхоплення джерел не повністю тотожне. Індекси не є показниками боргового навантаження.',fontsize=10,color='#555555')
fig.subplots_adjust(left=.08,right=.97,top=.74,bottom=.28,wspace=.17)
for ext in ['png','svg']: fig.savefig(OUT/f'growth_indices.{ext}',dpi=180)
plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(13,6))
fig.suptitle('Покращення 2025 року не повернуло показники\nдо рівня 2023 року',fontsize=17,x=.07,ha='left')
for ax,code in zip(axes,['C','G']):
    s=d[d.sector_code.eq(code)]
    bars=ax.bar(s.year.astype(str),s.profit_to_revenue_pct,color=['#94A3B8','#CBD5E1','#2563EB'],width=.55)
    ax.bar_label(bars,labels=[f'{v:.2f}%' for v in s.profit_to_revenue_pct],padding=6)
    ax.axhline(s.profit_to_revenue_pct.iloc[0],color='#64748B',linestyle='--',linewidth=1)
    ax.set_ylim(0,8); ax.set_axisbelow(True); ax.grid(axis='y',alpha=.2)
    ax.set_title(names[code],loc='left',pad=14)
    losses=s.loss_making_share_pct.to_list()
    ax.text(0,-.19,f'Частка збиткових: {losses[0]:.2f}% → {losses[2]:.2f}%\n2023 → 2025',transform=ax.transAxes,fontsize=11,color='#555555')
axes[0].set_ylabel('Фінрезультат до оподаткування / дохід, %')
fig.text(.07,.025,'Джерело: Держстат; січень–вересень, без малих підприємств. Пунктир — рівень 2023 року.\nЦе аналітичне відношення, не офіційний показник рентабельності; бізнес-моделі секторів відрізняються.',fontsize=10,color='#555555')
fig.subplots_adjust(left=.08,right=.97,top=.74,bottom=.29,wspace=.23)
for ext in ['png','svg']: fig.savefig(OUT/f'financial_recovery.{ext}',dpi=180)
plt.close(fig)
d.to_csv(Path(__file__).resolve().parents[1]/'data/processed/chart_data.csv',index=False,encoding='utf-8-sig')
print('Saved two charts as PNG/SVG and chart_data.csv')
