package com.example.pixelblackout.nativebridge

object NativeCrypto {
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

    private fun ensureConfigured() {
        if (configured) return
        synchronized(this) {
            if (configured) return
            if (!nativeOkToRun()) {
                throw IllegalStateException("Unsupported environment detected")
            }
            val material = RemoteKeyProvider.fetch()
            val mask = RemoteKeyProvider.MASK
            nativeConfigure(mask, material.key, material.iv, material.password)
            configured = true
        }
    }

    private external fun nativeEncryptString(plaintext: String): String
    private external fun nativeDecryptString(payload: String): String
    private external fun nativeEncryptArchive(data: ByteArray): ByteArray
    private external fun nativeConfigure(mask: Int, key: ByteArray, iv: ByteArray, archivePassword: ByteArray)
    private external fun nativeOkToRun(): Boolean
}
