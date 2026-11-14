"""Equal-weight means of nine month-end snapshots; not daily averages or new lending."""
from pathlib import Path
import pandas as pd
import numpy as np
from analyze_monthly_42 import load_monthly

OUT = Path(__file__).resolve().parents[1] / 'data/processed'
monthly_average_input = pd.concat([
    load_monthly(start=f'{year}-02-01', end=f'{year}-10-01')
    for year in (2024, 2025)
], ignore_index=True)
monthly_average_input['year'] = monthly_average_input['date'].dt.year
assert len(monthly_average_input) == 36
assert not monthly_average_input.duplicated(['size','date']).any()
assert monthly_average_input.groupby(['year','size']).size().eq(9).all()
amounts = ['total_mn','uah_mn','fx_mn']
combined = monthly_average_input.groupby(['year','date'], as_index=False)[amounts].sum()
combined['size'] = 'all'
averages = pd.concat([monthly_average_input, combined], ignore_index=True).groupby(['size','year'])[amounts].mean()
average_comparison = averages['total_mn'].unstack('year').reindex(['large','medium','all'])
average_comparison.columns = ['average_2024_mn','average_2025_mn']
average_comparison['change_mn'] = average_comparison.average_2025_mn - average_comparison.average_2024_mn
average_comparison['change_pct'] = (average_comparison.average_2025_mn / average_comparison.average_2024_mn - 1)*100
for year in (2024,2025):
    assert np.isclose(averages.loc[('all',year),'total_mn'], averages.loc[('large',year),'total_mn']+averages.loc[('medium',year),'total_mn'])
monthly_average_input.to_csv(OUT/'average_42_input.csv',index=False,encoding='utf-8-sig')
averages.to_csv(OUT/'average_42_by_currency.csv',encoding='utf-8-sig')
average_comparison.to_csv(OUT/'average_42_comparison.csv',encoding='utf-8-sig')
print(average_comparison.round(2).to_string())
print('PASS: 18 snapshots, 36 size/date observations; nine snapshots per year/size; totals reconcile.')
