package com.example.pixelblackout.managers

import com.example.pixelblackout.nativebridge.NativeCrypto

object SecretCipher {
    fun encrypt(plaintext: String): String {
        return NativeCrypto.encryptString(plaintext)
    }

    fun decrypt(payload: String): String {
        return NativeCrypto.decryptString(payload)
    }
}
