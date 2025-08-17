import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent
from fake_useragent import UserAgent

# --- Глобальное отключение проверки SSL-сертификатов ---
# ВНИМАНИЕ: Это небезопасно и делает скрипт уязвимым для MitM-атак.
# Использовать только при невозможности решить проблемы с сертификатами иначе.
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Для старых версий Python, где проверка не включена по умолчанию
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Подавление предупреждений о небезопасных запросах для чистоты вывода
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def get_most_active_tickers():
    """
    Получает список самых активных тикеров с Yahoo Finance.
    Использует глобальную сессию requests без проверки SSL и случайный User-Agent.
    """
    url = "https://finance.yahoo.com/markets/stocks/most-active/"
    try:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        # Явно отключаем проверку сертификата для requests,
        # так как глобальный патч может не работать в некоторых средах (например, за прокси).
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()  # Вызовет исключение для кодов 4xx/5xx

        soup = BeautifulSoup(response.text, 'html.parser')

        # Селектор для тикеров на странице 'Most Active'
        ticker_links = soup.select('a[data-testid="table-cell-ticker"]')

        if not ticker_links:
            print("Не удалось найти тикеры на странице. Возможно, структура сайта изменилась.")
            return []

        # Извлечение тикеров и удаление пробелов
        tickers = [link.text.strip() for link in ticker_links]

        # Удаление дубликатов с сохранением порядка
        unique_tickers = list(dict.fromkeys(tickers))

        print(f"Найдено {len(unique_tickers)} уникальных тикеров.")
        return unique_tickers

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return []


def compute_rsi(data, window=14):
    """Рассчитывает RSI для данных."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_verdict_report(signals, sector_performance, display_df):
    """Генерирует и выводит сводку и вердикт для каждой интересной акции."""
    if not signals:
        return

    print("\n" + "*"*30 + " СВОДКА И ВЕРДИКТ " + "*"*30)

    # Сортируем акции для более последовательного вывода
    sorted_tickers = sorted(signals.keys())

    for ticker in sorted_tickers:
        sig = signals[ticker]
        raw_data = sig['data'] # "Сырые" данные для анализа
        display_data = display_df.loc[ticker] # Отформатированные данные для вывода
        summary_parts = []
        verdict = ""

        # Формируем сводку
        if raw_data['Изменение (%)'] > 0:
            summary_parts.append(f"Сильный рост ({display_data['Изменение (%)']})")
        else:
            summary_parts.append(f"Значительное падение ({display_data['Изменение (%)']})")

        if sig['high_volume']:
            summary_parts.append(f"на аномально высоком объёме ({display_data['Отношение объёма']})")

        if sig['golden_cross']:
            summary_parts.append("после 'Золотого пересечения'")
        if sig['macd_buy']:
            summary_parts.append("с бычьим пересечением MACD")
        if sig['macd_sell']:
            summary_parts.append("с медвежьим пересечением MACD")
        if sig['bb_breakout']:
            summary_parts.append("и пробила верхнюю Полосу Боллинджера")
        if sig['bb_reversal']:
            summary_parts.append("и коснулась нижней Полосы Боллинджера")

        # Формируем вердикт
        fundamental_verdict = ""
        pe = raw_data['P/E']
        div_yield = raw_data['Див. дох. (%)']

        if pd.notna(pe) and 0 < pe < 20 and pd.notna(div_yield) and div_yield > 0:
            fundamental_verdict = "Фундаментально устойчива: компания прибыльна (P/E: {}) и платит дивиденды ({}).".format(display_data['P/E'], display_data['Див. дох. (%)'])
        elif pd.isna(pe) or pe <= 0:
            fundamental_verdict = "Высокие фундаментальные риски: компания убыточна."
        else:
            fundamental_verdict = "Смешанные фундаментальные показатели."


        technical_verdict = ""
        if sig['macd_buy'] and sig['golden_cross']:
             technical_verdict = "Сильный технический сигнал к покупке ('Золотое пересечение' + MACD)."
        elif sig['macd_buy'] and not sig['overbought']:
            technical_verdict = "Технический сигнал к покупке (пересечение MACD)."
        elif sig['macd_sell']:
            technical_verdict = "Технический сигнал к продаже (пересечение MACD)."
        elif sig['oversold'] or sig['bb_reversal']:
            technical_verdict = "Спекулятивный сигнал к отскоку (RSI: {}).".format(display_data['RSI (14)'])
        elif sig['overbought'] or sig['bb_breakout']:
            technical_verdict = "Технический риск перегрева (RSI: {}).".format(display_data['RSI (14)'])

        verdict = f"{technical_verdict} {fundamental_verdict}"

        # Добавляем контекст сектора
        sector = raw_data['Сектор']
        if sector in sector_performance.index and sector_performance.loc[sector] > 0:
            summary_parts.append(f"в лидирующем секторе '{sector}'")
        elif sector in sector_performance.index:
            summary_parts.append(f"в отстающем секторе '{sector}'")

        # Вывод отчета по акции
        print(f"\n--- {ticker} ({sector}) ---")
        print("Сводка: " + " ".join(summary_parts) + ".")
        if verdict:
            print(f"Вердикт: {verdict}")

    print("\n" + "*"*80)

def fetch_single_ticker_info(ticker):
    """Получает информацию для одного тикера."""
    try:
        info = yf.Ticker(ticker).info
        return ticker, {
            'P/E': info.get('trailingPE', None),
            'Dividend Yield': info.get('dividendYield', None),
            'Market Cap': info.get('marketCap', None),
            'Sector': info.get('sector', 'N/A')
        }
    except Exception as e:
        print(f"Не удалось загрузить фундаментальные данные для {ticker}: {e}")
        return ticker, {'P/E': None, 'Dividend Yield': None, 'Market Cap': None, 'Sector': 'N/A'}

def get_fundamental_data(tickers):
    """Получает фундаментальные данные для списка тикеров с использованием многопоточности."""
    fundamentals = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Запускаем задачи и получаем будущие объекты
        future_to_ticker = {executor.submit(fetch_single_ticker_info, ticker): ticker for ticker in tickers}

        # Собираем результаты по мере их готовности
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker, data = future.result()
            fundamentals[ticker] = data

    return fundamentals

def analyze_market_state():
    """Анализирует общее состояние рынка по индексу S&P 500."""
    try:
        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(period="51d")

        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        change = ((last_close - prev_close) / prev_close) * 100

        sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]

        state = "Растущий" if last_close > sma50 else "Падающий"
        trend = "выше SMA50" if last_close > sma50 else "ниже SMA50"

        print("="*80)
        print(f"Состояние рынка: {state} (S&P 500: {change:+.2f}%, {trend})")
        print("="*80)

        return state
    except Exception as e:
        print(f"Не удалось проанализировать состояние рынка: {e}")
        return "Неопределенное"

def analyze_stocks(tickers, market_state):
    """
    Загружает данные по списку тикеров, рассчитывает изменение
    и выводит итоговую таблицу.
    """
    if not tickers:
        print("Список тикеров пуст. Анализ невозможен.")
        return

    print(f"Анализирую {len(tickers)} самых активных акций...\n")

    try:
        # Загружаем данные за последний год (примерно 252 торговых дня) для расчета скользящих средних
        data = yf.download(tickers, period="252d", progress=False, auto_adjust=True)

        # Получаем фундаментальные данные
        fundamental_data = get_fundamental_data(tickers)


        if data.empty:
            print("Не удалось загрузить данные. Проверьте тикеры или интернет-соединение.")
            return

        # --- Расчет технических индикаторов ---
        close_prices = data['Close']

        # Простая скользящая средняя (SMA)
        sma_50 = close_prices.rolling(window=50).mean()
        sma_200 = close_prices.rolling(window=200).mean()

        # Экспоненциальная скользящая средняя (EMA)
        ema_20 = close_prices.ewm(span=20, adjust=False).mean()

        # Анализ объёма торгов
        volume_data = data['Volume']
        avg_volume_30d = volume_data.rolling(window=30).mean()
        latest_volume = volume_data.iloc[-1]

        # Расчет RSI
        rsi = compute_rsi(close_prices)

        # Расчет MACD
        exp12 = close_prices.ewm(span=12, adjust=False).mean()
        exp26 = close_prices.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        macd_signal = macd.ewm(span=9, adjust=False).mean()

        # Расчет Полос Боллинджера
        sma_20_bb = close_prices.rolling(window=20).mean()
        std_20_bb = close_prices.rolling(window=20).std()
        bb_upper = sma_20_bb + (std_20_bb * 2)
        bb_lower = sma_20_bb - (std_20_bb * 2)

        if len(close_prices) < 2:
            print("Недостаточно данных для анализа (нужно минимум 2 дня).")
            return

        # Отсев тикеров, для которых не удалось загрузить данные
        valid_tickers = close_prices.columns[close_prices.iloc[-1].notna()]

        previous_close = close_prices.iloc[-2][valid_tickers]
        latest_close = close_prices.iloc[-1][valid_tickers]

        # Создание DataFrame с результатами
        results = pd.DataFrame(index=valid_tickers)
        results['Предыдущее закрытие'] = previous_close
        results['Последнее закрытие'] = latest_close
        results['Изменение ($)'] = latest_close - previous_close
        results['Изменение (%)'] = ((latest_close - previous_close) / previous_close) * 100
        results['EMA_20'] = ema_20.iloc[-1][valid_tickers]
        results['SMA_50'] = sma_50.iloc[-1][valid_tickers]
        results['SMA_200'] = sma_200.iloc[-1][valid_tickers]
        results['Объём (вчера)'] = latest_volume[valid_tickers]
        results['Средний объём (30д)'] = avg_volume_30d.iloc[-1][valid_tickers]
        results['Отношение объёма'] = (results['Объём (вчера)'] / results['Средний объём (30д)'])
        results['RSI (14)'] = rsi.iloc[-1][valid_tickers]
        results['MACD'] = macd.iloc[-1][valid_tickers]
        results['MACD_Signal'] = macd_signal.iloc[-1][valid_tickers]
        results['BB_Upper'] = bb_upper.iloc[-1][valid_tickers]
        results['BB_Lower'] = bb_lower.iloc[-1][valid_tickers]
        results['P/E'] = pd.Series({k: v['P/E'] for k, v in fundamental_data.items()})
        results['Див. дох. (%)'] = pd.Series({k: v['Dividend Yield'] for k, v in fundamental_data.items()})
        results['Капитализация'] = pd.Series({k: v['Market Cap'] for k, v in fundamental_data.items()})
        results['Сектор'] = pd.Series({k: v['Sector'] for k, v in fundamental_data.items()})

        # Сортировка по процентному изменению (по убыванию)
        results_sorted = results.sort_values(by='Изменение (%)', ascending=False)

        # --- Анализ "Золотого пересечения" ---
        golden_cross_stocks = []
        for ticker in valid_tickers:
            # Убедимся, что данных достаточно для анализа
            if sma_50[ticker].iloc[-2] and sma_200[ticker].iloc[-2]:
                # Проверяем, была ли SMA50 НИЖЕ SMA200 вчера
                was_below = sma_50[ticker].iloc[-2] < sma_200[ticker].iloc[-2]
                # Проверяем, стала ли SMA50 ВЫШЕ SMA200 сегодня
                is_above = sma_50[ticker].iloc[-1] > sma_200[ticker].iloc[-1]

                if was_below and is_above:
                    golden_cross_stocks.append(ticker)

        # --- Анализ аномального объёма ---
        high_volume_stocks = results_sorted[results_sorted['Отношение объёма'] > 2.0]

        # --- Анализ RSI ---
        overbought_stocks = results_sorted[results_sorted['RSI (14)'].astype(float) > 70]
        oversold_stocks = results_sorted[results_sorted['RSI (14)'].astype(float) < 30]

        # --- Анализ MACD (Более надежный метод) ---
        macd_hist = macd - macd_signal
        # Бычье пересечение: гистограмма пересекает ноль снизу вверх
        macd_buy_signal_mask = (macd_hist.iloc[-1] > 0) & (macd_hist.iloc[-2] < 0)
        macd_buy_signal_tickers = macd_buy_signal_mask[macd_buy_signal_mask].index.tolist()
        # Медвежье пересечение: гистограмма пересекает ноль сверху вниз
        macd_sell_signal_mask = (macd_hist.iloc[-1] < 0) & (macd_hist.iloc[-2] > 0)
        macd_sell_signal_tickers = macd_sell_signal_mask[macd_sell_signal_mask].index.tolist()

        # --- Анализ Полос Боллинджера ---
        bb_breakout = results_sorted[results_sorted['Последнее закрытие'].astype(float) > results_sorted['BB_Upper'].astype(float)]
        bb_reversal = results_sorted[results_sorted['Последнее закрытие'].astype(float) < results_sorted['BB_Lower'].astype(float)]


        # --- Сбор сигналов в словарь ---
        signals = {}
        interesting_tickers = set(golden_cross_stocks) | set(high_volume_stocks.index) | set(overbought_stocks.index) | set(oversold_stocks.index) | set(macd_buy_signal_tickers) | set(macd_sell_signal_tickers) | set(bb_breakout.index) | set(bb_reversal.index)

        # --- Создание копии для отображения и ее форматирование ---
        display_df = results_sorted.copy()
        display_df['Изменение ($)'] = display_df['Изменение ($)'].map('{:+.2f}'.format)
        display_df['Изменение (%)'] = display_df['Изменение (%)'].map('{:+.2f}%'.format)
        display_df['Предыдущее закрытие'] = display_df['Предыдущее закрытие'].map('{:.2f}'.format)
        display_df['Последнее закрытие'] = display_df['Последнее закрытие'].map('{:.2f}'.format)
        display_df['EMA_20'] = display_df['EMA_20'].map('{:.2f}'.format)
        display_df['SMA_50'] = display_df['SMA_50'].map('{:.2f}'.format)
        display_df['SMA_200'] = display_df['SMA_200'].map('{:.2f}'.format)
        display_df['Объём (вчера)'] = display_df['Объём (вчера)'].map('{:,.0f}'.format)
        display_df['Средний объём (30д)'] = display_df['Средний объём (30д)'].map('{:,.0f}'.format)
        display_df['RSI (14)'] = display_df['RSI (14)'].map('{:.2f}'.format)
        display_df['MACD'] = display_df['MACD'].map('{:.2f}'.format)
        display_df['MACD_Signal'] = display_df['MACD_Signal'].map('{:.2f}'.format)
        display_df['BB_Upper'] = display_df['BB_Upper'].map('{:.2f}'.format)
        display_df['BB_Lower'] = display_df['BB_Lower'].map('{:.2f}'.format)
        display_df['P/E'] = display_df['P/E'].apply(lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A')
        display_df['Див. дох. (%)'] = display_df['Див. дох. (%)'].apply(lambda x: f'{x:.2%}' if pd.notna(x) and x > 0 else '0.00%')
        display_df['Капитализация'] = display_df['Капитализация'].apply(lambda x: f'{x:,.0f}' if pd.notna(x) else 'N/A')
        display_df['Отношение объёма'] = display_df['Отношение объёма'].map('{:.2f}x'.format)

        print("Результаты анализа акций (отсортировано по процентному изменению):")
        print(display_df.to_string())
        print("\n" + "="*80)

        for ticker in interesting_tickers:
            signals[ticker] = {
                'golden_cross': ticker in golden_cross_stocks,
                'high_volume': ticker in high_volume_stocks.index,
                'overbought': ticker in overbought_stocks.index,
                'oversold': ticker in oversold_stocks.index,
                'macd_buy': ticker in macd_buy_signal_tickers,
                'macd_sell': ticker in macd_sell_signal_tickers,
                'bb_breakout': ticker in bb_breakout.index,
                'bb_reversal': ticker in bb_reversal.index,
                'data': results_sorted.loc[ticker] # Используем исходные, неформатированные данные
            }

        # --- Анализ силы секторов ---
        sector_performance = results.groupby('Сектор')['Изменение (%)'].mean().sort_values(ascending=False)

        # Передаем данные и сигналы для генерации вердикта
        generate_verdict_report(signals, sector_performance, display_df)

        # --- Вывод рейтинга секторов ---
        print("\n" + "="*30 + " РЕЙТИНГ СЕКТОРОВ " + "="*30)
        for sector, perf in sector_performance.items():
            print(f"- {sector}: {perf:+.2f}%")
        print("="*80)

        # Вывод лидера роста
        if not results_sorted.empty:
            top_performer = results_sorted.index[0]
            top_change = results_sorted.iloc[0]['Изменение (%)']
            print(f"\nВывод: Наибольший рост показала акция {top_performer} с изменением {top_change}.")
        else:
            print("\nНе удалось проанализировать ни одной акции.")

        print("Помните, что прошлые показатели не гарантируют будущих результатов.")
        print("="*80)

    except Exception as e:
        print(f"Произошла ошибка во время анализа: {e}")


if __name__ == "__main__":
    # Основной блок выполнения
    print("ВНИМАНИЕ: Проверка SSL-сертификатов глобально отключена.")

    market_state = analyze_market_state()

    print("Получение списка самых активных акций с Yahoo Finance...")
    tickers_to_analyze = get_most_active_tickers()

    analyze_stocks(tickers_to_analyze, market_state)
