"""Load test for BMS-NF-001: 95 % of deposit, withdrawal and transfer requests within 3 seconds with 50 users.

Run (from the repository root, with the seed data loaded):

    python -m scripts.seed
    uvicorn app.main:app
    locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 2m --host http://127.0.0.1:8000 --csv docs/test-plan/load-test

Users: half are Tellers (deposit and withdraw), half are Customers (transfer between the seeded accounts).
The login is not measured (BMS-NF-001 covers the three money endpoints). All amounts are Rs 1 so no limit (minimum balance, daily limit) is ever reached. Every seeded user has the password
"Passw0rd!" (demo data only). Customer N owns accounts 1000000001+2(N-1) (Savings) and 1000000002+2(N-1) (Current).
"""
import itertools
import random

import requests
from locust import HttpUser, between, task

PASSWORD = "Passw0rd!"
TELLERS = ["teller1", "teller2", "teller3"]
CUSTOMER_IDS = [1, 2, 3, 4, 5]
ALL_ACCOUNTS = [str(1000000000 + n) for n in range(1, 11)]
_counter = itertools.count()


def customer_accounts(customer_id: int) -> list[str]:
    first = 1000000001 + 2 * (customer_id - 1)
    return [str(first), str(first + 1)]


class BankUser(HttpUser):
    abstract = True
    wait_time = between(0.2, 1.0)

    def login(self, username: str) -> None:
        """Logs in with a plain request, so the login is NOT part of the measured statistics:
        BMS-NF-001 covers deposit, withdrawal and transfer only."""
        response = requests.post(
            self.host + "/auth/login", json={"username": username, "password": PASSWORD}, timeout=120
        )
        response.raise_for_status()
        self.client.headers["Authorization"] = f"Bearer {response.json()['token']}"


class TellerUser(BankUser):
    weight = 1

    def on_start(self):
        self.login(TELLERS[next(_counter) % len(TELLERS)])

    @task(3)
    def deposit(self):
        self.client.post(
            "/transactions/deposit",
            json={"accountId": random.choice(ALL_ACCOUNTS), "amount": "1"},
            name="/transactions/deposit",
        )

    @task(2)
    def withdraw(self):
        self.client.post(
            "/transactions/withdraw",
            json={"accountId": random.choice(ALL_ACCOUNTS), "amount": "1"},
            name="/transactions/withdraw",
        )


class CustomerUser(BankUser):
    weight = 1

    def on_start(self):
        self.customer_id = CUSTOMER_IDS[next(_counter) % len(CUSTOMER_IDS)]
        self.login(str(self.customer_id))

    @task
    def transfer(self):
        source = random.choice(customer_accounts(self.customer_id))
        destination = random.choice([a for a in ALL_ACCOUNTS if a != source])
        self.client.post(
            "/transactions/transfer",
            json={"fromAccount": source, "toAccount": destination, "amount": "1"},
            name="/transactions/transfer",
        )
