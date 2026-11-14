from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_nbu import SIZES, section

BASE=Path(__file__).resolve().parents[1]/'data/raw'
OUT=Path(__file__).resolve().parents[1]/'data/processed'
FIG=Path(__file__).resolve().parents[1]/'reports/figures'
FIG.mkdir(parents=True,exist_ok=True)
OUT.mkdir(exist_ok=True)
names={'C':'Переробна промисловість','F':'Будівництво','G':'Торгівля','H':'Транспорт'}
frames=[]
for year in [2023,2024,2025]:
    path=BASE/f'Loans_MSE_KVED_{year}-10-01.xlsx'
    raw=pd.read_excel(path,sheet_name=f'вересень {year}',header=None)
    assert f'1 жовтня {year}' in str(raw.iloc[0,0])
    assert 'тис' in str(raw.iloc[1,0])
    assert 'Залишки коштів за кредитами' in str(raw.iloc[2,3])
    d=raw.iloc[5:,:6].copy()
    d.columns=['size','division','division_name','total_mn','uah_mn','fx_mn']
    d['division']=pd.to_numeric(d.division,errors='raise').astype(int)
    d['sector_code']=d.division.map(section)
    d=d.loc[d['size'].isin(SIZES)&d.sector_code.notna()].copy()
    assert not d.duplicated(['size','division']).any()
    cols=['total_mn','uah_mn','fx_mn']
    d[cols]=d[cols].apply(pd.to_numeric,errors='raise')/1000
    assert d[cols].notna().all().all()
    assert np.allclose(d.total_mn,d.uah_mn+d.fx_mn,atol=.00001,rtol=0)
    d['year']=year
    frames.append(d)
detail=pd.concat(frames,ignore_index=True)
div=detail.groupby(['sector_code','division','year'])[cols].sum().reset_index()
labels=detail.drop_duplicates('division').set_index('division').division_name
div['division_name']=div.division.map(labels)
sectors=div.groupby(['sector_code','year'])[cols].sum().reset_index()
sectors['fx_share_pct']=sectors.fx_mn/sectors.total_mn*100
changes=[]; contributions=[]
for start,end in [(2023,2024),(2024,2025),(2023,2025)]:
    a=sectors[sectors.year.eq(start)].set_index('sector_code')
    b=sectors[sectors.year.eq(end)].set_index('sector_code')
    c=pd.DataFrame(index=a.index)
    c['period']=f'{start}-{end}'
    for col in cols:
        c[col+'_change']=b[col]-a[col]
        c[col+'_growth_pct']=(b[col]/a[col].replace(0,np.nan)-1)*100
    c['fx_share_change_pp']=b.fx_share_pct-a.fx_share_pct
    changes.append(c.reset_index())
    for sector in names:
        x=div[div.sector_code.eq(sector)&div.year.eq(start)].set_index('division')
        y=div[div.sector_code.eq(sector)&div.year.eq(end)].set_index('division')
        shared=x.index.intersection(y.index)
        z=pd.DataFrame(index=shared)
        z['division_name']=z.index.map(labels)
        z['sector_code']=sector; z['period']=f'{start}-{end}'
        for col in cols:
            z[col+'_change']=y[col]-x[col]
        z['coverage_note']='matched division'
        if set(x.index)!=set(y.index):
            z.loc[-1,'division_name']='Непорівнянне охоплення (розділ 12 відсутній у 2025)'
            z.loc[-1,'sector_code']=sector; z.loc[-1,'period']=f'{start}-{end}'
            z.loc[-1,'coverage_note']='Residual of sums of published rows; not a confirmed debt reduction'
            for col in cols:
                z.loc[-1,col+'_change']=y.loc[y.index.difference(x.index),col].sum()-x.loc[x.index.difference(y.index),col].sum()
        denominator=b.loc[sector,'total_mn']-a.loc[sector,'total_mn']
        z['net_change_contribution_pct']=z.total_mn_change/denominator*100 if denominator!=0 else np.nan
        assert np.isclose(z.total_mn_change.sum(),denominator)
        contributions.append(z.reset_index())
changes=pd.concat(changes,ignore_index=True)
contributions=pd.concat(contributions,ignore_index=True)
for df,name in [(detail,'source_rows'),(sectors,'sector_balances'),(changes,'sector_changes'),(contributions,'division_contributions')]:
    df.to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig')
print('BALANCES'); print(sectors.round(2).to_string(index=False))
print('CHANGES'); print(changes.round(2).to_string(index=False))
for sector in names:
    q=contributions[contributions.sector_code.eq(sector)&contributions.period.eq('2024-2025')]
    print('TOP',sector); print(q.reindex(q.total_mn_change.abs().sort_values(ascending=False).index).head(8)[['division','division_name','total_mn_change','uah_mn_change','fx_mn_change','net_change_contribution_pct']].round(2).to_string(index=False))

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(13,10))
for ax,sector in zip(axes.flat,names):
    q=sectors[sectors.sector_code.eq(sector)]
    x=np.arange(3)
    ax.bar(x,q.uah_mn/1000,color='#2563EB',label='Гривневі')
    ax.bar(x,q.fx_mn/1000,bottom=q.uah_mn/1000,color='#D97706',label='Валютні у гривневому еквіваленті')
    for i,row in enumerate(q.itertuples()):
        ax.text(i,row.total_mn/1000,f'{row.total_mn/1000:.1f}\nFX {row.fx_share_pct:.1f}%',ha='center',va='bottom',fontsize=10)
    ax.set_xticks(x,['2023','2024','2025']); ax.set_title(names[sector],loc='left'); ax.set_ylabel('млрд грн'); ax.margins(y=.25); ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
fig.suptitle('Кредитні залишки: гривнева та валютна складові',fontsize=17,y=.98)
fig.legend(*axes.flat[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.075),ncol=2,frameon=False)
fig.text(.05,.025,'НБУ: великі та середні суб’єкти, КВЕД C/F/G/H; на 1 жовтня кожного року.\nFX — частка валютних кредитів. Шкали панелей різні. Валютні суми включають вплив переоцінки.',fontsize=10,color='#555555')
fig.tight_layout(rect=[0,.14,1,.95])
for ext in ['png','svg']: fig.savefig(FIG/f'currency_structure.{ext}',dpi=170)
plt.close(fig)
fig,axes=plt.subplots(2,2,figsize=(15,11))
import textwrap
for ax,sector in zip(axes.flat,names):
    q=contributions[contributions.sector_code.eq(sector)&contributions.period.eq('2024-2025')].copy()
    q['label']=q.division.astype(str)+' — '+q.division_name
    q.loc[q.division.eq(-1),'label']='Непорівнянне охоплення: розділ 12'
    if len(q)>7:
        indices=q.total_mn_change.abs().nlargest(6).index
        other=q.loc[~q.index.isin(indices),'total_mn_change'].sum()
        q=pd.concat([q.loc[indices],pd.DataFrame([{'label':'Решта розділів (сума)','total_mn_change':other}])],ignore_index=True)
    q=q.sort_values('total_mn_change')
    vals=q.total_mn_change/1000
    bars=ax.barh(range(len(q)),vals,color=['#2563EB' if v>=0 else '#D97706' for v in vals])
    ax.bar_label(bars,fmt='%+.2f',padding=3,fontsize=9)
    ax.set_yticks(range(len(q)),[textwrap.fill(t,34) for t in q.label],fontsize=9)
    ax.axvline(0,color='#555555',lw=.8); ax.set_title(names[sector],loc='left'); ax.set_xlabel('Зміна загальних залишків, млрд грн'); ax.margins(x=.25); ax.grid(axis='x',alpha=.2); ax.set_axisbelow(True)
fig.suptitle('Які підгалузі сформували зміну кредитних залишків у 2025 році?',fontsize=16,y=.99)
fig.text(.03,.02,'НБУ: великі та середні суб’єкти; 01.10.2025 проти 01.10.2024; усі валюти у гривневому еквіваленті.\nПромисловість: шість найбільших внесків і решта (включає −0,85 млрд грн через відсутність розділу 12 у 2025).\nЦей залишковий внесок не доводить погашення. Шкали різні; зміни залишків не дорівнюють новим видачам.',fontsize=9,color='#555555')
fig.tight_layout(rect=[0,.08,1,.97],h_pad=3,w_pad=3)
for ext in ['png','svg']: fig.savefig(FIG/f'division_changes.{ext}',dpi=170)
plt.close(fig)
