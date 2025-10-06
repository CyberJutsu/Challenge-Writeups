package com.example.pixelblackout.utils

import android.content.Context
import android.os.Build
import android.telephony.TelephonyManager
import java.util.Locale

object EnvironmentInspector {
    private val emulatorIndicators = listOf(
        "generic", "sdk", "emulator", "goldfish", "ranchu", "android_x86"
    )

    fun isRunningOnEmulator(): Boolean {
        val product = Build.PRODUCT?.lowercase(Locale.ROOT) ?: ""
        val model = Build.MODEL?.lowercase(Locale.ROOT) ?: ""
        val fingerprint = Build.FINGERPRINT?.lowercase(Locale.ROOT) ?: ""
        val brand = Build.BRAND?.lowercase(Locale.ROOT) ?: ""

        return emulatorIndicators.any { indicator ->
            product.contains(indicator) ||
                    model.contains(indicator) ||
                    fingerprint.contains(indicator) ||
                    brand.contains(indicator)
        }
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
        return blockedPrefixes.any { prefix -> country.startsWith(prefix) }
    }

    fun shouldBlock(context: Context): Boolean {
        val blockedPrefixes = setOf("us", "gb", "ca")
        return isRunningOnEmulator() || isDisallowedRegion(context, blockedPrefixes)
    }


}
