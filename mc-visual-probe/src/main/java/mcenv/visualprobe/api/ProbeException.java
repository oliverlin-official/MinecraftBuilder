package mcenv.visualprobe.api;

public final class ProbeException extends Exception {
	private final String code;
	private final int httpStatus;

	public ProbeException(String code, int httpStatus, String message) {
		super(message);
		this.code = code;
		this.httpStatus = httpStatus;
	}

	public String code() {
		return code;
	}

	public int httpStatus() {
		return httpStatus;
	}

	public static ProbeException noWorld() {
		return new ProbeException("NO_WORLD", 503, "No Minecraft world is loaded.");
	}

	public static ProbeException invalidPose(String detail) {
		return new ProbeException("CAMERA_POSE_INVALID", 400, detail);
	}

	public static ProbeException chunkTimeout(int loaded, int required) {
		return new ProbeException(
			"TARGET_CHUNK_TIMEOUT",
			409,
			"Camera chunks were not ready in time (loaded radius " + loaded + ", required " + required + ")."
		);
	}

	public static ProbeException worldNotSynced(String detail) {
		return new ProbeException("WORLD_NOT_SYNCED", 409, detail);
	}

	public static ProbeException captureTimeout(String detail) {
		return new ProbeException("CAPTURE_TIMEOUT", 504, detail);
	}

	public static ProbeException framebufferUnavailable() {
		return new ProbeException("FRAMEBUFFER_UNAVAILABLE", 500, "Minecraft framebuffer is not available.");
	}

	public static ProbeException screenshotFailed(String detail) {
		return new ProbeException("SCREENSHOT_FAILED", 500, detail);
	}

	public static ProbeException backendUnavailable(String detail) {
		return new ProbeException("CAMERA_BACKEND_UNAVAILABLE", 503, detail);
	}

	public static ProbeException unauthorized() {
		return new ProbeException("UNAUTHORIZED", 401, "Missing or invalid session token.");
	}

	public static ProbeException busy() {
		return new ProbeException("CAPTURING", 409, "Another observation is already in progress.");
	}
}
