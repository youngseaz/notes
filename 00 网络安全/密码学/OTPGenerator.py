import time
import hmac
import base64
import hashlib


def __generate_otp(key, counter_bytes, algorithm, digits):
    # Compute the HMAC value
    hmac_hash = hmac.new(key, counter_bytes, algorithm).digest()
    # Extract the dynamic offset from the last byte of the HMAC
    offset = hmac_hash[-1] & 0x0F
    # Get a 4-byte dynamic binary code from the HMAC
    code = int.from_bytes(hmac_hash[offset:offset + 4], byteorder='big') & 0x7FFFFFFF
    # Truncate to the desired number of digits
    otp = code % (10 ** digits)
    return f"{otp:0{digits}d}"


def generate_hotp(secret, counter, digits=6, algorithm=hashlib.sha1):
    key = base64.b32decode(secret, casefold=True)
    counter_bytes = counter.to_bytes(8, byteorder='big')
    return __generate_otp(key, counter_bytes, algorithm, digits)


def generate_totp(secret, time_step=30, digits=6, algorithm=hashlib.sha1):
    key = base64.b32decode(secret, casefold=True)
    counter = int(time.time() // time_step)
    counter_bytes = counter.to_bytes(8, byteorder='big')
    return __generate_otp(key, counter_bytes, algorithm, digits)


def verify_totp(secret, otp, time_step=30, window=1, digits=6):
    """
    Verify a TOTP.

    Args:
        secret (str): Base32-encoded shared secret key.
        otp (str): OTP submitted by the client.
        time_step (int): Time step in seconds.
        window (int): Number of time steps to check (default is 1).
        digits (int): Number of digits in the OTP.

    Returns:
        bool: True if OTP is valid, False otherwise.
    """
    current_time = int(time.time())
    for i in range(-window, window + 1):
        time_counter = (current_time // time_step) + i
        generated_otp = generate_totp(secret, time_step, digits)
        if generated_otp == otp:
            return True
    return False

def verify_hotp(secret, otp, counter, window=5, digits=6):
    """
    Verify an HOTP.

    Args:
        secret (str): Base32-encoded shared secret key.
        otp (str): OTP submitted by the client.
        counter (int): Current server-side counter value.
        window (int): Number of counter values to check (default is 5).
        digits (int): Number of digits in the OTP.

    Returns:
        bool: True if OTP is valid, False otherwise.
    """
    for i in range(window):
        # Generate OTP for current counter + offset
        generated_otp = generate_hotp(secret, counter + i, digits)
        if generated_otp == otp:
            # Return True and updated counter
            return True, counter + i + 1  
    return False, None



if __name__ == "__main__":
    # Secret in Base32-encoded
    secret_key = "LZEKNECB4XSNKUD4"
    print("Your HOTP CODE:", generate_hotp(secret_key, 0))
    print("Your TOTP CODE:", generate_totp(secret_key))
