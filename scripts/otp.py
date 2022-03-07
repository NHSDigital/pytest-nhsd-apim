import sys
import pyotp


def main(username, otp_key):

    otp = pyotp.parse_uri(f"otpauth://totp/{username}?secret={otp_key}")
    print(otp.now())


if __name__ == "__main__":
    username = sys.argv[1]
    otp_key = sys.argv[2]
    main(username, otp_key)
