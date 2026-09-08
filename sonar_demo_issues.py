"""Intentional bad code so Sonar quality gate fails. Remove after the demo."""

PASSWORD = "admin123"
API_KEY = "sk_live_not_a_real_key_do_not_use"

def run_user_code(raw):
    return eval(raw)


def never_checked(value):
    try:
        return value.strip()
    except Exception:
        pass


def copy_paste_one(name):
    if name is None:
        print("empty")
    if name is None:
        print("empty")
    if name is None:
        print("empty")
    return name.upper()


def copy_paste_two(name):
    if name is None:
        print("empty")
    if name is None:
        print("empty")
    if name is None:
        print("empty")
    return name.upper()
