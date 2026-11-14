"""Monthly division 42 balances. Dates come from filenames, not year folders."""
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1] / 'data/raw/monthly'
OUT = Path(__file__).resolve().parents[1] / 'data/processed'
SIZES = {"Суб'єкт великого підприємництва": 'large',
         "Суб'єкт середнього підприємництва": 'medium'}

def load_monthly(base=BASE, start='2024-10-01', end='2025-10-01'):
    rows = []
    dates = []
    for path in sorted(base.rglob('Loans_MSE_KVED_*.xlsx')):
        date = pd.Timestamp(path.stem.removeprefix('Loans_MSE_KVED_'))
        if not pd.Timestamp(start) <= date <= pd.Timestamp(end):
            continue
        dates.append(date)
        book = pd.ExcelFile(path)
        sheets = [s for s in book.sheet_names if 'метод' not in s.lower()]
        assert len(sheets) == 1, path
        raw = pd.read_excel(book, sheet_name=sheets[0], header=None)
        assert 'Залишки коштів за кредитами' in str(raw.iloc[2, 3]), path
        assert 'національна' in str(raw.iloc[3, 4]), path
        assert 'іноземна' in str(raw.iloc[3, 5]), path
        assert 'тис' in str(raw.iloc[1, 0]), path
        data = raw.iloc[5:, :6].copy()
        data.columns = ['size', 'division', 'name', 'total', 'uah', 'fx']
        data['division'] = pd.to_numeric(data['division'], errors='raise')
        selected = data.loc[data['size'].isin(SIZES) & data['division'].eq(42)].copy()
        assert len(selected) == 2 and not selected['size'].duplicated().any(), path
        amounts = ['total', 'uah', 'fx']
        selected[amounts] = selected[amounts].apply(pd.to_numeric, errors='raise')
        assert selected[amounts].notna().all().all(), path
        assert (selected[amounts] >= 0).all().all(), path
        assert np.allclose(selected.total, selected.uah + selected.fx, atol=.01, rtol=0), path
        for _, row in selected.iterrows():
            rows.append({'date': date, 'size': SIZES[row['size']],
                         **{f'{c}_mn': row[c]/1000 for c in amounts},
                         'source_file': path.name, 'source_title': str(raw.iloc[0,0])})
    expected = list(pd.date_range(start, end, freq='MS'))
    assert sorted(dates) == expected, 'Missing or duplicate dates'
    result = pd.DataFrame(rows).sort_values(['size', 'date']).reset_index(drop=True)
    for col in ['total_mn', 'uah_mn', 'fx_mn']:
        result[f'{col}_change'] = result.groupby('size')[col].diff()
    return result

if __name__ == '__main__':
    monthly_42 = load_monthly()
    totals = monthly_42.groupby('date')[['total_mn','uah_mn','fx_mn']].sum()
    totals['change_mn'] = totals.total_mn.diff()
    monthly_42.to_csv(OUT/'monthly_42_by_size.csv', index=False, encoding='utf-8-sig')
    totals.to_csv(OUT/'monthly_42_totals.csv', encoding='utf-8-sig')
    print(totals.round(2).to_string())
    print('SIZE BALANCES')
    print(monthly_42.pivot(index='date', columns='size', values='total_mn').round(2).to_string())
    assert np.isclose(totals.total_mn.iloc[0], 3448.842125, atol=.001)
    assert np.isclose(totals.total_mn.iloc[-1], 1653.514608, atol=.001)
    print('PASS: 13 dates, 26 size/date observations; currency sums and endpoints verified.')
