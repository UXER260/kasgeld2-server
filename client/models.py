from pydantic import BaseModel


class AdminLoginField(BaseModel):
    email: str
    password: str


class AdminSignupField(BaseModel):
    name: str
    email: str
    password: str


class AddUser(BaseModel):
    name: str
    saldo: float


class RawUserData(BaseModel):  # voor data direct uit database
    user_id: int
    name: str
    saldo: float
    last_salary_update_timestamp: int
    creation_timestamp: int


class TransactionField(BaseModel):
    saldo_after_transaction: float
    title: str
    description: str


class RawTransactionData(BaseModel):
    transaction_id: int
    title: str
    description: str
    amount: float
    saldo_after_transaction: float
    transaction_timestamp: int
    user_id: int
