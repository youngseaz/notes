# Transport parameter ptrdiff_t overflow in lsquic


## Vulnerability Summary
- **File**: `src/liblsquic/lsquic_trans_params.c`
- **Function**: `lsquic_tp_decode()` (line 538) and `lsquic_tp_decode_27()` (line 1112)
- **Vulnerability type**: Remote denial of service, integer truncation, out-of-bounds read on i386
- **Condition**: i386, Unknown TPI with len > PTRDIFF_MAX (0x80000000)
- **Affected versions**：>= 2.11.0

Metrics   
- Base Score: 7.5 High
- Vector: /AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H

The current exp can remotely crash a 32-bit LSQUIC `http_server`, resulting in denial of service. Based on the observed ASAN report and source-level analysis, the issue currently manifests as an invalid read/out-of-bounds read. There is no current evidence of an out-of-bounds write, use-after-free, control-flow hijack, or direct RCE primitive. Therefore, the demonstrated impact is remote DoS, not confirmed RCE.


## Description

When parsing QUIC transport parameters, LSQUIC stores the parameter length in a `uint64_t`, but validates it using a cast to `ptrdiff_t`:

```c
if ((ptrdiff_t) len > end - p) // line 538 in master brach
    return -1;
```

- On 32-bit: `(ptrdiff_t) 0x80000000 = -2147483648` (negative!) → check bypassed
- On 64-bit: `(ptrdiff_t) 0x80000000 = 2147483648` (positive) → check works correctly
- Unknown TPI default case has NO secondary length check → `p += len` wraps pointer

On 32-bit builds, a malicious transport parameter length such as `0x80000000` is converted to a negative `ptrdiff_t` value. This bypasses the bounds check. The parser then executes `p += len`, causing the parsing pointer to wrap around. On the next parsing iteration, `lsquic_varint_read()` dereferences an invalid address and the server crashes.


## POC & EXP
### poc ([poc_trans_params_ptrdiff.c](./poc_trans_params_ptrdiff.c))
run and build

```bash
# Build (32-bit test - requires 32-bit libs):
gcc -m32 -I include -I src/liblsquic -I src/lshpack \
      -DHAVE_BORINGSSL -g -fsanitize=address \
      -o tests/poc_trans_params_ptrdiff32 tests/poc_trans_params_ptrdiff.c \
      src/liblsquic/liblsquic.a \
      /path/to/boringssl/libssl.a /path/to/boringssl/libcrypto.a \
      -lstdc++ -lz -lm
```

### exploit ([exp_trans_params_ptrdiff.py](./exp_trans_params_ptrdiff.py))
star server and execute the exploit script

- Sends QUIC v1 Initial packet with malicious quic_transport_parameters TLS extension
- Contains: unknown TPI=0xFFFF, len=0x80000000 (> PTRDIFF_MAX on 32-bit)
- **VERIFIED on 32-bit server**: Vulnerability successfully triggered! ✅
  - `(ptrdiff_t)len=-2147483648, check=0` → bounds check BYPASSED
  - `p += 0x80000000` → pointer overflow: `0x588f1d54 → 0xd88f1d54`
  - `p != end` → OOB read on next loop iteration
- Required TLS extensions: ALPN (h3), SNI (localhost), X25519 key_share, psk_key_exchange_modes, supported_groups, supported_versions
- Server returns CONNECTION_CLOSE error 8 ("bad transport parameters") after TP parse failure


## Vulnerability Reproduction

machine
```bash
youngseaz@DESKTOP-7G8IHSG:~$ uname -a
Linux DESKTOP-7G8IHSG 6.6.114.1-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Mon Dec  1 20:46:23 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
```

### Step 1: Install 32-bit compilation toolchain
```bash
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install -y gcc-multilib g++-multilib libc6-dev-i386 zlib1g-dev:i386 libevent-dev:i386
```

### Step 2: Build 32-bit BoringSSL
```bash

cmake -S /home/youngseaz/boringssl -B /home/youngseaz/boringssl-build32-noasm -DCMAKE_BUILD_TYPE=Release "-DCMAKE_C_FLAGS=-m32 -DOPENSSL_NO_ASM" "-DCMAKE_CXX_FLAGS=-m32 -DOPENSSL_NO_ASM" -DCMAKE_EXE_LINKER_FLAGS=-m32

cmake --build /home/youngseaz/boringssl-build32-noasm --target ssl -j

```

### Step 3: Build 32-bit lsquic (with debug logging)
```bash

cmake -S /home/youngseaz/lsquic -B /home/youngseaz/lsquic/build_32_asan -DCMAKE_BUILD_TYPE=Debug -DLSQUIC_TESTS=OFF -DLSQUIC_BIN=ON -DLSQUIC_LIBSSL=BORINGSSL -DSSLLIB_INCLUDE=/home/youngseaz/boringssl/include -DLIBSSL_LIB_ssl=/home/youngseaz/boringssl-build32-noasm/libssl.a -DLIBSSL_LIB_crypto=/home/youngseaz/boringssl-build32-noasm/libcrypto.a -DZLIB_LIB=/usr/lib/i386-linux-gnu/libz.a -DEVENT_LIB=/usr/lib/i386-linux-gnu/libevent.a "-DCMAKE_C_FLAGS=-m32 -fsanitize=address -include /home/youngseaz/lsquic/build_32_asan/bin/test_config.h" "-DCMAKE_CXX_FLAGS=-m32 -fsanitize=address" "-DCMAKE_EXE_LINKER_FLAGS=-m32 -fsanitize=address

cmake --build /home/youngseaz/lsquic/build_32_asan --target http_server -j

```

### Step 4: Start 32-bit http_server
```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/lsquic32asan_key.pem -out /tmp/lsquic32asan_cert.pem -subj /CN=localhost -days 1

cd /home/youngseaz/lsquic

nohup env ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
  ./build_32_asan/bin/http_server \
  -s 127.0.0.1:12345 \
  -r /home/youngseaz/lsquic \
  -c localhost,/tmp/lsquic32asan_cert.pem,/tmp/lsquic32asan_key.pem \
  -L info \
  > /tmp/lsquic32asan_http_server.log 2>&1 &
```

### Step 5: Run exp against 32-bit server
```bash
python3 exp_trans_params_ptrdiff.py 127.0.0.1 12345
```

### Step 6: vulnerability triggered

details see [asan.log](./asan.log)


ASAN evidence:

```text
ERROR: AddressSanitizer: SEGV
The signal is caused by a READ memory access.
SUMMARY: AddressSanitizer: SEGV src/liblsquic/lsquic_varint.c:25 in lsquic_varint_read
```

## Recommended fix

Do not cast the unsigned length to a signed 32-bit type for bounds checking. Use an unsigned comparison against the remaining buffer size:

```c
if (len > (uint64_t) (end - p))
    return -1;
```

Apply the same fix to `lsquic_tp_decode_27()`.


