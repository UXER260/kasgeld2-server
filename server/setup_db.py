# server/setup_db.py
# stelt database in

from models_and_imports import *

config = load_config()


def setup():
    print(config)
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name text NOT NULL,
                email text NOT NULL UNIQUE,
                hashed_password text NOT NULL,
                creation_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                banned INTEGER NOT NULL
            );
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name text NOT NULL UNIQUE,
                saldo REAL NOT NULL,
                last_salary_update_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                creation_timestamp INTEGER DEFAULT (strftime('%s', 'now'))
            );
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                saldo_after_transaction REAL NOT NULL,
                transaction_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                user_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            """  # amount: ± geld, creation_timestamp: wanneer transactie was gemaakt
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS ips(
                ip_address text PRIMARY KEY,
                request_count INTEGER NOT NULL,
                banned INTEGER NOT NULL
            );
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions(
                ip_address text NOT NULL PRIMARY KEY,
                admin_id INTEGER NOT NULL,
                token text NOT NULL UNIQUE,
                creation_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY(ip_address) REFERENCES ips(ip_address),
                FOREIGN KEY(admin_id) REFERENCES admins(id)
            );
            """
        )

        conn.commit()
