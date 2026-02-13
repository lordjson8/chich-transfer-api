import base64

token = "WDRlZWxFY3F5dmNpM3Iwekx1djZxOmM0NTYwZmIyYTJhYjg3NDhhNTRmZTE1MjgwZjVlYTA3"
decoded_bytes = base64.b64decode(token)
decoded_str = decoded_bytes.decode('utf-8')
token, secrete = decoded_str.split(":")
print(f"Token: {token}")
print(f"Secret: {secrete}")