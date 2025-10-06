package com.example.pixelblackout.utils

import android.util.Base64

object StringVault {
    private const val MASK: Int = 0x23

    fun reveal(token: String): String {
        val decoded = Base64.decode(token, Base64.NO_WRAP)
        val bytes = ByteArray(decoded.size)
        for (i in decoded.indices) {
            bytes[i] = (decoded[i].toInt() xor MASK).toByte()
        }
        return String(bytes, Charsets.UTF_8)
    }
}
