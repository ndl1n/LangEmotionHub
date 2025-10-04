import re

def is_valid_email(email):
    """
    驗證電子郵件是否合法，允許含多層域名的郵箱。

    電子郵件格式：
    - 本地部分可以包含字母、數字、點號、加號、連字符或下劃線
    - 必須包含 '@'
    - 域名部分允許多層域名（如 nccu.edu.tw 和 g.nccu.edu.tw）
    - 頂級域名至少需要2個字符

    Parameters:
    - email (str): 要驗證的電子郵件地址。

    Returns:
    - bool: 如果電子郵件地址合法，返回 True；否則返回 False。
    """
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$", email) is not None


def is_strong_password(password):
    """
    檢查密碼是否符合規範。

    密碼至少應包含8個字符，並且必須包含字母和數字。

    Parameters:
    - password (str): 要檢查的密碼。

    Returns:
    - bool: 如果密碼符合要求，返回 True；否則返回 False。
    """
    return (
        len(password) >= 8
        and re.search(r"[A-Za-z]", password)
        and re.search(r"[0-9]", password)
    )