package com.example.pixelblackout.c2

import android.content.Context
import android.Manifest
import android.os.Build
import android.provider.Settings
import java.util.UUID

object DeviceId {
    private const val PREF = "c2_prefs"
    private const val KEY = "device_id"

    fun get(context: Context): String {
        val prefs = context.getSharedPreferences(PREF, Context.MODE_PRIVATE)
        val cached = prefs.getString(KEY, null)
        if (!cached.isNullOrBlank()) {
            return cached
        }
        val generated = resolveHardwareId(context) ?: UUID.randomUUID().toString()
        prefs.edit().putString(KEY, generated).apply()
        return generated
    }

    private fun resolveHardwareId(context: Context): String? {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            } else {
                @Suppress("DEPRECATION")
                val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as? android.telephony.TelephonyManager
                tm?.deviceId
            }
        } catch (error: SecurityException) {
            null
        }
    }
}
