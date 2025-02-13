import pandas as pd

from core.handle import BmacHandle

SPOT_SPLIT_MAP = {}

USDT_FUTURES_SPLIT_MAP = {
    'LUNAUSDT': ['LUNAUSDT', 'LUNA2USDT'],
    'DODOUSDT': ['DODOUSDT', 'DODOXUSDT'],
    'RAYUSDT': ['RAYUSDT', 'RAYSOLUSDT']
}


def get_normalized_symbol(s: str, split_map):
    for norm_sym, splits in split_map.items():
        if s in splits:
            s = norm_sym
            break
    if s.startswith('1000'):
        return s[4:]
    return s


def get_spot_swap_matches(spot_symbol_list, swap_symbol_list):

    spot_norms = [(sym, get_normalized_symbol(sym, SPOT_SPLIT_MAP)) for sym in spot_symbol_list]
    df_spot_norm = pd.DataFrame(spot_norms, columns=['spot', 'norm'])

    swap_norms = [(sym, get_normalized_symbol(sym, USDT_FUTURES_SPLIT_MAP)) for sym in swap_symbol_list]
    df_swap_norm = pd.DataFrame(swap_norms, columns=['swap', 'norm'])

    df_map = pd.merge(df_spot_norm, df_swap_norm, how='outer', on='norm')
    df_map.drop(columns='norm', inplace=True)
    df_map = df_map.sort_values(['spot', 'swap'], ignore_index=True)
    return df_map


def update_symbol_match(handle: BmacHandle, run_time):
    df_exginfo_spot = handle.exg_mgr.read_candle('exginfo_spot')
    spot_symbol_list = df_exginfo_spot['symbol'].to_list()

    df_exginfo_swap = handle.exg_mgr.read_candle('exginfo_swap')
    swap_symbol_list = df_exginfo_swap['symbol'].to_list()

    df_map = get_spot_swap_matches(spot_symbol_list, swap_symbol_list)

    handle.exg_mgr.set_candle('spot_swap_matches', run_time, df_map)
