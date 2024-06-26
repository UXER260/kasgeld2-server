import datetime

from main import *

month_map = {
    1: "januari",
    2: "februari",
    3: "maart",
    4: "april",
    5: "mei",
    6: "juni",
    7: "juli",
    8: "augustus",
    9: "september",
    10: "oktober",
    11: "november",
    12: "december",
}


def user_id_if_exists(username: str):  # geeft user_id alleen wanneer user bestaat
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"""
        SELECT id FROM users where name = "{username}"
        """)

        output = c.fetchone()
    if output:
        return output[0]
    return None  # gebruiker bestaat niet


def check_manage_monthly_saldo_updates(username: str):
    user_id = user_id_if_exists(username)
    if not user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker `{username}` bestaat niet")  # gebruiker bestaat niet

    user_data = get_raw_user_data(username, update_monthly_kasgeld=False)
    last_update_date = datetime.date.fromtimestamp(user_data.last_salary_update_timestamp)
    last_update_year, last_update_month = last_update_date.year, last_update_date.month

    current_date_time = datetime.datetime.now()

    months_to_account_for = (current_date_time.year * 12 + current_date_time.month) - (
            last_update_year * 12 + last_update_month)
    print("MONTHS:", months_to_account_for)
    if not months_to_account_for > 0:  # als je geen recht hebt op kasgeld:
        return True
    for month in range(months_to_account_for):
        transaction_month = (last_update_month + month) % 12 + 1

        # je krijgt standaard 10 × kasgeld (in plaats van 12)
        if transaction_month in config[
            "month_salary_blacklist"
        ]:
            continue
        # # kasgeld_datum = f"{}"

        month_name = month_map[transaction_month]
        transaction_year = int(last_update_year + month / 12)

        saldo_after_transaction = user_data.saldo + config["salary_amount"]
        print("SALARY:", config["salary_amount"])
        title = f"Kasgeld voor {month_name} {transaction_year}"
        description = f"""Maandelijks kasgeld voor {month_name} {transaction_year}.\nKasgeld wordt niet in de maanden {", ".join([month_map[m_] for m_ in [m for m in config["month_salary_blacklist"]]]).strip(", ")} bijgewerkt.
        \n\n{current_date_time.day}/{current_date_time.month}/{current_date_time.year}
        """

        transaction_timestamp = int(
            datetime.datetime.strptime(f'1/{transaction_month}/{transaction_year}', '%d/%m/%Y').strftime("%s"))

        transaction_info = TransactionField(
            saldo_after_transaction=saldo_after_transaction,
            title=title,
            description=description
        )
        set_saldo(
            username=username,
            transaction_info=transaction_info,
            transaction_made_timestamp=transaction_timestamp
        )

        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()

            c.execute(f"""
            UPDATE users SET last_salary_update_timestamp={transaction_timestamp}
            """)

            conn.commit()

        user_data.saldo = saldo_after_transaction

    return True


def get_raw_user_data(username: str, update_monthly_kasgeld=True):
    if update_monthly_kasgeld:
        check_manage_monthly_saldo_updates(username=username)

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"""
        SELECT id, name, saldo, last_salary_update_timestamp, creation_timestamp
        FROM users WHERE name = "{username}"
        """)

        output = c.fetchone()

    # bestaan van gebruiker is boven aan functie al geverifieerd, dus hoeft niet te checken of er output is.
    if not output:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker `{username}` bestaat niet")
    return RawUserData(
        user_id=output[0],
        name=output[1],
        saldo=output[2],
        last_salary_update_timestamp=output[3],
        creation_timestamp=output[4]
    )


def add_user(user_data: AddUser, transaction_made_timestamp=None):
    exists = user_id_if_exists(user_data.name)
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Gebruiker `{user_data.name}` bestaat al")

    current_time = int(time.time()) if transaction_made_timestamp is None else transaction_made_timestamp

    start_transaction = TransactionField(
        saldo_after_transaction=user_data.saldo,
        transaction_timestamp=current_time,
        title="Start bedrag",
        description=f"Start bedrag van {user_data.name}",
    )

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"""
        INSERT INTO users (name, creation_timestamp, saldo, last_salary_update_timestamp)
        VALUES ("{user_data.name}", {current_time}, {user_data.saldo}, {current_time})
        """)
        conn.commit()

        user_id = user_id_if_exists(user_data.name)

        c.execute(f"""
        INSERT INTO TRANSACTIONS (title, description, amount, saldo_after_transaction, transaction_timestamp, user_id)
        VALUES ("{start_transaction.title}", "{start_transaction.description}", {user_data.saldo},
        {start_transaction.saldo_after_transaction}, {current_time}, {user_id})
        """)

        conn.commit()

    return responses.Response(f"Gebruiker `{user_data.name}` succesvol toegevoegd", status_code=status.HTTP_200_OK)


def get_saldo(username: str):
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"""
        SELECT saldo FROM users where name = "{username}"
        """)
        output = c.fetchone()
    if output:
        return float(output[0])
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker `{username}` bestaat niet")  # gebruiker bestaat niet


def set_saldo(username, transaction_info: TransactionField, transaction_made_timestamp: float = None):
    user_id = user_id_if_exists(username)
    if not user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker `{username}` bestaat niet")

    current_time = int(time.time()) if transaction_made_timestamp is None else transaction_made_timestamp

    saldo_before_transaction = get_saldo(username)
    amount = transaction_info.saldo_after_transaction - saldo_before_transaction

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"""
                UPDATE users SET saldo = {transaction_info.saldo_after_transaction};
                """)

        c.execute(f"""
                INSERT INTO TRANSACTIONS
                (title, description, amount, saldo_after_transaction, transaction_timestamp, user_id)
                VALUES ("{transaction_info.title}", "{transaction_info.description}", {amount},
                {transaction_info.saldo_after_transaction}, {current_time}, {user_id})
                """)


def delete_user(username: str, leave_transactions=False):
    user_id = user_id_if_exists(username)
    if not user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker `{username}` bestaat niet")

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute(f"DELETE FROM users WHERE id = {user_id};")

        if not leave_transactions:  # als transacties ook moeten worden verwijderd:
            c.execute(f"DELETE FROM transactions WHERE user_id = {user_id};")

        conn.commit()

    return responses.Response(status_code=status.HTTP_200_OK)
