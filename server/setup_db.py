import sqlite3


def setup():
    with sqlite3.connect("database.db") as conn:
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
                saldo_after_transaction REAL NOT NULL,
                date_time TEXT CURRENT_TIMESTAMP
            );
            """
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
                id INTEGER NOT NULL PRIMARY KEY,
                ip_address text,
                FOREIGN KEY(ip_address) REFERENCES ips(ip_address),
                FOREIGN KEY(id) REFERENCES admins(id)
            );
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
