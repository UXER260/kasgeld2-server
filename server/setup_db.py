import sqlite3
import time

from main import load_config

config = load_config()


def setup():
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name text NOT NULL,
                email text NOT NULL UNIQUE,
                password text NOT NULL,
                banned INTEGER NOT NULL
            );
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS user_data(
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name text NOT NULL UNIQUE,
                creation_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                money REAL NOT NULL,
                last_salary_date TEXT DEFAULT (CURRENT_TIMESTAMP)
            );
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions(
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                saldo_before_transaction REAL NOT NULL,
                date_time TEXT CURRENT_TIMESTAMP
            );
            """  # amount: ± geld
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
