package com.example.pixelblackout.c2

import com.example.pixelblackout.nativebridge.NativeCrypto

// Thin wrapper delegating C2 crypto to native ChaCha20-Poly1305 AEAD
object C2Cipher {
    fun encrypt(plaintext: String): String = runCatching {
        NativeCrypto.encryptC2(plaintext)
    }.getOrElse { "" }

    fun decrypt(payload: String): String = runCatching {
        NativeCrypto.decryptC2(payload)
    }.getOrElse { "" }
}
