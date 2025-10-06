package com.example.pixelblackout.c2

import java.util.concurrent.atomic.AtomicReference

object C2KeyVault {
    private val keyRef = AtomicReference<ByteArray?>()
    private val nonceRef = AtomicReference<ByteArray?>()

    fun install(key: ByteArray, baseNonce: ByteArray) {
        keyRef.set(key.copyOf())
        nonceRef.set(baseNonce.copyOf())
    }

    fun require(): Material {
        val key = keyRef.get() ?: throw IllegalStateException("C2 key unavailable")
        val nonce = nonceRef.get() ?: throw IllegalStateException("C2 nonce unavailable")
        if (nonce.size != NONCE_SIZE) {
            throw IllegalStateException("Unexpected nonce length")
        }
        return Material(key, nonce)
    }

    data class Material(val key: ByteArray, val baseNonce: ByteArray)

    private const val NONCE_SIZE = 12
}
