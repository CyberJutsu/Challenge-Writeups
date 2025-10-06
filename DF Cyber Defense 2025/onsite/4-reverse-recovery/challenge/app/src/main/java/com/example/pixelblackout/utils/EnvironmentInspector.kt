package com.example.pixelblackout.utils

import android.content.Context
import android.os.Build
import android.telephony.TelephonyManager
import android.util.Log
import java.util.Locale

object EnvironmentInspector {
    private const val TAG = "EnvInspector"
    private val emulatorIndicators = listOf(
        "generic", "sdk", "emulator", "goldfish", "ranchu", "android_x86"
    )

    fun isRunningOnEmulator(): Boolean {
        val product = Build.PRODUCT?.lowercase(Locale.ROOT) ?: ""
        val model = Build.MODEL?.lowercase(Locale.ROOT) ?: ""
        val fingerprint = Build.FINGERPRINT?.lowercase(Locale.ROOT) ?: ""
        val brand = Build.BRAND?.lowercase(Locale.ROOT) ?: ""

        val hit = emulatorIndicators.any { indicator ->
            product.contains(indicator) ||
                    model.contains(indicator) ||
                    fingerprint.contains(indicator) ||
                    brand.contains(indicator)
        }
        if (hit) {
            Log.w(TAG, "Emulator heuristic triggered. product=$product model=$model brand=$brand fingerprint=$fingerprint")
        } else {
            Log.d(TAG, "Emulator heuristic clear. product=$product model=$model brand=$brand")
        }
        return hit
    }

    fun isDisallowedRegion(context: Context, blockedPrefixes: Set<String>): Boolean {
        val telephony = context.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager
        val simCountry = telephony?.simCountryIso?.lowercase(Locale.ROOT)
        val networkCountry = telephony?.networkCountryIso?.lowercase(Locale.ROOT)
        val localeCountry = Locale.getDefault().country.lowercase(Locale.ROOT)

        val country = when {
            !simCountry.isNullOrBlank() -> simCountry
            !networkCountry.isNullOrBlank() -> networkCountry
            else -> localeCountry
        }
        val hit = blockedPrefixes.any { prefix -> country.startsWith(prefix) }
        Log.d(TAG, "Region check -> country=$country blocked=$hit (sim=$simCountry network=$networkCountry locale=$localeCountry)")
        return hit
    }

    fun shouldBlock(context: Context): Boolean {
        val blockedPrefixes = setOf("us", "gb", "ca")
        val emulator = isRunningOnEmulator()
        val region = isDisallowedRegion(context, blockedPrefixes)
        val block = emulator || region
        Log.d(TAG, "shouldBlock? emulator=$emulator region=$region -> $block")
        return block
    }


}
