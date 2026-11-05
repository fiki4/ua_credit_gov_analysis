"""Read the three supplied NBU snapshots; never modify the source workbooks."""
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1] / 'data' / 'raw'
OUT = Path(__file__).resolve().parents[1] / 'data' / 'processed'
SECTORS = {
    'C': 'Переробна промисловість',
    'F': 'Будівництво',
    'G': 'Оптова та роздрібна торгівля; ремонт автотранспортних засобів і мотоциклів',
    'H': "Транспорт, складське господарство, поштова та кур'єрська діяльність",
}
SIZES = ["Суб'єкт великого підприємництва", "Суб'єкт середнього підприємництва"]

def section(code):
    for letter, lo, hi in [('C', 10, 33), ('F', 41, 43), ('G', 45, 47), ('H', 49, 53)]:
        if lo <= code <= hi:
            return letter
    return None

def load_nbu():
    results = []
    for year in (2023, 2024, 2025):
        path = BASE / f'Loans_MSE_KVED_{year}-10-01.xlsx'
        raw = pd.read_excel(path, sheet_name=f'вересень {year}', header=None)
        assert raw.shape[1] == (21 if year == 2025 else 9)
        assert f'1 жовтня {year}' in str(raw.iloc[0, 0])
        assert 'тис' in str(raw.iloc[1, 0])
        assert 'Залишки коштів за кредитами' in str(raw.iloc[2, 3])
        npl_start = 9 if year == 2025 else 6
        assert 'непрацюючими' in str(raw.iloc[2, npl_start])
        cols = [0, 1, 2, 3, 4, 5, npl_start, npl_start + 1, npl_start + 2]
        data = raw.iloc[5:, cols].copy()
        data.columns = ['size', 'division', 'division_name', 'loans_total', 'loans_uah',
                        'loans_fx', 'npl_total', 'npl_uah', 'npl_fx']
        data['division'] = pd.to_numeric(data['division'], errors='raise').astype(int)
        assert not data.duplicated(['size', 'division']).any()
        numeric = list(data.columns[3:])
        data[numeric] = data[numeric].apply(pd.to_numeric, errors='raise')
        assert data[numeric].notna().all().all()
        for prefix in ('loans', 'npl'):
            assert np.allclose(data[f'{prefix}_total'], data[f'{prefix}_uah'] + data[f'{prefix}_fx'], atol=0.01, rtol=0)
        data['sector_code'] = data['division'].map(section)
        selected = data.loc[data['size'].isin(SIZES) & data['sector_code'].notna()]
        # Source anomalies outside the selected sectors are not corrected or imported.
        assert (selected[numeric] >= 0).all().all()
        for currency in ('total', 'uah', 'fx'):
            assert (selected[f'npl_{currency}'] <= selected[f'loans_{currency}'] + 0.01).all()
        assert set(selected['size']) == set(SIZES)
        grouped = selected.groupby('sector_code')[numeric].sum(min_count=1)
        assert set(grouped.index) == set(SECTORS)
        grouped = grouped.div(1000).rename(columns={c: f'{c}_mn' for c in numeric})
        grouped['npl_uah_share_pct'] = grouped['npl_uah_mn'].div(grouped['loans_uah_mn'].replace(0, np.nan)).mul(100)
        grouped['sector'] = grouped.index.map(SECTORS)
        grouped['year'] = year
        grouped['snapshot_date'] = f'{year}-10-01'
        grouped['size_scope'] = 'large_and_medium_NBU'
        grouped['npl_definition'] = 'Reg97_2025' if year == 2025 else 'Reg351_JQ'
        grouped['source_file'] = path.name
        results.append(grouped.reset_index())
    result = pd.concat(results, ignore_index=True).sort_values(['sector_code', 'year'])
    assert len(result) == 12 and not result.duplicated(['sector', 'year']).any()
    return result.reset_index(drop=True)

def merge_with_derzhstat(analysis_df, nbu_df):
    """Do not infer identical populations from a successful key match."""
    assert len(analysis_df) == 12
    assert analysis_df['period'].eq(analysis_df['year'].astype(str) + '-Q3').all()
    result = analysis_df.merge(nbu_df, on=['sector', 'year'], how='outer', validate='one_to_one', indicator=True)
    assert result['_merge'].eq('both').all(), 'Unmatched sector/year keys'
    return result.drop(columns='_merge')

if __name__ == '__main__':
    nbu_df = load_nbu()
    OUT.mkdir(parents=True, exist_ok=True)
    nbu_df.to_csv(OUT / 'nbu_sector_snapshots.csv', index=False, encoding='utf-8-sig')
    print(nbu_df[['sector_code', 'year', 'loans_uah_mn', 'npl_uah_share_pct', 'npl_definition']].round(2).to_string(index=False))
    print('PASS: 12 sector/year rows; numeric, duplicate, currency and NPL checks passed.')
