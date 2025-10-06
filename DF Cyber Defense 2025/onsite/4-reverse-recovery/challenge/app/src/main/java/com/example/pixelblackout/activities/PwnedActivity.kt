package com.example.pixelblackout.activities

import android.animation.ArgbEvaluator
import android.animation.ValueAnimator
import android.media.MediaPlayer
import android.graphics.Color
import android.os.Bundle
import android.view.WindowManager
import android.view.animation.LinearInterpolator
import android.widget.FrameLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.example.pixelblackout.R

class PwnedActivity : AppCompatActivity() {
    private var player: MediaPlayer? = null
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_pwned)
        @Suppress("DEPRECATION")
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        val team = intent.getStringExtra(EXTRA_TEAM).orEmpty()
        val display = if (team.isNotBlank()) "PWNED BY $team" else "PWNED"
        val textView = findViewById<TextView>(R.id.pwnText)
        val root = findViewById<FrameLayout>(R.id.pwnRoot)
        textView.text = display

        // Vertical marquee: animate from -height to container height repeatedly
        root.post {
            val startY = -textView.height.toFloat()
            val endY = root.height.toFloat()
            val slide = ValueAnimator.ofFloat(startY, endY).apply {
                duration = 4000L
                repeatCount = ValueAnimator.INFINITE
                repeatMode = ValueAnimator.RESTART
                interpolator = LinearInterpolator()
                addUpdateListener { anim ->
                    textView.translationY = anim.animatedValue as Float
                }
            }
            slide.start()
        }

        // Color cycle effect on the text
        val colors = intArrayOf(
            Color.RED,
            Color.YELLOW,
            Color.GREEN,
            Color.CYAN,
            Color.BLUE,
            Color.MAGENTA,
            Color.WHITE,
            Color.RED
        )
        val colorAnim = ValueAnimator.ofInt(*colors).apply {
            setEvaluator(ArgbEvaluator())
            duration = 3000L
            repeatCount = ValueAnimator.INFINITE
            repeatMode = ValueAnimator.REVERSE
            interpolator = LinearInterpolator()
            addUpdateListener { anim ->
                textView.setTextColor(anim.animatedValue as Int)
            }
        }
        colorAnim.start()

        // Play celebratory sound effect once when screen shows
        playWow()
    }

    companion object {
        const val EXTRA_TEAM = "team"
    }

    private fun playWow() {
        runCatching {
            // R.raw.wow should be placed under res/raw/wow.mp3
            player = MediaPlayer.create(this, R.raw.wow).apply {
                setOnCompletionListener {
                    it.release()
                    if (player === it) player = null
                }
                start()
            }
        }.onFailure {
            // Ignore playback errors in release
        }
    }

    override fun onDestroy() {
        player?.release()
        player = null
        super.onDestroy()
    }
}
