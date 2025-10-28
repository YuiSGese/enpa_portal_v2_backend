import sys
import os
from migrations.seed.seed_users import seed_users
from migrations.seed.seed_roles import seed_roles

if __name__ == "__main__":
    seed_users()
    seed_roles()