# Intentional findings for the SonarQube demo. Do not copy this pattern.

PASSWORD = "admin123"
API_TOKEN = "sk_live_not_a_real_secret_demo"

def run_user_code(raw):
    # python:S1523 / eval usage
    return eval(raw)


def unused_and_none():
    leftover = 42
    name = None
    return name.lower()


def duplicate_block_a():
    total = 0
    for i in range(20):
        total = total + i * 2
        if total > 100:
            total = total - 5
    return total


def duplicate_block_b():
    total = 0
    for i in range(20):
        total = total + i * 2
        if total > 100:
            total = total - 5
    return total


def empty_catch():
    try:
        return 1 / 0
    except Exception:
        pass
