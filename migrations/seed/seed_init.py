import sys
import os
from migrations.seed.seed_users import seed_users
from migrations.seed.seed_roles import seed_roles
from migrations.seed.seed_company import seed_company

if __name__ == "__main__":
    seed_users()
    seed_roles()
    seed_company()