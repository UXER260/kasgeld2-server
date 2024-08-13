# server/kasgeld.py
# Bevat alle functies om kasgeld en leerling data aan te passen

import datetime
import time
from models_and_imports import *

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

        c.execute("SELECT id FROM users where name = ?", (username,))

        output = c.fetchone()

    print(output)
    if output:
        return output[0]
    return None  # gebruiker bestaat niet


def username_if_exists(user_id: int):  # geeft user_id alleen wanneer user bestaat
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()

        c.execute("SELECT name FROM users where id = ?", (user_id,))

        output = c.fetchone()
    if output:
        return output[0]
    return None  # gebruiker bestaat niet


def manage_monthly_saldo_updates(user_id: int):
    if not username_if_exists(user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker bestaat niet")  # gebruiker bestaat niet

    userdata = get_raw_userdata(user_id, update_monthly_kasgeld=False)
    last_update_date = datetime.date.fromtimestamp(userdata.last_salary_update_timestamp)
    last_update_year, last_update_month = last_update_date.year, last_update_date.month

    current_date_time = datetime.datetime.now()
    months_to_account_for = (current_date_time.year * 12 + current_date_time.month) - (
            last_update_year * 12 + last_update_month)
    print("MONTHS:", months_to_account_for)
    if not months_to_account_for > 0:  # als je geen recht hebt op kasgeld:
        return True
    for month in range(months_to_account_for):
        transaction_month = (last_update_month + month) % 12 + 1  # berekent maand nummer

        # standaard krijgt ieder 10× kasgeld (in plaats van 12)
        if transaction_month in config[
            "month_salary_blacklist"
        ]:
            continue

        month_name = month_map[transaction_month]  # verkrijgt maand naam
        transaction_year = int(last_update_year + month / 12)  # Berekend jaar waarin kasgeld maan was/is

        saldo_after_transaction = userdata.saldo + config["salary_amount"]
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
        set_saldo(user_id=user_id, transaction_info=transaction_info, transaction_made_timestamp=transaction_timestamp)

        with sqlite3.connect(config["database_path"]) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET last_salary_update_timestamp = ? WHERE id = ?",
                      (transaction_timestamp, user_id))
            conn.commit()

        userdata.saldo = saldo_after_transaction

    return True


def get_raw_userdata(user_id: int = None, username: str = None, update_monthly_kasgeld=True):
    if not user_id and not username:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Moet op zijn MINST één van de velden 'user_id' en 'username' invullen")
    elif username:
        user_id = user_id_if_exists(username)
        if not user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker `{username}` bestaat niet")
    else:  # er is op zijn minst een veld ingevuld en dat is niet username, Dus is het user_id.
        username = username_if_exists(user_id)
        if not username:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker met id `{user_id}` bestaat niet")

    if update_monthly_kasgeld:
        manage_monthly_saldo_updates(user_id=user_id)

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, saldo, last_salary_update_timestamp, creation_timestamp FROM users WHERE id = ?",
                  (user_id,))
        output = c.fetchone()

    # bestaan van gebruiker is boven aan functie al geverifieerd, dus hoeft niet te checken of er output is.
    return RawUserData(
        user_id=output[0],
        name=output[1],
        saldo=output[2],
        last_salary_update_timestamp=output[3],
        creation_timestamp=output[4]
    )


def add_user(userdata: AddUser, transaction_made_timestamp=None):
    if not userdata.name and type(userdata.name) is str:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{repr(userdata.name)}Voer geldige username in")
    exists = user_id_if_exists(userdata.name)
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Gebruiker `{userdata.name}` bestaat al")

    current_time = int(time.time()) if transaction_made_timestamp is None else transaction_made_timestamp

    start_transaction = TransactionField(
        saldo_after_transaction=userdata.saldo,
        transaction_timestamp=current_time,
        title="Start bedrag",
        description=f"Start bedrag van {userdata.name}",
    )

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (name, creation_timestamp, saldo, last_salary_update_timestamp) VALUES (?, ?, ?, ?)",
            (userdata.name, current_time, userdata.saldo, current_time))
        conn.commit()

        user_id = user_id_if_exists(userdata.name)

        c.execute("""
            INSERT INTO TRANSACTIONS
            (title, description, amount, saldo_after_transaction, transaction_timestamp, user_id)
            VALUES (?, ?, ?, ?, ?, ?)""",
                  (start_transaction.title, start_transaction.description, userdata.saldo,
                   start_transaction.saldo_after_transaction, current_time, user_id))
        conn.commit()

    return responses.Response(f"Gebruiker `{userdata.name}` succesvol toegevoegd", status_code=status.HTTP_200_OK)


def get_saldo(user_id: int):
    username = username_if_exists(user_id)
    if not username:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker met id `{user_id}` bestaat niet")
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT saldo FROM users WHERE name = ?", (username,))
        output = c.fetchone()
    if output:
        return float(output[0])


def set_saldo(user_id: int, transaction_info: TransactionField, transaction_made_timestamp: float = None):
    username = username_if_exists(user_id)
    if not username:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker met id `{user_id}` bestaat niet")

    current_time = int(time.time()) if transaction_made_timestamp is None else transaction_made_timestamp

    saldo_before_transaction = get_saldo(user_id)
    amount = transaction_info.saldo_after_transaction - saldo_before_transaction
    print(f"{transaction_info.saldo_after_transaction} - {saldo_before_transaction} = {amount}")

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET saldo = ? WHERE id = ?", (transaction_info.saldo_after_transaction, user_id))
        c.execute("""
        INSERT INTO TRANSACTIONS
        (title, description, amount, saldo_after_transaction, transaction_timestamp, user_id)
        VALUES (?, ?, ?, ?, ?, ?)""",
                  (transaction_info.title, transaction_info.description, amount,
                   transaction_info.saldo_after_transaction, current_time, user_id))
        conn.commit()
    return responses.Response(status_code=status.HTTP_200_OK)


def delete_user(user_id: int, leave_transactions=False):
    username = username_if_exists(user_id=user_id)
    if not username:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker met id `{user_id}` bestaat niet")

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))

        if not leave_transactions:  # als transacties ook moeten worden verwijderd:
            c.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        conn.commit()

    return responses.Response(status_code=status.HTTP_200_OK)


def rename_user(user_id: int, new_username: str):
    username = username_if_exists(user_id=user_id)
    if not username:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker met id `{user_id}` bestaat niet")

    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET name = ? WHERE id = ?", (new_username, user_id))
        conn.commit()
    return responses.Response(f"Gebruiker `{username}` is succesvol hernoemd naar `{new_username}`",
                              status_code=status.HTTP_200_OK)


def get_username_list():
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM users")
    output = [item[0] for item in c.fetchall()]
    return sorted(output)


def get_transaction_list(user_id):
    with sqlite3.connect(config["database_path"]) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id, title, description, amount, saldo_after_transaction, transaction_timestamp, user_id
            FROM transactions WHERE user_id = ?""",
            (user_id,))
        output = c.fetchall()

    if not output:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gebruiker met id `{user_id}` bestaat niet")

    return [
        RawTransactionData(
            transaction_id=transaction[0],
            title=transaction[1],
            description=transaction[2],
            amount=transaction[3],
            saldo_after_transaction=transaction[4],
            transaction_timestamp=transaction[5],
            user_id=transaction[6],
        ) for transaction in output
    ]
