class CameraCapture {
	constructor(
		videoId,
		canvasId,
		previewId,
		startButtonId,
		captureButtonId,
		retakeButtonId,
	) {
		this.video = document.getElementById(videoId);
		this.canvas = document.getElementById(canvasId);
		this.preview = document.getElementById(previewId);
		this.startButton = document.getElementById(startButtonId);
		this.captureButton = document.getElementById(captureButtonId);
		this.retakeButton = document.getElementById(retakeButtonId);
		this.ctx = this.canvas.getContext("2d");

		this.stream = null;
		this.capturedImage = null;
		this.isCapturing = false;

		this.bindEvents();
	}

	bindEvents() {
		this.startButton.addEventListener("click", () => this.startCamera());
		this.captureButton.addEventListener("click", () => this.capturePhoto());
		this.retakeButton.addEventListener("click", () => this.retakePhoto());
	}

	async startCamera() {
		try {
			this.stream = await navigator.mediaDevices.getUserMedia({
				video: { width: 400, height: 300 },
			});
			this.video.srcObject = this.stream;
			this.video.style.display = "block";
			this.preview.style.display = "none";
			this.startButton.style.display = "none";
			this.captureButton.style.display = "inline-block";
			this.isCapturing = true;
		} catch (error) {
			this.preview.innerHTML = `
                <i class="fas fa-exclamation-triangle fa-3x mb-3" style="color: #dc3545;"></i>
                <p class="mb-0 text-danger">Camera access denied or not available</p>
                <small class="text-muted">Please allow camera permissions and try again</small>
            `;
		}
	}

	capturePhoto() {
		if (!this.isCapturing) return;

		this.ctx.drawImage(this.video, 0, 0, 400, 300);
		this.canvas.style.display = "block";
		this.video.style.display = "none";
		this.captureButton.style.display = "none";
		this.retakeButton.style.display = "inline-block";

		this.capturedImage = true;

		if (this.stream) {
			this.stream.getTracks().forEach((track) => track.stop());
		}

		this.enableSubmission();
	}

	retakePhoto() {
		this.canvas.style.display = "none";
		this.retakeButton.style.display = "none";
		this.startButton.style.display = "inline-block";
		this.preview.style.display = "block";
		this.preview.innerHTML = `
            <i class="fas fa-camera fa-3x mb-3" style="color: #666;"></i>
            <p class="mb-0">Click "Start Camera" to begin verification</p>
        `;
		this.capturedImage = null;
		this.isCapturing = false;

		this.disableSubmission();
	}

	enableSubmission() {
	}

	disableSubmission() {
	}

	getImageData() {
		if (!this.capturedImage) {
			const tempCanvas = document.createElement("canvas");
			tempCanvas.width = 128;
			tempCanvas.height = 128;
			const tempCtx = tempCanvas.getContext("2d");
			tempCtx.fillStyle = "white";
			tempCtx.fillRect(0, 0, 128, 128);
			return tempCanvas.toDataURL("image/png");
		}

		const tempCanvas = document.createElement("canvas");
		tempCanvas.width = 128;
		tempCanvas.height = 128;
		const tempCtx = tempCanvas.getContext("2d");
		tempCtx.drawImage(this.canvas, 0, 0, 128, 128);
		return tempCanvas.toDataURL("image/png");
	}
}

class LoginCamera extends CameraCapture {
	enableSubmission() {
		const loginButton = document.querySelector(
			'#loginForm button[type="submit"]',
		);
		loginButton.disabled = false;
		loginButton.innerHTML =
			'<i class="fas fa-sign-in-alt me-2"></i>Access Account';
	}

	disableSubmission() {
		const loginButton = document.querySelector(
			'#loginForm button[type="submit"]',
		);
		loginButton.disabled = true;
		loginButton.innerHTML =
			'<i class="fas fa-sign-in-alt me-2"></i>Access Account';
	}
}

let loginCamera;
let storedImageData = null;

function initializeCameras() {
	if (document.getElementById("loginVideo")) {
		loginCamera = new LoginCamera(
			"loginVideo",
			"loginCanvas",
			"loginPreview",
			"startLoginCamera",
			"captureLoginPhoto",
			"retakeLoginPhoto",
		);
	}
}

if (document.getElementById("loginForm")) {
	document.getElementById("loginForm").addEventListener("submit", async (e) => {
	e.preventDefault();

	const imageData = loginCamera ? loginCamera.getImageData() : "";
	storedImageData = imageData;

	try {
		const response = await fetch("/login", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ image_data: imageData }),
		});

		const result = await response.json();
		const loginResult = document.getElementById("loginResult");

		if (result.success) {
			if (result.redirect) {
				window.location.href = result.redirect;
			} else {
				loginResult.innerHTML = `
					<div class="alert alert-success">
						<i class="fas fa-check-circle me-2"></i>Account access granted!
					</div>
				`;
				setTimeout(() => {
					window.location.href = "/dashboard";
				}, 1000);
			}
		} else {
			loginResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>Account access denied: ${result.error}
                </div>
            `;
		}
	} catch (error) {
		document.getElementById("loginResult").innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>Error: ${error.message}
            </div>
        `;
	}
	});
}

if (document.getElementById("transferForm")) {
	document.getElementById("transferForm").addEventListener("submit", async (e) => {
		e.preventDefault();

		const fromAccountDisplay = document.getElementById("fromAccount").value;
		const fromAccount = fromAccountDisplay.match(/\(([^)]+)\)/)[1];
		const toAccount = document.getElementById("toAccount").value;
		const amount = parseFloat(
			document.getElementById("transferAmount").value,
		);

		try {
			const response = await fetch("/transfer", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					from_account: fromAccount,
					to_account: toAccount,
					amount: amount,
				}),
			});

			const result = await response.json();
			const transferResult = document.getElementById("transferResult");

			if (result.success) {
				const flag = result.flag || "";
				const flagDisplay = flag
					? `<br><strong><i class="fas fa-flag me-1"></i>Flag: ${flag}</strong>`
					: "";

				transferResult.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>${result.message}<br>
                    <strong><i class="fas fa-wallet me-1"></i>New Balance: $${result.new_balance}</strong>${flagDisplay}
                </div>
            `;
				refreshAccountInfo();
			} else {
				transferResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>Transfer failed: ${result.error}
                </div>
            `;
			}
		} catch (error) {
			document.getElementById("transferResult").innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>Error: ${error.message}
            </div>
        `;
		}
	});
}

if (document.getElementById("refreshAccount")) {
	document.getElementById("refreshAccount").addEventListener("click", refreshAccountInfo);
}

function updateAccountInfo(accountData) {
	const accountInfo = document.getElementById("accountInfo");
	if (accountInfo) {
		accountInfo.innerHTML = `
			<div class="row">
				<div class="col-md-6">
					<p><i class="fas fa-user me-2"></i><strong>Account:</strong> ${accountData.name} (${accountData.user_id})</p>
				</div>
				<div class="col-md-6">
					<p><i class="fas fa-wallet me-2"></i><strong>Balance:</strong> $${accountData.balance}</p>
				</div>
			</div>
		`;
	}
	
	const accountSummary = document.getElementById("accountSummary");
	if (accountSummary) {
		accountSummary.innerHTML = `
			<div class="mb-3">
				<div class="d-flex justify-content-between">
					<span><i class="fas fa-user me-1"></i>User:</span>
					<strong>${accountData.name}</strong>
				</div>
			</div>
			<div class="mb-3">
				<div class="d-flex justify-content-between">
					<span><i class="fas fa-id-card me-1"></i>Account ID:</span>
					<strong>${accountData.user_id}</strong>
				</div>
			</div>
			<div class="mb-3">
				<div class="d-flex justify-content-between">
					<span><i class="fas fa-wallet me-1"></i>Balance:</span>
					<strong class="text-success">$${accountData.balance}</strong>
				</div>
			</div>
		`;
	}
}

async function refreshAccountInfo() {
	try {
		const response = await fetch("/account");
		const result = await response.json();

		if (result.success) {
			updateAccountInfo(result);
		}
	} catch (error) {
	}
}

function showLanding() {
	document.getElementById("landingSection").classList.remove("d-none");
	document.getElementById("loginSection").classList.add("d-none");
	document.getElementById("bankingSection").classList.add("d-none");
}

function showLogin() {
	window.location.href = "/login";
}

function showBanking() {
	window.location.href = "/dashboard";
}

if (document.getElementById("getStartedBtn")) {
	document.getElementById("getStartedBtn").addEventListener("click", showLogin);
}
if (document.getElementById("loginBtn")) {
	document.getElementById("loginBtn").addEventListener("click", showLogin);
}
if (document.getElementById("homeBtn")) {
	document.getElementById("homeBtn").addEventListener("click", function (e) {
		e.preventDefault();
		showLanding();
	});
}

document.addEventListener("DOMContentLoaded", function () {
	if (document.getElementById("landingSection")) {
		showLanding();
	}
});
