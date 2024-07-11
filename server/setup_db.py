import sqlite3
import time

from main import load_config

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
                password text NOT NULL,
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
            CREATE TABLE IF NOT EXISTS logins(
                admin_id INTEGER NOT NULL PRIMARY KEY,
                ip_address text,
                FOREIGN KEY(ip_address) REFERENCES ips(ip_address),
                FOREIGN KEY(admin_id) REFERENCES admins(id)
            );
            """
        )

        c.execute(
            """
            INSERT OR IGNORE INTO admins (name, email, password, banned) VALUES
            ("Camillo de Jong", "cydejong@icloud.com", "123@K@sg3ld!", 0);
            """
        )

        c.execute(
            """
            INSERT OR IGNORE INTO logins (admin_id, ip_address) VALUES
            (1, "127.0.0.1");
            """
        )

        # # routines
        #
        # c.execute(
        #     """
        #
        #     """
        # )

        conn.commit()
        
        load_config(path=config["last_session_wipe_path"], default_config={"timestamp": int(time.time())})
