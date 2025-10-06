package com.example.pixelblackout.c2

import java.util.concurrent.CopyOnWriteArraySet

object RemoteCommandRouter {
    private val listeners = CopyOnWriteArraySet<(String) -> Unit>()

    fun register(listener: (String) -> Unit) {
        listeners += listener
    }

    fun unregister(listener: (String) -> Unit) {
        listeners -= listener
    }

    fun dispatch(payload: String) {
        if (payload.isBlank()) return
        listeners.forEach { listener ->
            runCatching { listener(payload) }
        }
    }
}
