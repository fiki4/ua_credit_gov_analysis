"""Check net changes across every size category, not borrower-level migrations."""
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1] / 'data/raw/monthly'
OUT = Path(__file__).resolve().parents[1] / 'data/processed'
frames = []
for date in ['2024-12-01', '2025-01-01']:
    paths = list(BASE.rglob(f'Loans_MSE_KVED_{date}.xlsx'))
    assert len(paths) == 1
    book = pd.ExcelFile(paths[0])
    sheets = [s for s in book.sheet_names if 'метод' not in s.lower()]
    assert len(sheets) == 1
    raw = pd.read_excel(book, sheet_name=sheets[0], header=None)
    assert 'тис' in str(raw.iloc[1, 0])
    assert 'Залишки коштів за кредитами' in str(raw.iloc[2, 3])
    data = raw.iloc[5:, :6].copy()
    data.columns = ['size', 'division', 'division_name', 'total', 'uah', 'fx']
    data['division'] = pd.to_numeric(data['division'], errors='raise')
    selected = data.loc[data['division'].eq(42)].copy()
    assert not selected['size'].duplicated().any()
    values = ['total', 'uah', 'fx']
    selected[values] = selected[values].apply(pd.to_numeric, errors='raise')
    assert selected[values].notna().all().all()
    assert np.allclose(selected.total, selected.uah + selected.fx, atol=.01, rtol=0)
    selected[values] = selected[values] / 1000
    selected['date'] = date
    selected['source_file'] = paths[0].name
    frames.append(selected)
assert set(frames[0]['size']) == set(frames[1]['size'])
assert len(frames[0]) == len(frames[1]) == 7
size_detail = pd.concat(frames, ignore_index=True)
size_comparison = size_detail.pivot(index='size', columns='date', values='total')
size_comparison['change_mn'] = size_comparison['2025-01-01'] - size_comparison['2024-12-01']
size_comparison['change_pct'] = (size_comparison['2025-01-01'] / size_comparison['2024-12-01'] - 1) * 100
total_decline = -size_comparison.change_mn.sum()
large_name = "Суб'єкт великого підприємництва"
large_decline_share = -size_comparison.loc[large_name, 'change_mn'] / total_decline * 100
size_comparison.to_csv(OUT / 'size_transition_42_comparison.csv', encoding='utf-8-sig')
size_detail.to_csv(OUT / 'size_transition_42_detail.csv', index=False, encoding='utf-8-sig')
print(size_comparison.round(2).to_string())
print('Large contribution to net decline, %:', round(large_decline_share, 2))
print('PASS: same seven categories, unique keys, complete values, currency sums reconcile.')
