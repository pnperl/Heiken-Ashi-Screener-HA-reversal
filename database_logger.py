import sqlite3

class DatabaseLogger:
    def __init__(self, db_name='trades.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY,
            trade_type TEXT,
            entry_price REAL,
            exit_price REAL,
            entry_time TEXT,
            exit_time TEXT,
            performance REAL
        )''')
        self.conn.commit()

    def log_trade(self, trade_type, entry_price, exit_price, entry_time, exit_time):
        performance = exit_price - entry_price if trade_type == 'buy' else entry_price - exit_price
        cursor = self.conn.cursor()
        cursor.execute('''INSERT INTO trades (trade_type, entry_price, exit_price, entry_time, exit_time, performance)
                          VALUES (?, ?, ?, ?, ?, ?)''', 
                          (trade_type, entry_price, exit_price, entry_time, exit_time, performance))
        self.conn.commit()

    def fetch_all_trades(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM trades')
        return cursor.fetchall()

    def close(self):
        self.conn.close()

# Example Usage:
# logger = DatabaseLogger()
# logger.log_trade('buy', 100.0, 110.0, '2026-03-07 11:00:00', '2026-03-07 11:30:00')
# print(logger.fetch_all_trades())
# logger.close()